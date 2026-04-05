"""Unit tests for market_universe Celery beat tasks.

All tests use mocks — no real external API calls, no real DB, no real Redis.

Tests cover:
  - Beat schedule registration for all 3 tasks
  - includes list registration
  - Redis namespace isolation (no market:* collision)
  - refresh_screener_universe DB write path (mock brapi + fakeredis + mock session)
  - refresh_tesouro_rates ANBIMA-to-CKAN fallback path
"""
from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch, call

import fakeredis
import pytest

# ---------------------------------------------------------------------------
# Beat schedule tests (no mocking needed — just import celery_app)
# ---------------------------------------------------------------------------

def test_screener_beat_schedule_registered():
    """refresh_screener_universe must be registered with Mon-Fri 7h schedule."""
    from app.celery_app import celery_app
    from celery.schedules import crontab

    sched = celery_app.conf.beat_schedule
    assert "refresh-screener-universe-daily" in sched, (
        "refresh-screener-universe-daily missing from beat_schedule"
    )
    entry = sched["refresh-screener-universe-daily"]
    assert entry["task"] == "app.modules.market_universe.tasks.refresh_screener_universe"
    # Compare string representation — crontab equality check
    expected = crontab(minute=0, hour=7, day_of_week="1-5")
    assert str(entry["schedule"]) == str(expected), (
        f"Screener schedule mismatch: {entry['schedule']} != {expected}"
    )


def test_fii_beat_schedule_registered():
    """refresh_fii_metadata must be registered with Monday 6h schedule."""
    from app.celery_app import celery_app
    from celery.schedules import crontab

    sched = celery_app.conf.beat_schedule
    assert "refresh-fii-metadata-weekly" in sched, (
        "refresh-fii-metadata-weekly missing from beat_schedule"
    )
    entry = sched["refresh-fii-metadata-weekly"]
    assert entry["task"] == "app.modules.market_universe.tasks.refresh_fii_metadata"
    expected = crontab(minute=0, hour=6, day_of_week="1")
    assert str(entry["schedule"]) == str(expected), (
        f"FII schedule mismatch: {entry['schedule']} != {expected}"
    )


def test_tesouro_beat_schedule_registered():
    """refresh_tesouro_rates must be registered with every-6h schedule."""
    from app.celery_app import celery_app
    from celery.schedules import crontab

    sched = celery_app.conf.beat_schedule
    assert "refresh-tesouro-rates-6h" in sched, (
        "refresh-tesouro-rates-6h missing from beat_schedule"
    )
    entry = sched["refresh-tesouro-rates-6h"]
    assert entry["task"] == "app.modules.market_universe.tasks.refresh_tesouro_rates"
    expected = crontab(minute=0, hour="*/6")
    assert str(entry["schedule"]) == str(expected), (
        f"Tesouro schedule mismatch: {entry['schedule']} != {expected}"
    )


def test_market_universe_in_includes():
    """app.modules.market_universe.tasks must be in Celery includes list."""
    from app.celery_app import celery_app
    assert "app.modules.market_universe.tasks" in celery_app.conf.include, (
        "app.modules.market_universe.tasks not in celery_app.conf.include"
    )


# ---------------------------------------------------------------------------
# Redis namespace isolation
# ---------------------------------------------------------------------------

def test_redis_namespace_isolation():
    """No task Redis prefix may start with 'market:' — that's Phase 2 namespace."""
    from app.modules.market_universe.tasks import (
        _SCREENER_PREFIX,
        _TESOURO_PREFIX,
        _FII_PREFIX,
    )

    assert _SCREENER_PREFIX == "screener:universe:", (
        f"Screener prefix wrong: {_SCREENER_PREFIX!r}"
    )
    assert _TESOURO_PREFIX == "tesouro:rates:", (
        f"Tesouro prefix wrong: {_TESOURO_PREFIX!r}"
    )
    assert _FII_PREFIX == "fii:metadata:", (
        f"FII prefix wrong: {_FII_PREFIX!r}"
    )

    # None of them may collide with the market:* Phase 2 namespace
    for prefix in (_SCREENER_PREFIX, _TESOURO_PREFIX, _FII_PREFIX):
        assert not prefix.startswith("market:"), (
            f"Prefix {prefix!r} starts with 'market:' — namespace collision!"
        )


# ---------------------------------------------------------------------------
# refresh_screener_universe — DB write path (mocked)
# ---------------------------------------------------------------------------

def test_refresh_screener_universe_writes_db(fake_redis_sync):
    """refresh_screener_universe should call session.execute with pg_insert and write to Redis."""
    from app.modules.market_universe.tasks import refresh_screener_universe

    # Fake ticker list response from brapi /quote/list
    fake_list_response = {"stocks": [{"stock": "PETR4"}], "hasNextPage": False}

    # Fake fundamentals response — matches BrapiClient.fetch_fundamentals return dict
    fake_fundamentals = {
        "pl": 8.5,
        "pvp": 1.2,
        "dy": 0.045,
        "ev_ebitda": 6.3,
        "shortName": "PETROBRAS ON",
        "sector": "Energy",
        "regularMarketPrice": 38.5,
        "regularMarketChangePercent": 1.2,
        "regularMarketVolume": 10_000_000,
        "marketCap": 500_000_000_000,
    }

    # Mock session — just needs to not raise
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)

    with (
        patch("app.modules.market_universe.tasks._get_redis", return_value=fake_redis_sync),
        patch(
            "app.modules.market_universe.tasks._get_brapi_client",
        ) as mock_brapi_factory,
        patch(
            "app.modules.market_universe.tasks.get_sync_db_session",
            return_value=mock_session,
        ),
        patch("time.sleep"),  # Skip 200ms sleeps
    ):
        mock_brapi = MagicMock()
        mock_brapi._get.return_value = fake_list_response
        mock_brapi.fetch_fundamentals.return_value = fake_fundamentals
        mock_brapi_factory.return_value = mock_brapi

        # Run the task (Celery tasks are just functions when called directly)
        refresh_screener_universe()

    # Session execute should have been called (for the upsert)
    assert mock_session.execute.called, "session.execute was never called — no DB upsert happened"

    # Redis should have a screener:universe:PETR4 key
    value = fake_redis_sync.get("screener:universe:PETR4")
    assert value is not None, "screener:universe:PETR4 not written to Redis"
    payload = json.loads(value)
    assert payload["ticker"] == "PETR4"


# ---------------------------------------------------------------------------
# refresh_tesouro_rates — ANBIMA-to-CKAN fallback path
# ---------------------------------------------------------------------------

def test_refresh_tesouro_rates_anbima_fallback_to_ckan(fake_redis_sync):
    """When ANBIMA fails, refresh_tesouro_rates should fall back to CKAN CSV."""
    from app.modules.market_universe.tasks import refresh_tesouro_rates
    from datetime import date

    today_str = date.today().strftime("%d/%m/%Y")

    # CKAN CSV content — only 2 rows: header + one today row
    fake_csv = (
        "Tipo Titulo;Data Vencimento;Taxa Compra Manha;Taxa Venda Manha;PU Compra Manha;Data Base\n"
        f"Tesouro IPCA+ 2035;15/05/2035;5,12;5,15;3412,50;{today_str}\n"
        # A past row that should be filtered out
        "Tesouro SELIC 2027;01/03/2027;12,50;12,60;10000,00;01/01/2020\n"
    )

    fake_ckan_response = MagicMock()
    fake_ckan_response.text = fake_csv
    fake_ckan_response.raise_for_status = MagicMock()

    with (
        patch("app.modules.market_universe.tasks._get_redis", return_value=fake_redis_sync),
        patch(
            "app.modules.market_universe.tasks._get_anbima_credentials",
            side_effect=RuntimeError("AWS SM unavailable in test"),
        ),
        patch(
            "app.modules.market_universe.tasks.requests_lib.get",
            return_value=fake_ckan_response,
        ),
        patch("time.sleep"),
    ):
        refresh_tesouro_rates()

    # Redis must have a tesouro:rates:* key for the IPCA+ bond
    keys = fake_redis_sync.keys("tesouro:rates:*")
    assert len(keys) >= 1, f"Expected at least 1 tesouro:rates:* key, got {keys}"

    # Check that only today's record was written (not the 2020 row)
    assert len(keys) == 1, f"Expected exactly 1 key (today only), got {len(keys)}: {keys}"

    value = fake_redis_sync.get(keys[0])
    payload = json.loads(value)

    assert payload.get("source") == "ckan", (
        f"Expected source='ckan' (ANBIMA fallback), got {payload.get('source')!r}"
    )
    assert "Tesouro IPCA+" in payload.get("tipo_titulo", ""), (
        f"Unexpected tipo_titulo: {payload.get('tipo_titulo')!r}"
    )
    assert payload.get("data_base") == today_str, (
        f"Expected today ({today_str}), got {payload.get('data_base')!r}"
    )
