"""Load engagement-owned Python files named in engagement.yaml (seed scripts, fake-model scripts).

ADR-004: config first; engagement code only where config cannot express it (generating synthetic data, scripting an
offline fake model). That code lives in engagements/<name>/extensions/, so core/ stays the same for every customer.
Paths are relative to the repo root, like every path in engagement.yaml. Each file is loaded once per process.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from types import ModuleType

from core.config import resolve_path

_cache: dict[str, ModuleType] = {}


def load_module(relative_path: str) -> ModuleType:
    path = resolve_path(relative_path).resolve()
    key = str(path)
    if key in _cache:
        return _cache[key]
    if not path.is_file():
        raise FileNotFoundError(f"Engagement extension not found: {relative_path}")
    name = "fde_ext_" + hashlib.sha256(key.encode()).hexdigest()[:12]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses and pydantic look the module up by name while it loads
    spec.loader.exec_module(module)
    _cache[key] = module
    return module
