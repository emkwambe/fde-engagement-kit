"""All tools for an engagement, built from engagement.yaml (Day 2, part 2).

    tools = build_tools(cfg)          # SQL tool + one tool per OpenAPI operation
    requires_approval(tool) -> bool   # the agent pauses before running these

A new customer gets new tools by editing engagement.yaml (tools.openapi / tools.sql),
not by writing code (ADR-004).
"""

from __future__ import annotations

import httpx
from langchain_core.tools import BaseTool

from core.config import resolve_path
from core.config.schema import EngagementConfig
from core.toolgen.openapi import tools_from_openapi
from core.toolgen.sql import sql_tool


def build_tools(cfg: EngagementConfig, *, http_client: httpx.Client | None = None,
                sql_schema_text: str | None = None) -> list[BaseTool]:
    tools: list[BaseTool] = []
    if cfg.tools.sql and cfg.tools.sql.enabled:
        tools.append(sql_tool(cfg.tools.sql, schema_text=sql_schema_text))
    for api in cfg.tools.openapi:
        tools.extend(tools_from_openapi(api, resolve_path(api.spec), client=http_client))
    names = [t.name for t in tools]
    duplicates = {n for n in names if names.count(n) > 1}
    if duplicates:
        raise ValueError(f"Duplicate tool names across sources: {sorted(duplicates)}")
    return tools


def requires_approval(tool: BaseTool) -> bool:
    return bool((tool.metadata or {}).get("requires_approval"))
