"""Fixed income section: Tesouro Direto + CDB rates."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def fetch_fixed_income_data() -> dict[str, Any]:
    """Fetch Tesouro Direto rates + BCB CDI."""
    loop = asyncio.get_event_loop()

    try:
        from app.modules.market_data.adapters.tesouro import get_top_tesouro
        import os, functools
        # Pass SELIC rate for synthetic fallback (fetched from BCB macro in Redis)
        tesouro = await loop.run_in_executor(None, functools.partial(get_top_tesouro, 3))
    except Exception as exc:
        logger.warning("fixed_income: tesouro fetch failed: %s", exc)
        tesouro = []

    # CDB rates: typical market rates (can be enriched with real data later)
    cdb_rates = [
        {"nome": "CDB 100% CDI", "rentabilidade": "100% CDI", "liquidez": "D+0 ou vencimento", "risco": "baixo", "nota": 7.5},
        {"nome": "CDB 115% CDI", "rentabilidade": "115% CDI", "liquidez": "vencimento (1-2 anos)", "risco": "baixo/médio", "nota": 8.4},
        {"nome": "CDB 120% CDI", "rentabilidade": "120% CDI", "liquidez": "vencimento (2-3 anos)", "risco": "médio", "nota": 8.2},
    ]

    # LCI/LCA info (isentos de IR)
    lci_rates = [
        {"nome": "LCI 95% CDI líquido", "rentabilidade": "~95% CDI (isento IR)", "liquidez": "vencimento (90d+)", "risco": "baixo", "nota": 8.6},
    ]

    return {
        "tesouro": tesouro,
        "cdb": cdb_rates,
        "lci": lci_rates,
    }


def format_fixed_income_section(data: dict[str, Any], selic: float | None = None) -> str:
    """Format fixed income section as Telegram HTML."""
    lines = ["<b>💰 Renda Fixa Recomendada</b>", ""]

    tesouro = data.get("tesouro", [])
    cdb = data.get("cdb", [])
    lci = data.get("lci", [])

    if tesouro:
        lines.append("<b>Tesouro Direto</b>")
        for t in tesouro:
            rate = t.get("annual_rate", 0)
            label = t.get("label", "")
            maturity = t.get("maturity_date", "")
            profile = t.get("profile", "")
            min_invest = t.get("min_investment", 0)
            rate_str = f"{rate:.2f}% a.a." if rate else "ver site"
            maturity_str = f" | Vence: {maturity}" if maturity else ""
            lines.append(f"  • <b>{label}</b> — {rate_str}{maturity_str}")
            lines.append(f"    👤 {profile} | Mínimo: R${min_invest:.2f}")
        lines.append("")

    if cdb:
        lines.append("<b>CDBs</b>")
        for c in cdb:
            lines.append(
                f"  • <b>{c['nome']}</b> — {c['rentabilidade']} | "
                f"Liquidez: {c['liquidez']} | ⭐{c['nota']}"
            )
        lines.append("")

    if lci:
        lines.append("<b>LCI/LCA (isentos de IR)</b>")
        for l in lci:
            lines.append(
                f"  • <b>{l['nome']}</b> — {l['rentabilidade']} | "
                f"Liquidez: {l['liquidez']} | ⭐{l['nota']}"
            )
        lines.append("")

    # Leitura macro
    if selic:
        lines.append(
            f"<i>💡 Com SELIC em {selic:.2f}%, renda fixa está muito competitiva. "
            f"Tesouro Selic é o ponto de entrada mais seguro para reserva.</i>"
        )
    else:
        lines.append("<i>💡 Renda fixa competitiva — compare com rendimento líquido após IR.</i>")

    return "\n".join(lines)
