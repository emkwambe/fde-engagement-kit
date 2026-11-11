"""Load and validate an engagement config, interpolating ${ENV_VAR} references."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from core.config.schema import EngagementConfig

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGAGEMENTS_DIR = REPO_ROOT / "engagements"
_ENV_REF = re.compile(r"\$\{([A-Z0-9_]+)(?::-([^}]*))?\}")  # ${VAR} or ${VAR:-default}


class ConfigError(Exception):
    """Raised for any problem loading an engagement config. Message is meant for humans."""


def _interpolate(value: Any, missing: set[str]) -> Any:
    if isinstance(value, str):
        def repl(m: re.Match[str]) -> str:
            name, default = m.group(1), m.group(2)
            if name in os.environ and os.environ[name] != "":
                return os.environ[name]
            if default is not None:
                return default
            missing.add(name)
            return ""
        return _ENV_REF.sub(repl, value)
    if isinstance(value, dict):
        return {k: _interpolate(v, missing) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate(v, missing) for v in value]
    return value


def _apply_fake_mode(raw: dict[str, Any]) -> None:
    """FAKE_LLM=1 swaps model providers for deterministic fakes (FR-15) without editing YAML."""
    if os.environ.get("FAKE_LLM", "0") == "1":
        raw.setdefault("llm", {})["provider"] = "fake"
        raw["llm"].setdefault("model", "fake")
        raw.setdefault("embeddings", {})["provider"] = "fake"


def config_path(engagement: str) -> Path:
    return ENGAGEMENTS_DIR / engagement / "engagement.yaml"


def load_engagement(engagement: str | None = None, path: Path | None = None) -> EngagementConfig:
    """Load engagements/<engagement>/engagement.yaml (or an explicit path)."""
    engagement = engagement or os.environ.get("ENGAGEMENT")
    if path is None:
        if not engagement:
            raise ConfigError("No engagement given. Pass --engagement or set ENGAGEMENT.")
        path = config_path(engagement)
    if not path.exists():
        raise ConfigError(f"Config not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    _apply_fake_mode(raw)

    missing: set[str] = set()
    resolved = _interpolate(raw, missing)

    # In fake mode the model name is irrelevant, so an unset LLM_MODEL is not an error.
    if resolved.get("llm", {}).get("provider") == "fake":
        missing.discard("LLM_MODEL")
        resolved["llm"]["model"] = resolved["llm"].get("model") or "fake"

    # Only complain about variables that ended up in fields that need a value.
    required_missing = sorted(v for v in missing if v in {"DATABASE_URL", "LLM_MODEL"})
    if required_missing:
        raise ConfigError(
            f"{path.name}: environment variable(s) not set: {', '.join(required_missing)}. "
            "Add them to .env (see .env.example)."
        )

    try:
        return EngagementConfig.model_validate(resolved)
    except Exception as exc:  # pydantic.ValidationError has a readable str()
        raise ConfigError(f"{path} is invalid:\n{exc}") from exc


def resolve_path(relative: str) -> Path:
    """Paths in engagement.yaml are relative to the repo root."""
    p = Path(relative)
    return p if p.is_absolute() else REPO_ROOT / p
