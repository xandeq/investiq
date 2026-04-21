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

# Primary endpoint (blocked on some servers — falls back gracefully)
_URL = "https://www.tesourotransparencia.gov.br/thot/tesourodireto/obterTaxasTesouro.json"
# Secondary: Tesouro Direto direct API
_URL2 = "https://www.tesourodireto.com.br/json/br/com/b3/tesourodireto/geralatividade/rest/tesouroDiretoGetTaxasTesouroDireto.json"
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


def _get_bonds_from_url(url: str) -> list | None:
    """Try fetching bond list from a specific URL. Returns None on failure."""
    try:
        resp = requests.get(url, timeout=_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        data = resp.json()
        # Primary URL format
        bonds = data.get("response", {}).get("TrsrBdTradgList")
        if bonds is not None:
            return bonds
        # Secondary URL format (tesourodireto.com.br)
        for key in ("BdTradgList", "TrsrBdTradgList"):
            bonds = data.get(key)
            if bonds:
                return bonds
        # Try nested
        for v in data.values():
            if isinstance(v, list) and v:
                return v
        return None
    except Exception:
        return None


def get_tesouro_rates() -> list[dict[str, Any]]:
    """Fetch current Tesouro Direto rates.

    Tries primary URL then secondary. Returns empty list on both failures.
    """
    for url in [_URL, _URL2]:
        bonds = _get_bonds_from_url(url)
        if bonds:
            break
    else:
        logger.warning("tesouro: all endpoints failed")
        return []

    bonds = bonds  # type: ignore[assignment]
    try:

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
