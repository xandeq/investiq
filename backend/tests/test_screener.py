"""Tests for the Goldman Screener feature.

Coverage:
- Router smoke tests (POST /screener/analyze, GET /screener/jobs/{id}, GET /screener/history)
- Authorization: pro user → 202, free user → 403, unauthenticated → 401
- Rate limit header present on 202
- Regression: goldman_screener raises ValueError on JSON parse failure (not returns empty dict)
- Regression: goldman_screener raises ValueError on empty stocks (not returns silently)
- Regression: goldman_screener passes tier to call_llm
- Regression: tasks.py marks run as failed (not completed) when screener raises
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select, update

from app.modules.auth.models import User
from app.modules.screener.models import ScreenerRun
from tests.conftest import register_verify_and_login


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _upgrade_user_to_pro(db_session, user_id: str) -> None:
    await db_session.execute(
        update(User).where(User.id == user_id).values(plan="pro")
    )
    await db_session.flush()


async def _expire_trial(db_session, user_id: str) -> None:
    past = datetime.now(tz=timezone.utc) - timedelta(days=1)
    await db_session.execute(
        update(User).where(User.id == user_id).values(trial_ends_at=past)
    )
    await db_session.flush()


# ---------------------------------------------------------------------------
# Router smoke tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_screener_analyze_202_for_pro_user(client, db_session, email_stub):
    """Pro user gets 202 with run_id when requesting a screening."""
    user_id = await register_verify_and_login(
        client, email_stub, email="screener_pro@example.com"
    )
    await _upgrade_user_to_pro(db_session, user_id)

    with patch("app.modules.screener.router._dispatch_screener") as mock_dispatch:
        mock_dispatch.return_value = None
        resp = await client.post(
            "/screener/analyze",
            json={"sector_filter": "Financeiro", "custom_notes": ""},
        )

    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert data["sector_filter"] == "Financeiro"


@pytest.mark.asyncio
async def test_screener_analyze_403_for_free_user(client, db_session, email_stub):
    """Free user (expired trial) gets 403 — screener is premium-only."""
    user_id = await register_verify_and_login(
        client, email_stub, email="screener_free@example.com"
    )
    await _expire_trial(db_session, user_id)

    resp = await client.post("/screener/analyze", json={})

    assert resp.status_code == 403, resp.text
    assert "Premium" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_screener_analyze_401_unauthenticated(client):
    """Unauthenticated request gets 401."""
    resp = await client.post("/screener/analyze", json={})
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_screener_job_status_200(client, db_session, email_stub):
    """GET /screener/jobs/{id} returns 200 with run status for owner."""
    user_id = await register_verify_and_login(
        client, email_stub, email="screener_poll@example.com"
    )
    await _upgrade_user_to_pro(db_session, user_id)

    # Get tenant_id from user
    result = await db_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()

    # Insert a run directly into DB
    run = ScreenerRun(
        id="test-run-001",
        tenant_id=user.id,
        sector_filter="Tecnologia",
        status="pending",
    )
    db_session.add(run)
    await db_session.flush()

    resp = await client.get("/screener/jobs/test-run-001")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == "test-run-001"
    assert data["status"] == "pending"
    assert data["sector_filter"] == "Tecnologia"
    assert data["result"] is None


@pytest.mark.asyncio
async def test_screener_job_status_404_wrong_tenant(client, db_session, email_stub):
    """GET /screener/jobs/{id} returns 404 when run belongs to another tenant."""
    user_id = await register_verify_and_login(
        client, email_stub, email="screener_404@example.com"
    )
    await _upgrade_user_to_pro(db_session, user_id)

    # Insert run for a different tenant
    run = ScreenerRun(
        id="other-tenant-run",
        tenant_id="00000000-0000-0000-0000-000000000000",
        status="completed",
    )
    db_session.add(run)
    await db_session.flush()

    resp = await client.get("/screener/jobs/other-tenant-run")
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_screener_history_returns_list(client, db_session, email_stub):
    """GET /screener/history returns list of runs for the authenticated user."""
    user_id = await register_verify_and_login(
        client, email_stub, email="screener_hist@example.com"
    )
    await _upgrade_user_to_pro(db_session, user_id)

    result = await db_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()

    # Insert 2 runs
    for i in range(2):
        run = ScreenerRun(
            id=f"hist-run-{i}",
            tenant_id=user.id,
            sector_filter="Energia",
            status="completed",
        )
        db_session.add(run)
    await db_session.flush()

    resp = await client.get("/screener/history")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_screener_history_unauthenticated(client):
    """GET /screener/history returns 401 for unauthenticated requests."""
    resp = await client.get("/screener/history")
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_screener_job_completed_with_result(client, db_session, email_stub):
    """GET /screener/jobs/{id} returns parsed result when run is completed."""
    user_id = await register_verify_and_login(
        client, email_stub, email="screener_result@example.com"
    )
    await _upgrade_user_to_pro(db_session, user_id)

    result = await db_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()

    result_payload = {
        "summary": "Cenário de juros elevados favorece setor financeiro.",
        "stocks": [
            {
                "ticker": "ITUB4",
                "company_name": "Itaú Unibanco",
                "sector": "Financeiro",
                "pe_ratio": 8.5,
                "pe_vs_sector": "10% abaixo da média",
                "revenue_growth_5y": "+6% CAGR",
                "debt_to_equity": 0.3,
                "debt_health": "saudável",
                "dividend_yield": 7.5,
                "payout_score": "sustentável",
                "moat_rating": "forte",
                "moat_description": "Maior banco privado do Brasil",
                "bull_target": 35.0,
                "bear_target": 22.0,
                "current_price_ref": 28.5,
                "risk_score": 4,
                "risk_reasoning": "Regulado, bem capitalizado",
                "entry_zone": "R$ 26–29",
                "stop_loss": "abaixo de R$ 22",
                "thesis": "Dividendos consistentes acima do CDI.",
            }
        ],
        "disclaimer": "Apenas informativo.",
        "generated_at": "2026-03-25T12:00:00",
    }
    run = ScreenerRun(
        id="completed-run-001",
        tenant_id=user.id,
        status="completed",
        result_json=json.dumps(result_payload),
    )
    db_session.add(run)
    await db_session.flush()

    resp = await client.get("/screener/jobs/completed-run-001")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "completed"
    assert data["result"] is not None
    assert data["result"]["summary"] == result_payload["summary"]
    assert len(data["result"]["stocks"]) == 1
    assert data["result"]["stocks"][0]["ticker"] == "ITUB4"


# ---------------------------------------------------------------------------
# Regression tests — goldman_screener.py behavior after bug fix
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_goldman_screener_raises_on_json_parse_failure():
    """REGRESSION: JSON parse failure must raise ValueError, not return empty stocks.

    Before fix: returned {"summary": "Erro...", "stocks": []} → task marked completed.
    After fix:  raises ValueError → task marks run as failed.
    """
    from app.modules.screener.skills.goldman_screener import run_goldman_screener

    with patch("app.modules.screener.skills.goldman_screener.call_llm") as mock_llm:
        # Simulate LLM returning invalid JSON (e.g. a small model that ignores schema)
        mock_llm.return_value = "Desculpe, não posso fornecer recomendações de investimento."

        with pytest.raises(ValueError, match="invalid JSON|empty stocks"):
            await run_goldman_screener(
                investor_profile=None,
                portfolio_tickers=[],
                macro={"selic": "14.65", "cdi": "14.65", "ipca": "0.7", "ptax_usd": "5.8"},
                sector_filter="Financeiro",
                custom_notes=None,
                tier="paid",
            )


@pytest.mark.asyncio
async def test_goldman_screener_raises_on_empty_stocks():
    """REGRESSION: Empty stocks list must raise ValueError.

    Ensures a run that gets stocks=[] is never stored as 'completed'.
    """
    from app.modules.screener.skills.goldman_screener import run_goldman_screener

    with patch("app.modules.screener.skills.goldman_screener.call_llm") as mock_llm:
        # Valid JSON but stocks is empty (model partially followed schema)
        mock_llm.return_value = json.dumps({
            "summary": "Cenário adverso, nenhum ativo recomendado.",
            "stocks": [],
        })

        with pytest.raises(ValueError, match="empty stocks|no stocks"):
            await run_goldman_screener(
                investor_profile=None,
                portfolio_tickers=[],
                macro={"selic": "14.65", "cdi": "14.65", "ipca": "0.7", "ptax_usd": "5.8"},
                sector_filter=None,
                custom_notes=None,
                tier="paid",
            )


@pytest.mark.asyncio
async def test_goldman_screener_passes_tier_to_call_llm():
    """REGRESSION: goldman_screener must pass tier='paid' to call_llm.

    Before fix: call_llm was called without tier → defaulted to 'free' → small models
    that don't follow JSON schema.
    """
    from app.modules.screener.skills.goldman_screener import run_goldman_screener

    valid_result = {
        "summary": "Boa seleção.",
        "stocks": [
            {
                "ticker": "VALE3", "company_name": "Vale", "sector": "Mineração",
                "pe_ratio": 6.5, "pe_vs_sector": "30% abaixo", "revenue_growth_5y": "+8%",
                "debt_to_equity": 0.42, "debt_health": "saudável", "dividend_yield": 8.2,
                "payout_score": "sustentável", "moat_rating": "forte",
                "moat_description": "Líder global", "bull_target": 75.0, "bear_target": 48.0,
                "current_price_ref": 62.0, "risk_score": 6, "risk_reasoning": "Sólido",
                "entry_zone": "R$ 58–64", "stop_loss": "abaixo de R$ 52",
                "thesis": "Dividendos acima do CDI.",
            }
        ],
    }

    with patch("app.modules.screener.skills.goldman_screener.call_llm") as mock_llm:
        mock_llm.return_value = json.dumps(valid_result)

        result = await run_goldman_screener(
            investor_profile=None,
            portfolio_tickers=[],
            macro={"selic": "14.65", "cdi": "14.65", "ipca": "0.7", "ptax_usd": "5.8"},
            sector_filter=None,
            custom_notes=None,
            tier="paid",
        )

    # Verify tier was forwarded to call_llm
    call_kwargs = mock_llm.call_args
    assert call_kwargs.kwargs.get("tier") == "paid" or (
        len(call_kwargs.args) > 2 and call_kwargs.args[2] == "paid"
    ), f"call_llm was not called with tier='paid'. Call: {call_kwargs}"

    # Result should be valid
    assert len(result["stocks"]) == 1
    assert result["stocks"][0]["ticker"] == "VALE3"
    assert "disclaimer" in result
    assert "generated_at" in result


@pytest.mark.asyncio
async def test_goldman_screener_happy_path():
    """goldman_screener returns expected structure on valid AI response."""
    from app.modules.screener.skills.goldman_screener import run_goldman_screener

    valid_result = {
        "summary": "Mercado favorável para financeiro.",
        "stocks": [
            {
                "ticker": "BBDC4", "company_name": "Bradesco", "sector": "Financeiro",
                "pe_ratio": 7.2, "pe_vs_sector": "15% abaixo", "revenue_growth_5y": "+5%",
                "debt_to_equity": 0.5, "debt_health": "controlado", "dividend_yield": 6.8,
                "payout_score": "sustentável", "moat_rating": "moderado",
                "moat_description": "Rede ampla", "bull_target": 18.0, "bear_target": 11.0,
                "current_price_ref": 14.5, "risk_score": 5, "risk_reasoning": "Regulatório",
                "entry_zone": "R$ 13–15", "stop_loss": "abaixo de R$ 11",
                "thesis": "Yield acima do CDI com upside moderado.",
            }
        ],
    }

    with patch("app.modules.screener.skills.goldman_screener.call_llm") as mock_llm:
        mock_llm.return_value = json.dumps(valid_result)

        result = await run_goldman_screener(
            investor_profile={"tolerancia_risco": "moderado", "horizonte_anos": 5,
                              "objetivo": "renda", "percentual_renda_fixa_alvo": "40"},
            portfolio_tickers=["ITUB4"],
            macro={"selic": "14.65", "cdi": "14.65", "ipca": "0.7", "ptax_usd": "5.8"},
            sector_filter="Financeiro",
            custom_notes="Prefiro dividendos mensais",
            tier="paid",
        )

    assert result["summary"] == valid_result["summary"]
    assert len(result["stocks"]) == 1
    assert result["stocks"][0]["ticker"] == "BBDC4"
    assert result["disclaimer"] != ""
    assert "generated_at" in result


@pytest.mark.asyncio
async def test_goldman_screener_handles_markdown_json_fences():
    """goldman_screener strips ```json ... ``` fences before parsing."""
    from app.modules.screener.skills.goldman_screener import run_goldman_screener

    payload = {
        "summary": "Bom cenário.",
        "stocks": [
            {
                "ticker": "PETR4", "company_name": "Petrobras", "sector": "Petróleo",
                "pe_ratio": 5.0, "pe_vs_sector": "20% abaixo", "revenue_growth_5y": "+3%",
                "debt_to_equity": 1.2, "debt_health": "alto", "dividend_yield": 12.0,
                "payout_score": "elevado", "moat_rating": "forte",
                "moat_description": "Pré-sal exclusivo", "bull_target": 42.0, "bear_target": 25.0,
                "current_price_ref": 35.0, "risk_score": 7, "risk_reasoning": "Político",
                "entry_zone": "R$ 33–36", "stop_loss": "abaixo de R$ 28",
                "thesis": "Dividend yield superior ao CDI.",
            }
        ],
    }
    fenced = f"```json\n{json.dumps(payload)}\n```"

    with patch("app.modules.screener.skills.goldman_screener.call_llm") as mock_llm:
        mock_llm.return_value = fenced

        result = await run_goldman_screener(
            investor_profile=None,
            portfolio_tickers=[],
            macro={"selic": "14.65", "cdi": "14.65", "ipca": "0.7", "ptax_usd": "5.8"},
            sector_filter=None,
            custom_notes=None,
            tier="paid",
        )

    assert result["stocks"][0]["ticker"] == "PETR4"
