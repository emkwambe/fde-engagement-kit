from datetime import UTC, datetime
from decimal import Decimal

import pytest

from core.ingest.etl import RowError, clean_money, clean_tier, clean_ts


@pytest.mark.parametrize("raw,expected", [("Gold", "Gold"), ("gold ", "Gold"), ("GOLD", "Gold"),
                                          (" platinum", "Platinum")])
def test_clean_tier_normalizes(raw, expected):
    assert clean_tier(raw) == expected


def test_clean_tier_rejects_unknown():
    with pytest.raises(RowError):
        clean_tier("Bronze")


def test_clean_ts_formats():
    iso = clean_ts("2026-10-28T09:30:00+00:00")
    us = clean_ts("10/28/2026 09:30")
    assert iso == us == datetime(2026, 10, 28, 9, 30, tzinfo=UTC)
    assert clean_ts("", required=False) is None
    with pytest.raises(RowError):
        clean_ts("")
    with pytest.raises(RowError):
        clean_ts("next tuesday")


def test_clean_money():
    assert clean_money("$1,234.5") == Decimal("1234.50")
    assert clean_money("99") == Decimal("99.00")
    with pytest.raises(RowError):
        clean_money("abc")
