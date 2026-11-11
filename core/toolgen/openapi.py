"""Turn an OpenAPI 3 spec into agent tools (Day 2, part 2, FR-07).

One tool per operation. The tool name is the operationId, the description is the
operation's summary, and the arguments are built from the spec's path/query parameters
and JSON request body, INCLUDING its rules (pattern, minimum, maximum, enum, lengths).
So invalid arguments are rejected before any HTTP request leaves our side.

Each tool carries metadata the agent uses later:
    requires_approval  True when the HTTP method is listed in engagement.yaml require_approval
    method, path       what the tool calls
Tools never raise on HTTP errors: they return {"error": ..., "status": ...} so the agent
can read the problem and recover instead of crashing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import httpx
import yaml
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

from core.config.schema import OpenAPITool

SKIP_HEADERS = {"authorization", "x-client"}  # set by us, never by the model
CLIENT_NAME = "fde-agent"


# ----------------------------------------------------------------------------- JSON schema -> pydantic
def _resolve(schema: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    while "$ref" in schema:
        ref = schema["$ref"]  # e.g. "#/components/schemas/TicketCreate"
        node: Any = spec
        for part in ref.lstrip("#/").split("/"):
            node = node[part]
        schema = node
    return schema


def _python_type(schema: dict[str, Any]) -> tuple[Any, bool]:
    """Return (python type, nullable) for a JSON-schema fragment."""
    if "anyOf" in schema:
        options = [s for s in schema["anyOf"] if s.get("type") != "null"]
        nullable = len(options) < len(schema["anyOf"])
        inner, _ = _python_type(options[0]) if options else (str, True)
        return inner, nullable
    if "enum" in schema:
        return Literal[tuple(schema["enum"])], False  # type: ignore[valid-type]
    return {"string": str, "integer": int, "number": float, "boolean": bool,
            "array": list, "object": dict}.get(schema.get("type", "string"), str), False


def _constraints(schema: dict[str, Any]) -> dict[str, Any]:
    if "anyOf" in schema:
        options = [s for s in schema["anyOf"] if s.get("type") != "null"]
        schema = {**(options[0] if options else {}), **{k: v for k, v in schema.items() if k != "anyOf"}}
    mapping = {"minimum": "ge", "maximum": "le", "exclusiveMinimum": "gt", "exclusiveMaximum": "lt",
               "minLength": "min_length", "maxLength": "max_length", "pattern": "pattern"}
    return {py: schema[js] for js, py in mapping.items() if js in schema}


def _field(schema: dict[str, Any], required: bool, description: str = "") -> tuple[Any, Any]:
    py_type, nullable = _python_type(schema)
    has_default = "default" in schema
    if nullable or (not required and not has_default):
        py_type = py_type | None  # optional with no default value -> may be omitted (None)
    default = ... if required else schema.get("default")
    return py_type, Field(default, description=description or schema.get("description", ""),
                          **_constraints(schema))


# ----------------------------------------------------------------------------- operations -> tools
class Operation(BaseModel):
    operation_id: str
    method: str
    path: str
    summary: str
    path_params: list[str]
    query_params: list[str]
    body_fields: list[str]
    args_model: type[BaseModel]

    model_config = {"arbitrary_types_allowed": True}


def parse_operations(spec: dict[str, Any], include: list[str] | None = None) -> list[Operation]:
    ops: list[Operation] = []
    for path, methods in spec.get("paths", {}).items():
        for method, op in methods.items():
            op_id = op.get("operationId")
            if not op_id or (include and op_id not in include):
                continue
            fields: dict[str, Any] = {}
            path_params: list[str] = []
            query_params: list[str] = []
            body_fields: list[str] = []
            for p in op.get("parameters", []):
                if p["in"] == "header" and p["name"].lower() in SKIP_HEADERS:
                    continue
                if p["in"] not in ("path", "query"):
                    continue
                schema = _resolve(p.get("schema", {}), spec)
                fields[p["name"]] = _field(schema, p.get("required", False), p.get("description", ""))
                (path_params if p["in"] == "path" else query_params).append(p["name"])
            body = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
            if body:
                body = _resolve(body, spec)
                required = set(body.get("required", []))
                for name, prop in body.get("properties", {}).items():
                    fields[name] = _field(_resolve(prop, spec), name in required)
                    body_fields.append(name)
            model = create_model(f"{op_id}_args", **fields)
            summary = op.get("summary") or op.get("description") or op_id
            ops.append(Operation(operation_id=op_id, method=method.upper(), path=path, summary=summary,
                                 path_params=path_params, query_params=query_params,
                                 body_fields=body_fields, args_model=model))
    return ops


def _make_caller(op: Operation, cfg: OpenAPITool, client: httpx.Client | None):
    headers = {"X-Client": CLIENT_NAME}
    if cfg.auth.type == "bearer" and cfg.auth.token:
        headers["Authorization"] = f"Bearer {cfg.auth.token}"
    elif cfg.auth.type == "api_key" and cfg.auth.token:
        headers["X-API-Key"] = cfg.auth.token

    def call(**kwargs: Any) -> str:
        url_path = op.path
        for name in op.path_params:
            url_path = url_path.replace("{" + name + "}", str(kwargs[name]))
        params = {k: kwargs[k] for k in op.query_params if kwargs.get(k) is not None}
        body = {k: kwargs[k] for k in op.body_fields if kwargs.get(k) is not None} or None
        http = client or httpx.Client(base_url=cfg.base_url, timeout=10.0)
        try:
            resp = http.request(op.method, url_path, params=params, json=body, headers=headers)
        except httpx.HTTPError as exc:
            return json.dumps({"error": f"cannot reach system: {exc.__class__.__name__}", "status": None})
        finally:
            if client is None:
                http.close()
        if resp.is_error:
            try:
                detail = resp.json().get("detail")
            except ValueError:
                detail = resp.text[:300]
            return json.dumps({"error": detail, "status": resp.status_code})
        return resp.text

    return call


def tools_from_openapi(cfg: OpenAPITool, spec_path: Path,
                       client: httpx.Client | None = None) -> list[StructuredTool]:
    """Build one StructuredTool per included operation. `client` lets tests inject a TestClient."""
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    approval = {m.upper() for m in cfg.require_approval}
    tools = []
    for op in parse_operations(spec, cfg.include_operations or None):
        needs_approval = op.method in approval
        description = op.summary + (" REQUIRES HUMAN APPROVAL before it runs." if needs_approval else "")
        tools.append(StructuredTool.from_function(
            func=_make_caller(op, cfg, client),
            name=op.operation_id,
            description=description,
            args_schema=op.args_model,
            metadata={"source": "openapi", "method": op.method, "path": op.path,
                      "requires_approval": needs_approval},
        ))
    return tools
