import pytest

from core.config import resolve_path
from core.ingest.etl import run_tabular_etl
from tests.helpers import generate_logistics, logistics_specs

pytestmark = pytest.mark.db


def test_etl_loads_cleans_and_is_idempotent(conn, demo_cfg):
    folder = resolve_path(demo_cfg.sources.tables[0].path)
    generate_logistics(folder)
    first = {r.table: r for r in run_tabular_etl(conn, "demo-logistics", folder, "ops", logistics_specs())}
    second = {r.table: r for r in run_tabular_etl(conn, "demo-logistics", folder, "ops", logistics_specs())}

    assert first["customers"].rows_loaded == 40          # 41 rows, Bronze rejected
    assert len(first["customers"].rejected) == 1
    assert first["orders"].duplicates == 5
    assert any("C-404" in r["reason"] for r in first["orders"].rejected)
    assert {t: r.rows_loaded for t, r in first.items()} == {t: r.rows_loaded for t, r in second.items()}

    n_orders = conn.execute("SELECT count(*) FROM ops.orders").fetchone()[0]
    assert n_orders == first["orders"].rows_loaded

    days_late, tier = conn.execute(
        "SELECT days_late, tier FROM ops.sla_breaches WHERE order_id = 'ORD-1043'").fetchone()
    assert (days_late, tier) == (3, "Gold")


def test_readonly_role_cannot_write(migrated_db, conn, demo_cfg):
    import psycopg

    folder = resolve_path(demo_cfg.sources.tables[0].path)
    generate_logistics(folder)
    run_tabular_etl(conn, "demo-logistics", folder, "ops", logistics_specs())
    conn.commit()
    ro_url = migrated_db.replace("fde:fde@", "agent_ro:agent_ro@")
    with psycopg.connect(ro_url) as ro:
        assert ro.execute("SELECT count(*) FROM ops.customers").fetchone()[0] > 0
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            ro.execute("DELETE FROM ops.orders")
    with psycopg.connect(ro_url) as ro, pytest.raises(psycopg.errors.InsufficientPrivilege):
        ro.execute("SELECT count(*) FROM kb.chunks")
