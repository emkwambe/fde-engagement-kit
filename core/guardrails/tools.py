"""Wrap every tool so its RESULT is cleaned before the model (or the audit log) sees it.

    tool result --> neutralize injection lines --> redact PII --> model

Tool results are usually JSON on ONE line. Cleaning line-by-line would then hide the whole result,
so JSON is parsed and every string VALUE inside it is cleaned separately (a document chunk keeps its
own line breaks inside its "text" value). Non-JSON results are cleaned as plain text.

The wrapped tool keeps the same name, description, arguments (and their validation) and metadata,
so the agent graph, approvals and tests don't notice the difference. metadata["guarded"] = True.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

from core.config.schema import Guardrails
from core.guardrails.injection import neutralize
from core.guardrails.pii import redact


def _clean_string(text: str, cfg: Guardrails) -> str:
    if cfg.injection_filter:
        text, _ = neutralize(text)
    if cfg.pii_redaction:
        text, _ = redact(text, cfg.pii_redaction)
    return text


def _walk(value: Any, cfg: Guardrails) -> Any:
    if isinstance(value, str):
        return _clean_string(value, cfg)
    if isinstance(value, list):
        return [_walk(v, cfg) for v in value]
    if isinstance(value, dict):
        return {k: _walk(v, cfg) for k, v in value.items()}
    return value


def clean_text(text: str, cfg: Guardrails) -> str:
    """Clean a tool result or a document chunk. JSON stays valid JSON."""
    stripped = text.lstrip()
    if stripped[:1] in ("{", "["):
        try:
            return json.dumps(_walk(json.loads(text), cfg))
        except ValueError:
            pass
    return _clean_string(text, cfg)


def guard_tool(tool: BaseTool, cfg: Guardrails) -> BaseTool:
    if not isinstance(tool, StructuredTool) or tool.func is None:
        return tool
    inner = tool.func

    def guarded(**kwargs: Any) -> str:
        return clean_text(str(inner(**kwargs)), cfg)

    return StructuredTool.from_function(
        func=guarded, name=tool.name, description=tool.description, args_schema=tool.args_schema,
        metadata={**(tool.metadata or {}), "guarded": True},
    )


def guard_tools(tools: list[BaseTool], cfg: Guardrails) -> list[BaseTool]:
    if not cfg.injection_filter and not cfg.pii_redaction:
        return tools
    return [guard_tool(t, cfg) for t in tools]
