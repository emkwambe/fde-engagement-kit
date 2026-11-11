"""Where the agent's conversation state is saved (Day 2, part 3).

  memory   - InMemorySaver: fast, for tests; everything is lost when the process ends.
  postgres - PostgresSaver: every step is written to Postgres (schema `agent`), so a thread paused
             for approval survives restarts, and any API replica can resume it (needed on Cloud Run).
LangGraph owns these tables and creates/upgrades them with setup() (idempotent). They live in the
`agent` schema next to our own agent.approvals / agent.audit_log tables (DC-013).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row

from core.db.connection import database_url

CHECKPOINT_SCHEMA = "agent"


@contextmanager
def postgres_checkpointer(dsn: str | None = None) -> Iterator[PostgresSaver]:
    with psycopg.connect(dsn or database_url(), autocommit=True, prepare_threshold=0, row_factory=dict_row,
                         options=f"-c search_path={CHECKPOINT_SCHEMA}") as conn:
        saver = PostgresSaver(conn)  # type: ignore[arg-type]
        saver.setup()
        yield saver
