"""Tesouro Direto public API adapter.

Fetches current rates for Tesouro Selic, Tesouro IPCA+ and Tesouro Prefixado
from the official Tesouro Transparência API (no key required).

API: https://www.tesourotransparencia.gov.br/thot/tesourodireto/obterTaxasTesouro.json
"""
from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

_URL = "https://www.tesourotransparencia.gov.br/thot/tesourodireto/obterTaxasTesouro.json"
_TIMEOUT = 10

# Map official names to short labels
_LABEL_MAP = {
    "Tesouro Selic": "Tesouro Selic",
    "Tesouro IPCA+": "Tesouro IPCA+",
    "Tesouro IPCA+ com Juros Semestrais": "Tesouro IPCA+ Semestral",
    "Tesouro Prefixado": "Tesouro Prefixado",
    "Tesouro Prefixado com Juros Semestrais": "Tesouro Prefixado Semestral",
    "Tesouro Renda+": "Tesouro Renda+",
    "Tesouro Educa+": "Tesouro Educa+",
}


def get_tesouro_rates() -> list[dict[str, Any]]:
    """Fetch current Tesouro Direto rates.

    Returns list of dicts with:
      name, label, maturity_date, annual_rate, min_investment, price
    Sorted by maturity date ascending.
    Returns empty list on failure.
    """
    try:
        resp = requests.get(_URL, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        bonds = data.get("response", {}).get("TrsrBdTradgList", [])

        results = []
        for item in bonds:
            bd = item.get("TrsrBd", {})
            name = bd.get("nm", "")
            label = _LABEL_MAP.get(name, name)
            rate_str = bd.get("anulInvstmtRate", "0")
            try:
                annual_rate = float(str(rate_str).replace(",", "."))
            except ValueError:
                annual_rate = 0.0
            maturity = bd.get("mtrtyDt", "")[:10]
            min_invest = float(str(bd.get("minInvstmtAmt", "0")).replace(",", ".")) if bd.get("minInvstmtAmt") else 0.0
            price = float(str(bd.get("untrInvstmtVal", "0")).replace(",", ".")) if bd.get("untrInvstmtVal") else 0.0
            results.append({
                "name": name,
                "label": label,
                "maturity_date": maturity,
                "annual_rate": annual_rate,
                "min_investment": min_invest,
                "price": price,
            })

        results.sort(key=lambda x: x["maturity_date"])
        return results
    except Exception as exc:
        logger.warning("tesouro: rates fetch failed: %s", exc)
        return []


def get_top_tesouro(n: int = 3) -> list[dict[str, Any]]:
    """Return top N Tesouro bonds: Selic, best IPCA+, best Prefixado."""
    all_bonds = get_tesouro_rates()
    if not all_bonds:
        return []

    selic = [b for b in all_bonds if "Selic" in b["label"] and "+" not in b["label"]]
    ipca = [b for b in all_bonds if "IPCA+" in b["label"] and "Semestral" not in b["label"]]
    prefixado = [b for b in all_bonds if "Prefixado" in b["label"] and "Semestral" not in b["label"]]

    picks = []
    if selic:
        picks.append({**selic[0], "profile": "conservador – liquidez diária"})
    if ipca:
        # Best IPCA+ = highest rate
        best_ipca = max(ipca, key=lambda x: x["annual_rate"])
        picks.append({**best_ipca, "profile": "proteção inflação – longo prazo"})
    if prefixado:
        best_pre = max(prefixado, key=lambda x: x["annual_rate"])
        picks.append({**best_pre, "profile": "travar taxa – cenário de queda de juros"})

    return picks[:n]
