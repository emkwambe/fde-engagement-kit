"""Structured logging: one JSON object per line, so Cloud Logging, Loki or `ConvertFrom-Json` can filter by field.

The request log line (written by the API middleware) holds WHAT happened, never WHAT WAS SAID: route, status,
duration, how many model calls, token counts and tool names. No request body, no prompt, no answer, no tool
arguments, so it is safe with guardrails.log_prompts false (customer text stays out of logs; the audit log keeps
length + hash only). Tool arguments are an auditor's concern and live in agent.audit_log, not in application logs.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

REQUEST_LOGGER = "fde.request"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(), "logger": record.name, "msg": record.getMessage(),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            entry.update(fields)
        if record.exc_info:
            entry["error"] = self.formatException(record.exc_info).splitlines()[-1]
        return json.dumps(entry, default=str)


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Idempotent: attach one JSON stdout handler to the 'fde' logger tree."""
    root = logging.getLogger("fde")
    if not any(isinstance(h.formatter, JsonFormatter) for h in root.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
        root.setLevel(level)
        root.propagate = False
    return logging.getLogger(REQUEST_LOGGER)
