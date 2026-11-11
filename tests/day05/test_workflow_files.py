"""Review finding F-R5: every GitHub Actions workflow file must be valid YAML.

Sprint 01b renamed a step in deploy.yml to an unquoted name containing ": ", which YAML reads as a second key.
GitHub rejected the whole file on every push ("This run likely failed because of a workflow file issue"), and
nothing in CI noticed because deploy.yml only runs when started by hand. This test parses every workflow, so the
same mistake fails `uv run pytest -q` before it is pushed (DC-035).

Run: uv run pytest tests/day05/test_workflow_files.py -v
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

WORKFLOWS = sorted((Path(__file__).resolve().parents[2] / ".github" / "workflows").glob("*.y*ml"))


def test_the_repository_has_workflows():
    assert {p.name for p in WORKFLOWS} >= {"ci.yml", "deploy.yml", "eval-real.yml"}


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_is_valid_yaml_with_triggers_and_jobs(path: Path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), path.name
    triggers = data.get("on", data.get(True))  # PyYAML reads the bare key `on` as the boolean True
    assert data.get("name") and triggers, f"{path.name}: needs a name and triggers"
    jobs = data.get("jobs")
    assert isinstance(jobs, dict) and jobs, f"{path.name}: no jobs"
    for job_id, job in jobs.items():
        for step in job.get("steps", []):
            assert isinstance(step.get("name", ""), str), f"{path.name}: job {job_id} has a step name that is not text"
