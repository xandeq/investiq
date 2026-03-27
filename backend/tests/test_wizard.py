"""Tests for the Wizard Onde Investir backend (Phase 11 — WIZ-02 through WIZ-05).

Covers:
- Unit tests for _parse_and_validate (ticker detection, sum check, markdown strip)
- Unit tests for _build_prompt (macro inclusion, portfolio section)
- Integration tests for POST /wizard/start and GET /wizard/{job_id}
- CVM disclaimer presence in all responses
- Delta output in GET response for completed wizard jobs
"""
from __future__ import annotations

import json
import pytest

from app.modules.wizard.tasks import _parse_and_validate, _build_prompt, _TICKER_RE
from app.modules.wizard.schemas import CVM_DISCLAIMER
from tests.conftest import register_verify_and_login


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_raw(
    acoes: int = 40,
    fiis: int = 20,
    rf: int = 30,
    caixa: int = 10,
    rationale: str = "Texto generico sem tickers",
) -> str:
    """Build a raw JSON string for _parse_and_validate tests."""
    return json.dumps({
        "acoes_pct": acoes,
        "fiis_pct": fiis,
        "renda_fixa_pct": rf,
        "caixa_pct": caixa,
        "rationale": rationale,
    })


# ---------------------------------------------------------------------------
# Unit tests: _parse_and_validate
# ---------------------------------------------------------------------------

def test_parse_and_validate_valid_json():
    """Valid JSON with correct percentages returns dict with all 5 fields."""
    result = _parse_and_validate(_make_raw(40, 20, 30, 10, "Texto sem tickers"))
    assert "acoes_pct" in result
    assert "fiis_pct" in result
    assert "renda_fixa_pct" in result
    assert "caixa_pct" in result
    assert "rationale" in result
    assert result["acoes_pct"] == 40
    assert result["fiis_pct"] == 20


def test_parse_and_validate_ticker_in_rationale():
    """JSON with PETR4 in rationale raises ValueError with 'Ticker detected'."""
    raw = _make_raw(rationale="Considere alocar em PETR4 para renda.")
    with pytest.raises(ValueError, match="Ticker detected"):
        _parse_and_validate(raw)


def test_parse_and_validate_ticker_hglg11():
    """JSON with HGLG11 (4+2 digit FII pattern) raises ValueError."""
    raw = _make_raw(rationale="O fundo HGLG11 tem bom historico de distribuicao.")
    with pytest.raises(ValueError, match="Ticker detected"):
        _parse_and_validate(raw)


def test_parse_and_validate_no_ticker_false_positive():
    """FII, CDI, SELIC abbreviations (no trailing digits) do not trigger ticker check."""
    raw = _make_raw(
        rationale="O CDI esta em alta e SELIC aumentou. FII sao bons ativos."
    )
    result = _parse_and_validate(raw)
    assert "rationale" in result


def test_parse_and_validate_sum_over_103():
    """Percentages summing to 110 raises ValueError about sum."""
    raw = _make_raw(acoes=40, fiis=30, rf=30, caixa=10)  # sum = 110
    with pytest.raises(ValueError, match="Percentages sum"):
        _parse_and_validate(raw)


def test_parse_and_validate_markdown_fences():
    """Input wrapped in ```json ... ``` fences is stripped and parsed correctly."""
    inner = json.dumps({
        "acoes_pct": 30,
        "fiis_pct": 20,
        "renda_fixa_pct": 40,
        "caixa_pct": 10,
        "rationale": "Sem tickers aqui",
    })
    raw = f"```json\n{inner}\n```"
    result = _parse_and_validate(raw)
    assert result["acoes_pct"] == 30
    assert result["renda_fixa_pct"] == 40


# ---------------------------------------------------------------------------
# Unit tests: _build_prompt
# ---------------------------------------------------------------------------

def test_build_prompt_includes_macro():
    """Prompt includes SELIC, CDI, and IPCA values from macro dict."""
    macro = {"selic": "13.75", "cdi": "13.65", "ipca": "4.5"}
    prompt = _build_prompt("moderado", "1a", 10000.0, macro, None)
    assert "SELIC: 13.75%" in prompt
    assert "CDI: 13.65%" in prompt
    assert "IPCA (12 meses): 4.5%" in prompt


def test_build_prompt_includes_portfolio():
    """Prompt includes portfolio section with asset percentages when portfolio provided."""
    macro = {"selic": "13.75", "cdi": "13.65", "ipca": "4.5"}
    portfolio = {
        "total": 100000,
        "acoes": {"pct": 60.0, "valor": 60000},
        "fiis": {"pct": 20.0, "valor": 20000},
        "renda_fixa": {"pct": 20.0, "valor": 20000},
    }
    prompt = _build_prompt("moderado", "1a", 10000.0, macro, portfolio)
    assert "CARTEIRA ATUAL DO INVESTIDOR" in prompt
    assert "60.0%" in prompt


def test_build_prompt_no_portfolio():
    """Prompt says investor has no portfolio when portfolio is None."""
    macro = {"selic": "13.75", "cdi": "13.65", "ipca": "4.5"}
    prompt = _build_prompt("conservador", "6m", 5000.0, macro, None)
    assert "ainda" in prompt.lower() and "carteira" in prompt.lower()


# ---------------------------------------------------------------------------
# Integration tests: POST /wizard/start
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_start_wizard_202(client, email_stub):
    """Authenticated user gets 202 with job_id and disclaimer."""
    await register_verify_and_login(client, email_stub, email="wizard1@example.com")
    resp = await client.post(
        "/wizard/start",
        json={"perfil": "moderado", "prazo": "1a", "valor": 10000},
    )
    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "pending"
    assert "disclaimer" in data


@pytest.mark.asyncio
async def test_start_wizard_unauthenticated(client):
    """Unauthenticated user gets 401 when calling /wizard/start."""
    resp = await client.post(
        "/wizard/start",
        json={"perfil": "moderado", "prazo": "1a", "valor": 10000},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_wizard_job_not_found(client, email_stub):
    """GET /wizard/{nonexistent-id} returns 404 for authenticated user."""
    await register_verify_and_login(client, email_stub, email="wizard2@example.com")
    resp = await client.get("/wizard/nonexistent-uuid-that-does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_disclaimer_in_start_response(client, email_stub):
    """POST /wizard/start response body includes disclaimer matching CVM_DISCLAIMER exactly."""
    await register_verify_and_login(client, email_stub, email="wizard3@example.com")
    resp = await client.post(
        "/wizard/start",
        json={"perfil": "conservador", "prazo": "6m", "valor": 5000},
    )
    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert data["disclaimer"] == CVM_DISCLAIMER


# ---------------------------------------------------------------------------
# Integration test: GET /wizard/{job_id} with completed job and delta output
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_wizard_job_returns_delta_on_completion(client, email_stub, db_session):
    """Completed wizard job returns delta field in result."""
    from app.modules.wizard.models import WizardJob

    user_id = await register_verify_and_login(
        client, email_stub, email="wizard4@example.com"
    )

    # Insert a completed wizard job directly into DB
    result_data = {
        "allocation": {
            "acoes_pct": 40.0,
            "fiis_pct": 20.0,
            "renda_fixa_pct": 30.0,
            "caixa_pct": 10.0,
            "rationale": "Texto generico de analise",
        },
        "macro": {"selic": "13.75", "cdi": "13.65", "ipca": "4.5"},
        "portfolio_context": None,
        "delta": [
            {
                "asset_class": "acoes",
                "label": "Acoes",
                "current_pct": 20.0,
                "suggested_pct": 40.0,
                "delta_pct": 20.0,
                "action": "adicionar",
                "valor_delta": 2000.0,
            }
        ],
        "provider_used": "test",
        "completed_at": "2026-03-24T00:00:00+00:00",
    }

    completed_job = WizardJob(
        tenant_id=user_id,
        perfil="moderado",
        prazo="1a",
        valor=10000.0,
        status="completed",
        result_json=json.dumps(result_data),
    )
    db_session.add(completed_job)
    await db_session.flush()
    job_id = completed_job.id

    resp = await client.get(f"/wizard/{job_id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "completed"
    assert data["result"] is not None
    assert "delta" in data["result"]
    assert len(data["result"]["delta"]) == 1
    assert data["result"]["delta"][0]["asset_class"] == "acoes"
    assert data["result"]["delta"][0]["suggested_pct"] == 40.0
    assert data["result"]["delta"][0]["action"] == "adicionar"
