"""Tests for market data Celery tasks, Redis service, and market data router.

Tests cover:
- refresh_quotes Celery task writing to fakeredis
- refresh_macro Celery task writing to fakeredis
- MarketDataService reads from async fakeredis
- data_stale=True when cache keys are missing
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio


def test_celery_broker_alive():
    """Celery app can be imported and broker URL is configured.

    Does not require a live Redis — checks configuration only.
    celery_app.py is created in Task 2 of this plan.
    """
    try:
        from app.celery_app import celery_app
    except ImportError:
        pytest.skip("app.celery_app not yet created (Task 2)")

    assert celery_app.conf.broker_url is not None
    assert celery_app.conf.broker_url.startswith("redis://")
    assert "refresh-quotes-market-hours" in celery_app.conf.beat_schedule
    assert "refresh-macro-every-6h" in celery_app.conf.beat_schedule


def test_beat_schedule_expires_configured():
    """Every periodic task must carry an `expires` option to prevent queue starvation.

    Root cause of P0 (Apr 2026): scan_crypto + cleanup_stale_runs accumulated 344 tasks
    in the queue because workers were busy with screener tasks. The expires option
    causes Celery to discard stale copies rather than letting the queue grow unbounded.
    """
    from app.celery_app import celery_app

    schedule = celery_app.conf.beat_schedule

    # Tasks with no natural expiry concern (rare non-repeating ops) may be exempt,
    # but all high-frequency and scheduled tasks must have expires.
    required = [
        "refresh-quotes-market-hours",
        "refresh-macro-every-6h",
        "cleanup-stale-screener-runs",
        "opportunity-detector-crypto",
        "opportunity-detector-acoes",
        "check-price-alerts",
        "refresh-tesouro-rates-6h",
    ]
    for name in required:
        entry = schedule[name]
        expires = entry.get("options", {}).get("expires")
        assert expires is not None and expires > 0, (
            f"Beat entry '{name}' is missing options.expires — "
            "add it to prevent queue starvation (see P0_INVESTIGATION.md)"
        )

    # scan_crypto must be <= 30min to keep 24/7 load manageable.
    # crontab(minute="*/15") fires 96×/day; crontab(minute="*/30") fires 48×/day.
    # Check _orig_minute does not contain "*/15" (or "*/10", "*/5", etc.)
    crypto_schedule = schedule["opportunity-detector-crypto"]["schedule"]
    orig_minute = str(crypto_schedule._orig_minute)
    assert orig_minute not in {"*/15", "*/10", "*/5", "*/1"}, (
        f"scan_crypto fires too often ({orig_minute}/min) — use */30 or slower "
        "to prevent 24/7 queue flood (see P0_INVESTIGATION.md)"
    )

    # check-macro-freshness watchdog must be present in beat schedule
    assert "check-macro-freshness" in schedule, (
        "Macro freshness watchdog is missing from beat_schedule — add it"
    )


# ---------------------------------------------------------------------------
# check_macro_freshness watchdog tests
# ---------------------------------------------------------------------------

def test_macro_watchdog_missing_key(fake_redis_sync):
    """Returns status=missing when market:macro:fetched_at key is absent."""
    from unittest.mock import patch
    from app.modules.market_data.tasks import check_macro_freshness

    with patch("app.modules.market_data.tasks._get_redis", return_value=fake_redis_sync):
        result = check_macro_freshness()

    assert result["status"] == "missing"
    assert result["age_seconds"] is None


def test_macro_watchdog_stale(fake_redis_sync):
    """Returns status=stale when fetched_at is older than 2h."""
    from datetime import timedelta
    from unittest.mock import patch
    from app.modules.market_data.tasks import check_macro_freshness

    stale_ts = (datetime.utcnow() - timedelta(hours=3)).isoformat()
    fake_redis_sync.set("market:macro:fetched_at", stale_ts)

    with patch("app.modules.market_data.tasks._get_redis", return_value=fake_redis_sync):
        result = check_macro_freshness()

    assert result["status"] == "stale"
    assert result["age_seconds"] > 2 * 3600


def test_macro_watchdog_ok(fake_redis_sync):
    """Returns status=ok when fetched_at is recent."""
    from datetime import timedelta
    from unittest.mock import patch
    from app.modules.market_data.tasks import check_macro_freshness

    fresh_ts = (datetime.utcnow() - timedelta(minutes=30)).isoformat()
    fake_redis_sync.set("market:macro:fetched_at", fresh_ts)

    with patch("app.modules.market_data.tasks._get_redis", return_value=fake_redis_sync):
        result = check_macro_freshness()

    assert result["status"] == "ok"
    assert result["age_seconds"] < 2 * 3600


def test_refresh_quotes_writes_redis(fake_redis_sync, mock_brapi_client):
    """Task writes market:quote:PETR4 key to Redis with TTL=1200.

    Mocks brapi.dev HTTP call; verifies Redis key is written with correct TTL.
    """
    from app.modules.market_data.tasks import refresh_quotes
    from app.modules.market_data.adapters.brapi import BrapiClient

    # Mock BrapiClient.fetch_quotes to return PETR4 data
    mock_quotes = [
        {
            "symbol": "PETR4",
            "regularMarketPrice": 38.50,
            "regularMarketChange": 0.50,
            "regularMarketChangePercent": 1.32,
        }
    ]
    mock_ibov = {
        "symbol": "^BVSP",
        "regularMarketPrice": 128000.0,
        "regularMarketChange": 500.0,
        "regularMarketChangePercent": 0.39,
    }
    mock_fundamentals = {
        "pl": 7.5,
        "pvp": 1.2,
        "dy": 0.085,
        "ev_ebitda": 4.2,
    }

    with patch.object(BrapiClient, "fetch_quotes", return_value=mock_quotes):
        with patch.object(BrapiClient, "fetch_ibovespa", return_value=mock_ibov):
            with patch.object(BrapiClient, "fetch_fundamentals", return_value=mock_fundamentals):
                # Patch redis.Redis.from_url to return our fakeredis instance
                with patch("redis.Redis.from_url", return_value=fake_redis_sync):
                    refresh_quotes.apply()

    raw = fake_redis_sync.get("market:quote:PETR4")
    assert raw is not None, "market:quote:PETR4 key was not written to Redis"

    data = json.loads(raw)
    assert data["symbol"] == "PETR4"
    assert data["price"] == 38.50
    assert data["change"] == 0.50
    assert data["change_pct"] == 1.32

    # Check TTL is approximately 1200 (fakeredis stores TTL)
    ttl = fake_redis_sync.ttl("market:quote:PETR4")
    assert 1190 <= ttl <= 1200, f"Expected TTL ~1200, got {ttl}"


def test_brapi_client_writes_redis(fake_redis_sync):
    """brapi adapter fetches quote and writes to Redis via refresh_quotes task."""
    from app.modules.market_data.tasks import refresh_quotes
    from app.modules.market_data.adapters.brapi import BrapiClient

    mock_quotes = [
        {
            "symbol": "VALE3",
            "regularMarketPrice": 65.20,
            "regularMarketChange": -0.30,
            "regularMarketChangePercent": -0.46,
        }
    ]
    mock_fundamentals = {
        "pl": 5.8,
        "pvp": None,
        "dy": None,
        "ev_ebitda": None,
    }

    with patch.object(BrapiClient, "fetch_quotes", return_value=mock_quotes):
        with patch.object(BrapiClient, "fetch_ibovespa", return_value={"symbol": "^BVSP", "regularMarketPrice": 128000.0, "regularMarketChange": 0.0, "regularMarketChangePercent": 0.0}):
            with patch.object(BrapiClient, "fetch_fundamentals", return_value=mock_fundamentals):
                with patch("redis.Redis.from_url", return_value=fake_redis_sync):
                    refresh_quotes.apply()

    raw = fake_redis_sync.get("market:quote:VALE3")
    assert raw is not None, "market:quote:VALE3 key was not written"
    data = json.loads(raw)
    assert data["price"] == 65.20

    ibov_raw = fake_redis_sync.get("market:quote:IBOV")
    assert ibov_raw is not None, "market:quote:IBOV key was not written"
    ibov_data = json.loads(ibov_raw)
    assert ibov_data["symbol"] == "IBOV"
    assert ibov_data["price"] == 128000.0
    assert ibov_data["change"] == 0.0
    assert ibov_data["change_pct"] == 0.0


def test_refresh_macro_writes_redis(fake_redis_sync):
    """refresh_macro task writes macro indicators to Redis with TTL=25200."""
    from app.modules.market_data.tasks import refresh_macro
    from decimal import Decimal

    mock_macro = {
        "selic": Decimal("13.75"),
        "cdi": Decimal("13.65"),
        "ipca": Decimal("0.52"),
        "ptax_usd": Decimal("5.25"),
        "fetched_at": "2024-01-31T12:00:00",
    }

    with patch("app.modules.market_data.tasks.fetch_macro_indicators", return_value=mock_macro):
        with patch("redis.Redis.from_url", return_value=fake_redis_sync):
            refresh_macro.apply()

    # Check each indicator was written
    assert fake_redis_sync.get("market:macro:selic") is not None
    assert fake_redis_sync.get("market:macro:cdi") is not None
    assert fake_redis_sync.get("market:macro:ipca") is not None
    assert fake_redis_sync.get("market:macro:ptax_usd") is not None

    # Verify TTL is approximately 25200
    ttl = fake_redis_sync.ttl("market:macro:selic")
    assert 25190 <= ttl <= 25200, f"Expected TTL ~25200, got {ttl}"

    # Verify value
    selic_val = fake_redis_sync.get("market:macro:selic")
    assert selic_val is not None
    assert "13.75" in selic_val.decode()


@pytest.mark.asyncio
async def test_macro_from_redis(fake_redis_async):
    """MarketDataService.get_macro() reads assembled macro data from Redis."""
    from app.modules.market_data.service import MarketDataService

    # Pre-populate Redis with macro data
    await fake_redis_async.set("market:macro:selic", "13.75", ex=25200)
    await fake_redis_async.set("market:macro:cdi", "13.65", ex=25200)
    await fake_redis_async.set("market:macro:ipca", "0.52", ex=25200)
    await fake_redis_async.set("market:macro:ptax_usd", "5.25", ex=25200)
    await fake_redis_async.set("market:macro:fetched_at", "2024-01-31T12:00:00", ex=25200)

    service = MarketDataService(fake_redis_async)
    macro = await service.get_macro()

    assert macro.selic == Decimal("13.75")
    assert macro.cdi == Decimal("13.65")
    assert macro.ipca == Decimal("0.52")
    assert macro.ptax_usd == Decimal("5.25")
    assert macro.data_stale is False


@pytest.mark.asyncio
async def test_macro_from_redis_stale_when_empty(fake_redis_async):
    """MarketDataService.get_macro() returns data_stale=True when cache is empty."""
    from app.modules.market_data.service import MarketDataService

    service = MarketDataService(fake_redis_async)
    macro = await service.get_macro()

    assert macro.data_stale is True


@pytest.mark.asyncio
async def test_fundamentals_from_redis(fake_redis_async):
    """MarketDataService.get_fundamentals() reads fundamentals from Redis."""
    import json
    from app.modules.market_data.service import MarketDataService
    from app.modules.market_data.schemas import FundamentalsCache

    fund_data = FundamentalsCache(
        ticker="PETR4",
        pl=Decimal("7.5"),
        pvp=Decimal("1.2"),
        dy=Decimal("0.085"),
        ev_ebitda=Decimal("4.2"),
        fetched_at=datetime(2024, 1, 31, 12, 0, 0),
        data_stale=False,
    )

    await fake_redis_async.set(
        "market:fundamentals:PETR4",
        fund_data.model_dump_json(),
        ex=86400,
    )

    service = MarketDataService(fake_redis_async)
    result = await service.get_fundamentals("PETR4")

    assert result.ticker == "PETR4"
    assert result.pl == Decimal("7.5")
    assert result.pvp == Decimal("1.2")
    assert result.data_stale is False


@pytest.mark.asyncio
async def test_fundamentals_stale_when_cache_empty(fake_redis_async):
    """MarketDataService.get_fundamentals() returns data_stale=True on cache miss."""
    from app.modules.market_data.service import MarketDataService

    service = MarketDataService(fake_redis_async)
    result = await service.get_fundamentals("UNKNWN")

    assert result.data_stale is True
    assert result.ticker == "UNKNWN"


@pytest.mark.asyncio
async def test_historical_from_redis(fake_redis_async):
    """MarketDataService.get_historical() reads OHLCV data from Redis."""
    from app.modules.market_data.service import MarketDataService
    from app.modules.market_data.schemas import HistoricalCache, HistoricalPoint

    hist_data = HistoricalCache(
        ticker="PETR4",
        points=[
            HistoricalPoint(
                date=1700000000,
                open=Decimal("38.0"),
                high=Decimal("39.0"),
                low=Decimal("37.0"),
                close=Decimal("38.5"),
                volume=1000000,
            )
        ],
        fetched_at=datetime(2024, 1, 31, 12, 0, 0),
        data_stale=False,
    )

    await fake_redis_async.set(
        "market:historical:PETR4",
        hist_data.model_dump_json(),
        ex=86400,
    )

    service = MarketDataService(fake_redis_async)
    result = await service.get_historical("PETR4")

    assert result.ticker == "PETR4"
    assert len(result.points) == 1
    assert result.points[0].close == Decimal("38.5")
    assert result.data_stale is False


@pytest.mark.asyncio
async def test_quote_stale_when_cache_empty(fake_redis_async):
    """MarketDataService.get_quote() returns data_stale=True when cache is empty."""
    from app.modules.market_data.service import MarketDataService

    service = MarketDataService(fake_redis_async)
    result = await service.get_quote("PETR4")

    assert result.data_stale is True
    assert result.symbol == "PETR4"
    assert result.price == Decimal("0")


@pytest.mark.asyncio
async def test_quote_from_legacy_redis_shape(fake_redis_async):
    """MarketDataService tolerates old quote payloads with regularMarket* keys."""
    from app.modules.market_data.service import MarketDataService

    await fake_redis_async.set(
        "market:quote:IBOV",
        json.dumps({
            "symbol": "^BVSP",
            "regularMarketPrice": 128000.0,
            "regularMarketChange": 500.0,
            "regularMarketChangePercent": 0.39,
        }),
        ex=1200,
    )

    service = MarketDataService(fake_redis_async)
    result = await service.get_quote("IBOV")

    assert result.symbol == "IBOV"
    assert result.price == Decimal("128000.0")
    assert result.change == Decimal("500.0")
    assert result.change_pct == Decimal("0.39")
    assert result.data_stale is False
