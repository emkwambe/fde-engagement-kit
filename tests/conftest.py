"""Shared fixtures. Tests always run with fake models (no API key, no cost)."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

os.environ["FAKE_LLM"] = "1"
os.environ.setdefault("OTEL_TRACES_EXPORTER", "none")  # tests capture spans in memory, not on stdout
os.environ.setdefault("DATABASE_URL", "postgresql://fde:fde@localhost:5432/fde")
os.environ.setdefault("ENGAGEMENT", "demo-logistics")

from core.config import EngagementConfig, load_engagement  # noqa: E402


@pytest.fixture(scope="session")
def demo_cfg() -> EngagementConfig:
    return load_engagement("demo-logistics")


@pytest.fixture(scope="session")
def migrated_db(demo_cfg: EngagementConfig) -> str:
    """Skip DB tests cleanly when Postgres isn't running (e.g. `.\\tasks.ps1 up` not done)."""
    import psycopg

    url = os.environ["DATABASE_URL"]
    try:
        psycopg.connect(url, connect_timeout=3).close()
    except Exception as exc:
        pytest.skip(f"Postgres not reachable at {url} ({exc.__class__.__name__}). Run: .\\tasks.ps1 up")
    from core.db.migrate import apply_migrations, ensure_readonly_role

    apply_migrations(demo_cfg.embeddings.dimensions)
    ensure_readonly_role()
    return url


@pytest.fixture
def conn(migrated_db: str) -> Iterator:
    from core.db.connection import connect

    with connect() as c:
        yield c
        c.rollback()  # tests never leave data behind unless they commit on purpose
