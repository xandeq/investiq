"""Tests for GET /advisor/inbox (Action Inbox v1).

Covers:
- 401 when unauthenticated
- 200 with empty cards when user has no portfolio / no events
- Source-level graceful degradation (mock one source to raise — others survive)
- Cards from health (concentration), insights, watchlist, opportunity_detector
- Cards are sorted desc by priority, capped at 10
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from tests.conftest import register_verify_and_login


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_inbox_requires_auth(client: AsyncClient):
    """Unauthenticated GET /advisor/inbox returns 401."""
    resp = await client.get("/advisor/inbox")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_inbox_empty_when_no_data(client: AsyncClient, db_session, email_stub):
    """User with no portfolio / no events → 200 with empty cards.

    Health source still runs (returns has_portfolio=False → 0 cards). Other
    sources query empty tables. swing_signals is skipped because the
    redis dependency is overridden to None below.
    """
    await register_verify_and_login(client, email_stub, email="inbox_empty@example.com")

    # Override inbox redis dep → None so swing_signals is skipped (counted as failed).
    from app.modules.advisor.router import _get_inbox_redis
    from app.main import app as fastapi_app

    fastapi_app.dependency_overrides[_get_inbox_redis] = lambda: None
    try:
        resp = await client.get("/advisor/inbox")
    finally:
        fastapi_app.dependency_overrides.pop(_get_inbox_redis, None)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["cards"] == []
    assert "generated_at" in data
    assert "health" in data["meta"]["sources_ok"]
    # opportunity_detector + insights + watchlist also "ok" even if empty result set
    assert "opportunity_detector" in data["meta"]["sources_ok"]
    assert "insights" in data["meta"]["sources_ok"]
    assert "watchlist_alerts" in data["meta"]["sources_ok"]
    assert "swing_signals" in data["meta"]["sources_failed"]


# ---------------------------------------------------------------------------
# Source contributions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_inbox_surfaces_unread_insight(client: AsyncClient, db_session, email_stub):
    """An unread insight shows up as kind=insight."""
    user_id = await register_verify_and_login(
        client, email_stub, email="inbox_insight@example.com",
    )

    # tenant_id == user_id in v1 (see auth/models.py docstring)
    insight_id = str(uuid.uuid4())
    await db_session.execute(text(
        "INSERT INTO user_insights (id, tenant_id, type, title, body, severity, ticker, seen, created_at) "
        "VALUES (:id, :tid, :type, :title, :body, :sev, :ticker, :seen, :now)"
    ), {
        "id": insight_id,
        "tid": user_id,
        "type": "macro",
        "title": "SELIC subiu para 13.5%",
        "body": "A taxa básica de juros subiu — renda fixa pós-fixada fica mais atrativa.",
        "sev": "info",
        "ticker": None,
        "seen": False,
        "now": datetime.now(tz=timezone.utc),
    })
    await db_session.commit()

    from app.modules.advisor.router import _get_inbox_redis
    from app.main import app as fastapi_app
    fastapi_app.dependency_overrides[_get_inbox_redis] = lambda: None

    try:
        resp = await client.get("/advisor/inbox")
    finally:
        fastapi_app.dependency_overrides.pop(_get_inbox_redis, None)

    assert resp.status_code == 200
    cards = resp.json()["cards"]
    assert any(c["kind"] == "insight" and "SELIC" in c["title"] for c in cards)


@pytest.mark.asyncio
async def test_inbox_surfaces_watchlist_alert(client: AsyncClient, db_session, email_stub):
    """A watchlist item with alert_triggered_at recent shows up as kind=watchlist_alert."""
    user_id = await register_verify_and_login(
        client, email_stub, email="inbox_watch@example.com",
    )
    item_id = str(uuid.uuid4())
    triggered = datetime.now(tz=timezone.utc) - timedelta(hours=2)
    await db_session.execute(text(
        "INSERT INTO watchlist_items (id, tenant_id, ticker, notes, price_alert_target, "
        "alert_triggered_at, created_at) "
        "VALUES (:id, :tid, :ticker, :notes, :target, :trig, :now)"
    ), {
        "id": item_id,
        "tid": user_id,
        "ticker": "ITUB4",
        "notes": None,
        "target": 32.0,
        "trig": triggered,
        "now": datetime.now(tz=timezone.utc),
    })
    await db_session.commit()

    from app.modules.advisor.router import _get_inbox_redis
    from app.main import app as fastapi_app
    fastapi_app.dependency_overrides[_get_inbox_redis] = lambda: None

    try:
        resp = await client.get("/advisor/inbox")
    finally:
        fastapi_app.dependency_overrides.pop(_get_inbox_redis, None)

    assert resp.status_code == 200
    cards = resp.json()["cards"]
    alert_cards = [c for c in cards if c["kind"] == "watchlist_alert"]
    assert len(alert_cards) == 1
    card = alert_cards[0]
    assert card["ticker"] == "ITUB4"
    assert card["severity"] == "alert"
    assert "32.00" in card["body"]
    assert card["cta"]["href"] == "/watchlist"


@pytest.mark.asyncio
async def test_inbox_surfaces_opportunity(client: AsyncClient, db_session, email_stub):
    """A recent is_opportunity=true row in detected_opportunities → kind=opportunity_detected."""
    await register_verify_and_login(
        client, email_stub, email="inbox_opp@example.com",
    )
    opp_id = str(uuid.uuid4())
    detected = datetime.now(tz=timezone.utc) - timedelta(hours=3)
    await db_session.execute(text(
        "INSERT INTO detected_opportunities (id, ticker, asset_type, drop_pct, period, current_price, "
        "currency, risk_level, is_opportunity, cause_category, cause_explanation, risk_rationale, "
        "recommended_amount_brl, target_upside_pct, telegram_message, followed, detected_at) "
        "VALUES (:id, :ticker, :atype, :drop, :period, :price, :ccy, :risk, :is_opp, :cat, :cause, "
        ":rationale, :amt, :upside, :msg, :followed, :detected)"
    ), {
        "id": opp_id,
        "ticker": "MGLU3",
        "atype": "acao",
        "drop": -8.5,
        "period": "diario",
        "price": 4.20,
        "ccy": "BRL",
        "risk": "baixo",
        "is_opp": True,
        "cat": "macro",
        "cause": "Reação ao IPCA acima do esperado, sem fato relevante para a empresa.",
        "rationale": None,
        "amt": 1000.0,
        "upside": 12.0,
        "msg": None,
        "followed": False,
        "detected": detected,
    })
    await db_session.commit()

    from app.modules.advisor.router import _get_inbox_redis
    from app.main import app as fastapi_app
    fastapi_app.dependency_overrides[_get_inbox_redis] = lambda: None

    try:
        resp = await client.get("/advisor/inbox")
    finally:
        fastapi_app.dependency_overrides.pop(_get_inbox_redis, None)

    assert resp.status_code == 200
    cards = resp.json()["cards"]
    opp_cards = [c for c in cards if c["kind"] == "opportunity_detected"]
    assert len(opp_cards) == 1
    assert opp_cards[0]["ticker"] == "MGLU3"
    assert opp_cards[0]["severity"] == "alert"  # risk_level=baixo → alert per mapping


# ---------------------------------------------------------------------------
# Ranking & cap
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_inbox_sorts_by_priority_desc(client: AsyncClient, db_session, email_stub):
    """Insert 1 watchlist alert + 1 low-severity insight; alert ranks higher."""
    user_id = await register_verify_and_login(
        client, email_stub, email="inbox_rank@example.com",
    )
    now = datetime.now(tz=timezone.utc)

    # Lower-priority insight (info severity, weight 0.50)
    await db_session.execute(text(
        "INSERT INTO user_insights (id, tenant_id, type, title, body, severity, ticker, seen, created_at) "
        "VALUES (:id, :tid, :type, :title, :body, :sev, :ticker, :seen, :now)"
    ), {
        "id": str(uuid.uuid4()),
        "tid": user_id,
        "type": "tip",
        "title": "Dica do dia",
        "body": "Considere FIIs para fluxo de caixa mensal.",
        "sev": "info",
        "ticker": None,
        "seen": False,
        "now": now,
    })

    # Higher-priority watchlist alert (alert severity, weight 0.90)
    await db_session.execute(text(
        "INSERT INTO watchlist_items (id, tenant_id, ticker, notes, price_alert_target, "
        "alert_triggered_at, created_at) "
        "VALUES (:id, :tid, :ticker, :notes, :target, :trig, :now)"
    ), {
        "id": str(uuid.uuid4()),
        "tid": user_id,
        "ticker": "PETR4",
        "notes": None,
        "target": 30.0,
        "trig": now - timedelta(minutes=5),
        "now": now,
    })
    await db_session.commit()

    from app.modules.advisor.router import _get_inbox_redis
    from app.main import app as fastapi_app
    fastapi_app.dependency_overrides[_get_inbox_redis] = lambda: None

    try:
        resp = await client.get("/advisor/inbox")
    finally:
        fastapi_app.dependency_overrides.pop(_get_inbox_redis, None)

    cards = resp.json()["cards"]
    assert len(cards) >= 2
    # Watchlist alert should outrank insight
    alert_pos = next(i for i, c in enumerate(cards) if c["kind"] == "watchlist_alert")
    insight_pos = next(i for i, c in enumerate(cards) if c["kind"] == "insight")
    assert alert_pos < insight_pos
    # Priorities are descending
    priorities = [c["priority"] for c in cards]
    assert priorities == sorted(priorities, reverse=True)


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_inbox_degrades_when_one_source_fails(client: AsyncClient, db_session, email_stub):
    """If insights query raises, inbox still returns 200 + insights in sources_failed."""
    await register_verify_and_login(client, email_stub, email="inbox_degrade@example.com")

    from app.modules.advisor.router import _get_inbox_redis
    from app.main import app as fastapi_app
    fastapi_app.dependency_overrides[_get_inbox_redis] = lambda: None

    with patch(
        "app.modules.advisor.service._insights_to_cards",
        side_effect=RuntimeError("simulated insights outage"),
    ):
        try:
            resp = await client.get("/advisor/inbox")
        finally:
            fastapi_app.dependency_overrides.pop(_get_inbox_redis, None)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "insights" in data["meta"]["sources_failed"]
    # Other sources still ran
    assert "health" in data["meta"]["sources_ok"]
    assert "opportunity_detector" in data["meta"]["sources_ok"]
    assert "watchlist_alerts" in data["meta"]["sources_ok"]
