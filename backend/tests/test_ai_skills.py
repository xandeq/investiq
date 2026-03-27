"""Unit tests for AI skill adapters.

All LLM calls are mocked — these tests verify that each skill:
1. Returns a dict with the required keys
2. Includes the exact CVM disclaimer text
3. Passes data to call_llm and returns its response as 'analysis'
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from app.modules.ai.skills import DISCLAIMER_TEXT
from app.modules.ai.skills.dcf import run_dcf
from app.modules.ai.skills.valuation import run_valuation
from app.modules.ai.skills.earnings import run_earnings
from app.modules.ai.skills.macro import run_macro_impact
from app.modules.ai.skills.portfolio_advisor import run_portfolio_advisor


MOCK_ANALYSIS = "Test analysis response from mocked LLM provider."

SAMPLE_FUNDAMENTALS = {
    "pe_ratio": "12.5",
    "pb_ratio": "1.8",
    "dividend_yield": "6.2",
    "ev_ebitda": "8.1",
    "roe": "18.5",
    "revenue_growth": "12.3",
    "profit_margin": "22.1",
    "payout_ratio": "45.0",
    "market_cap": "180000000000",
    "sector": "Mineração",
}

SAMPLE_MACRO = {
    "selic": "10.50",
    "cdi": "10.40",
    "ipca": "5.20",
    "ptax_usd": "4.95",
}

SAMPLE_ALLOCATION = [
    {"asset_class": "acao", "total_value": "120000.00", "percentage": "65.0"},
    {"asset_class": "fii", "total_value": "45000.00", "percentage": "24.3"},
    {"asset_class": "renda_fixa", "total_value": "20000.00", "percentage": "10.7"},
]


@pytest.mark.asyncio
async def test_run_dcf_returns_required_keys():
    """run_dcf returns dict with ticker, analysis, methodology, disclaimer."""
    with patch(
        "app.modules.ai.skills.dcf.call_llm",
        new=AsyncMock(return_value=MOCK_ANALYSIS),
    ):
        result = await run_dcf("VALE3", SAMPLE_FUNDAMENTALS, SAMPLE_MACRO)

    assert isinstance(result, dict)
    assert result["ticker"] == "VALE3"
    assert result["analysis"] == MOCK_ANALYSIS
    assert "methodology" in result
    assert "disclaimer" in result


@pytest.mark.asyncio
async def test_run_dcf_disclaimer_matches_cvm_constant():
    """run_dcf disclaimer matches the exact CVM Res. 19/2021 text."""
    with patch(
        "app.modules.ai.skills.dcf.call_llm",
        new=AsyncMock(return_value=MOCK_ANALYSIS),
    ):
        result = await run_dcf("VALE3", SAMPLE_FUNDAMENTALS, SAMPLE_MACRO)

    assert result["disclaimer"] == DISCLAIMER_TEXT


@pytest.mark.asyncio
async def test_run_valuation_returns_required_keys():
    """run_valuation returns dict with ticker, analysis, methodology, disclaimer."""
    with patch(
        "app.modules.ai.skills.valuation.call_llm",
        new=AsyncMock(return_value=MOCK_ANALYSIS),
    ):
        result = await run_valuation("PETR4", SAMPLE_FUNDAMENTALS)

    assert isinstance(result, dict)
    assert result["ticker"] == "PETR4"
    assert result["analysis"] == MOCK_ANALYSIS
    assert "methodology" in result
    assert "disclaimer" in result


@pytest.mark.asyncio
async def test_run_valuation_disclaimer_matches_cvm_constant():
    """run_valuation disclaimer matches the exact CVM Res. 19/2021 text."""
    with patch(
        "app.modules.ai.skills.valuation.call_llm",
        new=AsyncMock(return_value=MOCK_ANALYSIS),
    ):
        result = await run_valuation("PETR4", SAMPLE_FUNDAMENTALS)

    assert result["disclaimer"] == DISCLAIMER_TEXT


@pytest.mark.asyncio
async def test_run_earnings_returns_required_keys():
    """run_earnings returns dict with ticker, analysis, methodology, disclaimer."""
    with patch(
        "app.modules.ai.skills.earnings.call_llm",
        new=AsyncMock(return_value=MOCK_ANALYSIS),
    ):
        result = await run_earnings("ITUB4", SAMPLE_FUNDAMENTALS)

    assert isinstance(result, dict)
    assert result["ticker"] == "ITUB4"
    assert result["analysis"] == MOCK_ANALYSIS
    assert "methodology" in result
    assert "disclaimer" in result


@pytest.mark.asyncio
async def test_run_earnings_disclaimer_matches_cvm_constant():
    """run_earnings disclaimer matches the exact CVM Res. 19/2021 text."""
    with patch(
        "app.modules.ai.skills.earnings.call_llm",
        new=AsyncMock(return_value=MOCK_ANALYSIS),
    ):
        result = await run_earnings("ITUB4", SAMPLE_FUNDAMENTALS)

    assert result["disclaimer"] == DISCLAIMER_TEXT


@pytest.mark.asyncio
async def test_run_macro_impact_returns_required_keys():
    """run_macro_impact returns dict with analysis, methodology, disclaimer (no ticker)."""
    with patch(
        "app.modules.ai.skills.macro.call_llm",
        new=AsyncMock(return_value=MOCK_ANALYSIS),
    ):
        result = await run_macro_impact(SAMPLE_MACRO, SAMPLE_ALLOCATION)

    assert isinstance(result, dict)
    assert result["analysis"] == MOCK_ANALYSIS
    assert "methodology" in result
    assert "disclaimer" in result
    # Macro result has no ticker key
    assert "ticker" not in result


@pytest.mark.asyncio
async def test_run_macro_impact_disclaimer_matches_cvm_constant():
    """run_macro_impact disclaimer matches the exact CVM Res. 19/2021 text."""
    with patch(
        "app.modules.ai.skills.macro.call_llm",
        new=AsyncMock(return_value=MOCK_ANALYSIS),
    ):
        result = await run_macro_impact(SAMPLE_MACRO, SAMPLE_ALLOCATION)

    assert result["disclaimer"] == DISCLAIMER_TEXT


def test_disclaimer_constant_contains_cvm_reference():
    """DISCLAIMER_TEXT contains the required CVM Res. 19/2021 reference."""
    assert "CVM Res. 19/2021" in DISCLAIMER_TEXT
    assert "recomendação de investimento" in DISCLAIMER_TEXT


@pytest.mark.asyncio
async def test_run_dcf_with_empty_fundamentals():
    """run_dcf handles empty fundamentals dict without crashing."""
    with patch(
        "app.modules.ai.skills.dcf.call_llm",
        new=AsyncMock(return_value=MOCK_ANALYSIS),
    ):
        result = await run_dcf("UNKN3", {}, {})

    assert result["ticker"] == "UNKN3"
    assert result["disclaimer"] == DISCLAIMER_TEXT


@pytest.mark.asyncio
async def test_run_macro_impact_with_empty_allocation():
    """run_macro_impact handles empty allocation list without crashing."""
    with patch(
        "app.modules.ai.skills.macro.call_llm",
        new=AsyncMock(return_value=MOCK_ANALYSIS),
    ):
        result = await run_macro_impact(SAMPLE_MACRO, [])

    assert result["disclaimer"] == DISCLAIMER_TEXT


# ---------------------------------------------------------------------------
# Tests: run_portfolio_advisor (AI Advisor skill)
# ---------------------------------------------------------------------------

SAMPLE_POSITIONS = [
    {
        "ticker": "VALE3",
        "asset_class": "acao",
        "quantity": "100",
        "cmp": "65.50",
        "total_cost": "6000.00",
        "current_price": "65.50",
        "unrealized_pnl": "550.00",
        "unrealized_pnl_pct": "9.17",
    },
    {
        "ticker": "BCFF11",
        "asset_class": "fii",
        "quantity": "50",
        "cmp": "80.00",
        "total_cost": "3800.00",
        "current_price": "80.00",
        "unrealized_pnl": "200.00",
        "unrealized_pnl_pct": "5.26",
    },
]

SAMPLE_PNL = {
    "realized_pnl_total": "320.00",
    "unrealized_pnl_total": "750.00",
    "total_portfolio_value": "11275.00",
}

MOCK_ADVISOR_JSON = """{
  "diagnostico": "Carteira equilibrada entre ações e FIIs.",
  "pontos_positivos": ["Diversificação adequada", "DY elevado nos FIIs"],
  "pontos_de_atencao": ["Concentração em commodities"],
  "sugestoes": ["Considerar renda fixa"],
  "proximos_passos": ["Revisar em 3 meses"]
}"""


@pytest.mark.asyncio
async def test_run_portfolio_advisor_returns_required_keys():
    """[SMOKE] run_portfolio_advisor returns dict with all required keys."""
    with patch(
        "app.modules.ai.skills.portfolio_advisor.call_llm",
        new=AsyncMock(return_value=MOCK_ADVISOR_JSON),
    ):
        result = await run_portfolio_advisor(
            positions=SAMPLE_POSITIONS,
            pnl=SAMPLE_PNL,
            allocation=SAMPLE_ALLOCATION,
            macro=SAMPLE_MACRO,
        )

    assert isinstance(result, dict)
    assert "diagnostico" in result
    assert "pontos_positivos" in result
    assert "pontos_de_atencao" in result
    assert "sugestoes" in result
    assert "proximos_passos" in result
    assert "disclaimer" in result


@pytest.mark.asyncio
async def test_run_portfolio_advisor_disclaimer_matches_cvm_constant():
    """[REGRESSION] run_portfolio_advisor disclaimer matches CVM Res. 19/2021 text."""
    with patch(
        "app.modules.ai.skills.portfolio_advisor.call_llm",
        new=AsyncMock(return_value=MOCK_ADVISOR_JSON),
    ):
        result = await run_portfolio_advisor(
            positions=SAMPLE_POSITIONS,
            pnl=SAMPLE_PNL,
            allocation=SAMPLE_ALLOCATION,
            macro=SAMPLE_MACRO,
        )

    assert result["disclaimer"] == DISCLAIMER_TEXT


@pytest.mark.asyncio
async def test_run_portfolio_advisor_parses_json_response():
    """[REGRESSION] run_portfolio_advisor parses LLM JSON into structured fields."""
    with patch(
        "app.modules.ai.skills.portfolio_advisor.call_llm",
        new=AsyncMock(return_value=MOCK_ADVISOR_JSON),
    ):
        result = await run_portfolio_advisor(
            positions=SAMPLE_POSITIONS,
            pnl=SAMPLE_PNL,
            allocation=SAMPLE_ALLOCATION,
            macro=SAMPLE_MACRO,
        )

    assert result["diagnostico"] == "Carteira equilibrada entre ações e FIIs."
    assert result["pontos_positivos"] == ["Diversificação adequada", "DY elevado nos FIIs"]
    assert result["pontos_de_atencao"] == ["Concentração em commodities"]
    assert result["sugestoes"] == ["Considerar renda fixa"]
    assert result["proximos_passos"] == ["Revisar em 3 meses"]


@pytest.mark.asyncio
async def test_run_portfolio_advisor_handles_markdown_fenced_json():
    """[REGRESSION] run_portfolio_advisor strips markdown code fences before parsing."""
    fenced = f"```json\n{MOCK_ADVISOR_JSON}\n```"
    with patch(
        "app.modules.ai.skills.portfolio_advisor.call_llm",
        new=AsyncMock(return_value=fenced),
    ):
        result = await run_portfolio_advisor(
            positions=SAMPLE_POSITIONS,
            pnl=SAMPLE_PNL,
            allocation=SAMPLE_ALLOCATION,
            macro=SAMPLE_MACRO,
        )

    assert result["diagnostico"] == "Carteira equilibrada entre ações e FIIs."
    assert "disclaimer" in result


@pytest.mark.asyncio
async def test_run_portfolio_advisor_fallback_on_invalid_json():
    """[REGRESSION] run_portfolio_advisor falls back gracefully when LLM returns non-JSON."""
    raw_text = "A carteira está bem diversificada mas precisa de revisão."
    with patch(
        "app.modules.ai.skills.portfolio_advisor.call_llm",
        new=AsyncMock(return_value=raw_text),
    ):
        result = await run_portfolio_advisor(
            positions=SAMPLE_POSITIONS,
            pnl=SAMPLE_PNL,
            allocation=SAMPLE_ALLOCATION,
            macro=SAMPLE_MACRO,
        )

    # Fallback: raw text goes into diagnostico, lists are empty
    assert result["diagnostico"] == raw_text
    assert result["pontos_positivos"] == []
    assert result["pontos_de_atencao"] == []
    assert result["sugestoes"] == []
    assert result["proximos_passos"] == []
    assert "disclaimer" in result


@pytest.mark.asyncio
async def test_run_portfolio_advisor_with_empty_portfolio():
    """[REGRESSION] run_portfolio_advisor handles empty positions list without crashing."""
    with patch(
        "app.modules.ai.skills.portfolio_advisor.call_llm",
        new=AsyncMock(return_value=MOCK_ADVISOR_JSON),
    ):
        result = await run_portfolio_advisor(
            positions=[],
            pnl={},
            allocation=[],
            macro=SAMPLE_MACRO,
        )

    assert "disclaimer" in result


@pytest.mark.asyncio
async def test_run_portfolio_advisor_with_investor_profile():
    """[INTEGRATION] run_portfolio_advisor accepts optional investor_profile context."""
    investor_profile = {
        "objetivo": "crescimento",
        "horizonte_anos": 10,
        "tolerancia_risco": "moderado",
        "percentual_renda_fixa_alvo": "30",
    }

    captured_prompt = []

    async def capture_llm(prompt, system="", **kwargs):
        captured_prompt.append(prompt)
        return MOCK_ADVISOR_JSON

    with patch(
        "app.modules.ai.skills.portfolio_advisor.call_llm",
        new=capture_llm,
    ):
        result = await run_portfolio_advisor(
            positions=SAMPLE_POSITIONS,
            pnl=SAMPLE_PNL,
            allocation=SAMPLE_ALLOCATION,
            macro=SAMPLE_MACRO,
            investor_profile=investor_profile,
        )

    # Investor profile context must appear in the prompt sent to the LLM
    assert len(captured_prompt) == 1
    prompt_text = captured_prompt[0]
    assert "crescimento" in prompt_text
    assert "moderado" in prompt_text
    assert "10" in prompt_text  # horizonte_anos
    assert "disclaimer" in result


@pytest.mark.asyncio
async def test_run_portfolio_advisor_limits_positions_to_15():
    """[REGRESSION] run_portfolio_advisor truncates prompt to top 15 positions."""
    many_positions = [
        {
            "ticker": f"TICK{i:02d}",
            "asset_class": "acao",
            "quantity": "10",
            "cmp": "50.00",
            "total_cost": "450.00",
            "current_price": "50.00",
            "unrealized_pnl": "50.00",
            "unrealized_pnl_pct": "11.11",
        }
        for i in range(20)  # 20 positions, expect only 15 in prompt
    ]

    captured_prompt = []

    async def capture_llm(prompt, system="", **kwargs):
        captured_prompt.append(prompt)
        return MOCK_ADVISOR_JSON

    with patch(
        "app.modules.ai.skills.portfolio_advisor.call_llm",
        new=capture_llm,
    ):
        await run_portfolio_advisor(
            positions=many_positions,
            pnl=SAMPLE_PNL,
            allocation=SAMPLE_ALLOCATION,
            macro=SAMPLE_MACRO,
        )

    prompt_text = captured_prompt[0]
    # TICK15 through TICK19 should NOT appear in the prompt (truncated at 15)
    assert "TICK15" not in prompt_text
    assert "TICK00" in prompt_text  # first one must be there
