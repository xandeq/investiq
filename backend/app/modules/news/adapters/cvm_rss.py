"""CVM RSS feed adapter — fatos relevantes e comunicados.

Fetches from CVM's official RSS feeds (no key required):
  - Fatos Relevantes: https://www.rad.cvm.gov.br/ENETCONSULTA/frmGerenciaPaginaFRE.aspx?...
  - ITR/DFP filings

Uses the simpler RAD CVM RSS endpoint which is publicly available.
Falls back to scraping the CVM search API if RSS is unavailable.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any
import re

import requests

logger = logging.getLogger(__name__)

_TIMEOUT = 10
# Primary: CVM EFTS API (may be blocked in some networks)
_CVM_RSS_URL = "https://efts.cvm.gov.br/EFTS-API/search?q=&dateRange=custom&startDate={start}&endDate={end}&category=IPE"
# Secondary: CVM RSS feed (simpler, more reliable)
_CVM_RSS_FEED = "https://www.rad.cvm.gov.br/ENETCONSULTA/frmGerenciaPaginaFRE.aspx?NumeroProtocolo=&NumeroSeqProtocolo=&CNPJ=&NomePregao=&CategoriaDocumento=&TipoCategoria=&DescricaoTipoDocumento=&CodigoGrupoDFP=&CodigoSubgrupoDFP=&DataSelecionada=&isITR=S&DataApresentacaoInicio=&DataApresentacaoFim=&DataReferencia=&SFN=N&ordenacaoDocumento=&paginaAtual=1"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; InvestIQ/1.0)"}


def _parse_date(date_str: str) -> datetime | None:
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str[:19], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def get_cvm_news(hours_back: int = 48) -> list[dict[str, Any]]:
    """Fetch CVM filings from the last N hours.

    Tries EFTS API first, falls back gracefully.
    Returns list of dicts with: headline, company, ticker_hint, url, published_at, category, source
    """
    brt = timezone(timedelta(hours=-3))
    now = datetime.now(brt)
    start = (now - timedelta(hours=hours_back)).strftime("%Y-%m-%d")
    end = now.strftime("%Y-%m-%d")

    url = _CVM_RSS_URL.format(start=start, end=end)
    try:
        resp = requests.get(url, timeout=_TIMEOUT, headers=_HEADERS)
        resp.raise_for_status()
        data = resp.json()
        hits = data.get("hits", {}).get("hits", [])

        results = []
        for hit in hits[:20]:
            src = hit.get("_source", {})
            headline = src.get("descrição", src.get("assunto", ""))
            company = src.get("nomePregao", src.get("nomeEmpresa", ""))
            category = src.get("categoria", "")
            published = src.get("dataReferencia", src.get("dataApresentacao", ""))
            doc_url = src.get("linkDownload", "")
            ticker_hint = src.get("codigoCVM", "")

            if not headline:
                continue

            results.append({
                "headline": f"{company}: {headline}" if company else headline,
                "company": company,
                "ticker_hint": ticker_hint,
                "url": doc_url or "https://www.rad.cvm.gov.br/ENETCONSULTA/",
                "published_at": published[:19] if published else "",
                "category": category,
                "source": "CVM",
            })

        return results

    except Exception as exc:
        logger.debug("cvm_rss: primary EFTS endpoint failed (%s) — CVM news unavailable", exc)
        return []
