"""Tests for Phase 20 Swing Trade module.

Covers:
- Signal classification thresholds (unit — no HTTP)
- compute_signals against a fakeredis instance
- CRUD endpoints (POST/GET/PATCH close/DELETE) — happy path + 404s
- Auth enforcement on /swing-trade endpoints
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import fakeredis.aioredis
import pytest
import pytest_asyncio

from tests.conftest import register_verify_and_login


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_redis_ticker(
    redis,
    ticker: str,
    current: float,
    high_30d: float,
    dy: float | None = 6.0,
):
    """Populate Redis with quote + historical + fundamentals for a ticker.

    The high_30d value is applied to a synthetic point timestamped "yesterday"
    so it lives inside the 30-day window.
    """
    now = datetime.now(timezone.utc)
    yesterday_epoch = int((now - timedelta(days=1)).timestamp())

    quote_payload = {
        "symbol": ticker,
        "price": str(current),
        "change": "0",
        "change_pct": "0",
        "fetched_at": now.isoformat(),
        "data_stale": False,
    }
    await redis.set(f"market:quote:{ticker}", json.dumps(quote_payload))

    historical_payload = {
        "ticker": ticker,
        "points": [
            {
                "date": yesterday_epoch,
                "open": str(high_30d),
                "high": str(high_30d),
                "low": str(high_30d * 0.95),
                "close": str(current),
                "volume": 1000,
            }
        ],
        "fetched_at": now.isoformat(),
        "data_stale": False,
    }
    await redis.set(f"market:historical:{ticker}", json.dumps(historical_payload))

    fundamentals_payload = {
        "ticker": ticker,
        "pl": None,
        "pvp": None,
        "dy": str(dy) if dy is not None else None,
        "ev_ebitda": None,
        "fetched_at": now.isoformat(),
        "data_stale": False,
    }
    await redis.set(
        f"market:fundamentals:{ticker}", json.dumps(fundamentals_payload)
    )


# ---------------------------------------------------------------------------
# Unit tests — signal classification
# ---------------------------------------------------------------------------


class TestSignalClassification:
    def test_buy_when_drop_exceeds_12_and_dy_above_5(self):
        from app.modules.swing_trade.service import _classify_signal

        assert _classify_signal(-15.0, Decimal("6.5")) == "buy"

    def test_neutral_when_drop_under_12(self):
        from app.modules.swing_trade.service import _classify_signal

        assert _classify_signal(-8.0, Decimal("6.5")) == "neutral"

    def test_neutral_when_dy_below_floor(self):
        from app.modules.swing_trade.service import _classify_signal

        assert _classify_signal(-15.0, Decimal("3.0")) == "neutral"

    def test_buy_when_dy_unknown_and_drop_big(self):
        from app.modules.swing_trade.service import _classify_signal

        # Unknown DY should NOT mask a genuine 30d dip
        assert _classify_signal(-15.0, None) == "buy"

    def test_exactly_twelve_percent_triggers_buy(self):
        from app.modules.swing_trade.service import _classify_signal

        assert _classify_signal(-12.0, Decimal("6.0")) == "buy"

    def test_enrich_sell_signal_on_10pct_gain(self):
        from app.modules.swing_trade.models import SwingTradeOperation
        from app.modules.swing_trade.service import _enrich_operation

        op = SwingTradeOperation(
            id=str(uuid.uuid4()),
            tenant_id="t",
            ticker="PETR4",
            asset_class="acao",
            quantity=Decimal("100"),
            entry_price=Decimal("30"),
            entry_date=datetime.now(timezone.utc) - timedelta(days=5),
            target_price=Decimal("40"),
            stop_price=Decimal("27"),
            status="open",
            created_at=datetime.now(timezone.utc),
        )
        resp = _enrich_operation(op, Decimal("33"))
        assert resp.live_signal == "sell"
        assert pytest.approx(resp.pnl_pct, rel=1e-3) == 10.0
        assert pytest.approx(resp.pnl_brl, rel=1e-3) == 300.0
        assert resp.days_open >= 4

    def test_enrich_stop_signal_when_price_below_stop(self):
        from app.modules.swing_trade.models import SwingTradeOperation
        from app.modules.swing_trade.service import _enrich_operation

        op = SwingTradeOperation(
            id=str(uuid.uuid4()),
            tenant_id="t",
            ticker="PETR4",
            asset_class="acao",
            quantity=Decimal("100"),
            entry_price=Decimal("30"),
            entry_date=datetime.now(timezone.utc),
            target_price=Decimal("40"),
            stop_price=Decimal("27"),
            status="open",
            created_at=datetime.now(timezone.utc),
        )
        resp = _enrich_operation(op, Decimal("26"))
        assert resp.live_signal == "stop"

    def test_enrich_hold_signal_between_thresholds(self):
        from app.modules.swing_trade.models import SwingTradeOperation
        from app.modules.swing_trade.service import _enrich_operation

        op = SwingTradeOperation(
            id=str(uuid.uuid4()),
            tenant_id="t",
            ticker="PETR4",
            asset_class="acao",
            quantity=Decimal("100"),
            entry_price=Decimal("30"),
            entry_date=datetime.now(timezone.utc),
            target_price=Decimal("40"),
            stop_price=Decimal("27"),
            status="open",
            created_at=datetime.now(timezone.utc),
        )
        resp = _enrich_operation(op, Decimal("31"))
        assert resp.live_signal == "hold"


# ---------------------------------------------------------------------------
# Service-level — compute_signals with fakeredis
# ---------------------------------------------------------------------------


class TestComputeSignals:
    @pytest.mark.anyio
    async def test_buy_signal_appears_in_radar(self):
        from app.modules.swing_trade.service import compute_signals

        redis = fakeredis.aioredis.FakeRedis()
        # PETR4 is in RADAR_ACOES — seed as a deep drop with DY>5
        await _seed_redis_ticker(redis, "PETR4", current=30.0, high_30d=40.0, dy=7.0)

        response = await compute_signals(redis, portfolio_tickers=[])

        petr = [s for s in response.radar_signals if s.ticker == "PETR4"]
        assert len(petr) == 1
        assert petr[0].signal == "buy"
        assert petr[0].discount_pct < -12.0
        assert petr[0].in_portfolio is False

    @pytest.mark.anyio
    async def test_portfolio_ticker_lands_in_portfolio_signals(self):
        from app.modules.swing_trade.service import compute_signals

        redis = fakeredis.aioredis.FakeRedis()
        await _seed_redis_ticker(redis, "VALE3", current=30.0, high_30d=40.0, dy=7.0)

        response = await compute_signals(
            redis,
            portfolio_tickers=["VALE3"],
            portfolio_quantities={"VALE3": Decimal("100")},
        )

        vale_port = [s for s in response.portfolio_signals if s.ticker == "VALE3"]
        vale_radar = [s for s in response.radar_signals if s.ticker == "VALE3"]
        assert len(vale_port) == 1
        assert len(vale_radar) == 0
        assert vale_port[0].in_portfolio is True
        assert vale_port[0].quantity == Decimal("100")
        assert vale_port[0].signal == "buy"

    @pytest.mark.anyio
    async def test_stale_cache_skipped(self):
        """Tickers with no Redis data are silently skipped (no crash)."""
        from app.modules.swing_trade.service import compute_signals

        redis = fakeredis.aioredis.FakeRedis()
        response = await compute_signals(redis, portfolio_tickers=[])
        # All radar stocks have stale cache → lists should be empty but valid
        assert response.radar_signals == []
        assert response.portfolio_signals == []


# ---------------------------------------------------------------------------
# Integration — HTTP CRUD
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def authed_swing_client(client, email_stub, fake_redis_async):
    """Registered + logged-in client with swing_trade._get_redis overridden."""
    from app.main import app
    from app.modules.swing_trade.router import _get_redis as swing_get_redis

    app.dependency_overrides[swing_get_redis] = lambda: fake_redis_async
    unique_email = f"swing_{uuid.uuid4().hex[:8]}@example.com"
    await register_verify_and_login(client, email_stub, email=unique_email)
    yield client
    app.dependency_overrides.pop(swing_get_redis, None)


class TestOperationCrud:
    @pytest.mark.anyio
    async def test_create_and_list_operation(self, authed_swing_client):
        payload = {
            "ticker": "petr4",
            "asset_class": "acao",
            "quantity": "100",
            "entry_price": "30.50",
            "entry_date": datetime.now(timezone.utc).isoformat(),
            "target_price": "35.00",
            "stop_price": "28.00",
            "notes": "Test op",
        }
        resp = await authed_swing_client.post("/swing-trade/operations", json=payload)
        assert resp.status_code == 201, resp.text
        created = resp.json()
        assert created["ticker"] == "PETR4"  # uppercased
        assert created["status"] == "open"
        op_id = created["id"]

        # List open
        resp2 = await authed_swing_client.get("/swing-trade/operations?status=open")
        assert resp2.status_code == 200, resp2.text
        listed = resp2.json()
        assert listed["open_count"] >= 1
        assert any(r["id"] == op_id for r in listed["results"])

    @pytest.mark.anyio
    async def test_close_operation(self, authed_swing_client):
        payload = {
            "ticker": "VALE3",
            "asset_class": "acao",
            "quantity": "50",
            "entry_price": "60",
            "entry_date": datetime.now(timezone.utc).isoformat(),
        }
        resp = await authed_swing_client.post("/swing-trade/operations", json=payload)
        assert resp.status_code == 201, resp.text
        op_id = resp.json()["id"]

        close_body = {"exit_price": "72.50"}
        resp2 = await authed_swing_client.patch(
            f"/swing-trade/operations/{op_id}/close", json=close_body
        )
        assert resp2.status_code == 200, resp2.text
        closed = resp2.json()
        assert closed["status"] == "closed"
        assert Decimal(closed["exit_price"]) == Decimal("72.50")
        assert closed["exit_date"] is not None

    @pytest.mark.anyio
    async def test_close_nonexistent_returns_404(self, authed_swing_client):
        fake_id = str(uuid.uuid4())
        resp = await authed_swing_client.patch(
            f"/swing-trade/operations/{fake_id}/close",
            json={"exit_price": "10"},
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_delete_operation(self, authed_swing_client):
        payload = {
            "ticker": "ITUB4",
            "asset_class": "acao",
            "quantity": "30",
            "entry_price": "28",
            "entry_date": datetime.now(timezone.utc).isoformat(),
        }
        resp = await authed_swing_client.post("/swing-trade/operations", json=payload)
        assert resp.status_code == 201
        op_id = resp.json()["id"]

        resp2 = await authed_swing_client.delete(f"/swing-trade/operations/{op_id}")
        assert resp2.status_code == 204

        # Soft-deleted row should no longer appear in listing
        resp3 = await authed_swing_client.get("/swing-trade/operations")
        assert resp3.status_code == 200
        listed = resp3.json()
        assert not any(r["id"] == op_id for r in listed["results"])

    @pytest.mark.anyio
    async def test_delete_nonexistent_returns_404(self, authed_swing_client):
        resp = await authed_swing_client.delete(
            f"/swing-trade/operations/{uuid.uuid4()}"
        )
        assert resp.status_code == 404


class TestSignalsEndpoint:
    @pytest.mark.anyio
    async def test_signals_endpoint_returns_structure(
        self, authed_swing_client, fake_redis_async
    ):
        # Seed one radar ticker
        await _seed_redis_ticker(
            fake_redis_async, "PETR4", current=30.0, high_30d=40.0, dy=7.0
        )
        resp = await authed_swing_client.get("/swing-trade/signals")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "portfolio_signals" in data
        assert "radar_signals" in data
        assert "generated_at" in data
        # PETR4 should surface as a buy in the radar
        tickers = [s["ticker"] for s in data["radar_signals"]]
        assert "PETR4" in tickers


class TestAuthRequired:
    @pytest.mark.anyio
    async def test_signals_unauth_returns_401(self, client):
        resp = await client.get("/swing-trade/signals")
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_operations_list_unauth_returns_401(self, client):
        resp = await client.get("/swing-trade/operations")
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_create_unauth_returns_401(self, client):
        resp = await client.post(
            "/swing-trade/operations",
            json={
                "ticker": "PETR4",
                "quantity": "1",
                "entry_price": "30",
                "entry_date": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert resp.status_code == 401
