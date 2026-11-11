"""Postgres connections with pgvector types registered."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from pgvector.psycopg import register_vector


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env.")
    return url


@contextmanager
def connect(dsn: str | None = None, *, vector: bool = True) -> Iterator[psycopg.Connection]:
    """Open a connection; commits on success, rolls back on error."""
    with psycopg.connect(dsn or database_url()) as conn:
        if vector:
            register_vector(conn)
        yield conn
