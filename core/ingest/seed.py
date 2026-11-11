"""Generate an engagement's synthetic data by running ITS OWN seed script (Sprint 01, kit-generic).

Usage:  uv run python -m core.ingest.seed --engagement demo-logistics

The generator is engagement-owned code: engagement.yaml -> sources.tables[].seed_script points to a Python file with
    def generate(out_dir: Path) -> dict[str, int]      # writes CSV exports, returns {table: rows}
Same seed number -> byte-identical files, so data, mock systems and golden facts always agree. Real engagements have no
seed script: their exports are copied into data/tables/ instead.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from core.config import load_engagement, resolve_path
from core.config.schema import EngagementConfig
from core.extensions import load_module


def run_seed(cfg: EngagementConfig) -> dict[str, dict[str, int]]:
    """Run every seed script of the engagement into its table folder. Returns {table folder: counts}."""
    done: dict[str, dict[str, int]] = {}
    for src in cfg.sources.tables:
        if src.seed_script:
            out_dir = resolve_path(src.path)
            done[src.path] = load_module(src.seed_script).generate(Path(out_dir))
    return done


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic data for an engagement")
    parser.add_argument("--engagement", default=os.environ.get("ENGAGEMENT", "demo-logistics"))
    args = parser.parse_args()
    cfg = load_engagement(args.engagement)
    done = run_seed(cfg)
    if not done:
        print(f"No seed_script configured for '{args.engagement}'. Put real exports in data/tables/ instead.")
    for folder, counts in done.items():
        print(f"seeded {args.engagement} ({folder}): {counts}")


if __name__ == "__main__":
    main()
