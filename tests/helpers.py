"""Shared test helpers for the demo-logistics engagement (Sprint 01, kit-generic).

The logistics seed generator, table specs and fake-model script moved out of core/ into the engagement folder.
Tests reach them the same way the kit does: through engagement.yaml.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

from core.config import load_engagement
from core.extensions import load_module
from core.ingest.etl import TableSpec, table_specs

_CFG = load_engagement("demo-logistics")
LOGISTICS_SEED: ModuleType = load_module(str(_CFG.sources.tables[0].seed_script))
LOGISTICS_FAKE: ModuleType = load_module(str(_CFG.llm.fake_script))


def generate_logistics(out_dir: Path) -> dict[str, int]:
    result: dict[str, int] = LOGISTICS_SEED.generate(out_dir)
    return result


def logistics_specs() -> list[TableSpec]:
    return table_specs(_CFG.sources.tables[0])
