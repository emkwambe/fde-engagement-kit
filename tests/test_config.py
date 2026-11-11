from pathlib import Path

import pytest
import yaml

from core.config import ConfigError, load_engagement


def test_demo_config_loads_in_fake_mode(demo_cfg):
    assert demo_cfg.engagement.name == "demo-logistics"
    assert demo_cfg.llm.provider == "fake"
    assert demo_cfg.embeddings.provider == "fake"
    assert demo_cfg.retrieval.chunk_overlap < demo_cfg.retrieval.chunk_size


def test_template_config_is_valid():
    cfg = load_engagement(path=Path("engagements/_template/engagement.yaml"))
    assert cfg.engagement.name == "customer-slug"


def _write(tmp_path: Path, mutate) -> Path:
    raw = yaml.safe_load(Path("engagements/demo-logistics/engagement.yaml").read_text())
    mutate(raw)
    p = tmp_path / "engagement.yaml"
    p.write_text(yaml.safe_dump(raw))
    return p


def test_unknown_key_is_rejected(tmp_path):
    p = _write(tmp_path, lambda r: r["retrieval"].update(top_kk=3))
    with pytest.raises(ConfigError, match="top_kk"):
        load_engagement(path=p)


def test_overlap_must_be_smaller_than_size(tmp_path):
    p = _write(tmp_path, lambda r: r["retrieval"].update(chunk_size=200, chunk_overlap=200))
    with pytest.raises(ConfigError, match="chunk_overlap"):
        load_engagement(path=p)


def test_missing_database_url_is_a_clear_error(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL")
    p = _write(tmp_path, lambda r: None)
    with pytest.raises(ConfigError, match="DATABASE_URL"):
        load_engagement(path=p)


def test_env_default_syntax(tmp_path, monkeypatch):
    monkeypatch.delenv("ERP_API_URL", raising=False)
    p = _write(tmp_path, lambda r: r["tools"]["openapi"][0].update(base_url="${ERP_API_URL:-http://x:1}"))
    assert load_engagement(path=p).tools.openapi[0].base_url == "http://x:1"
