"""Radar de Oportunidades — gera relatório de ativos descontados em 4 categorias.

Diferente do scanner de quedas (alerta de crash), o radar analisa:
- Ações: desconto vs máxima 52 semanas + P/L + setor
- FIIs: desconto vs 52s + P/VP referência + DY estimado
- Crypto: desconto vs ATH histórico (CoinGecko)
- Renda Fixa: melhores taxas do Tesouro Direto em cache

Cache: Redis key "opportunity_detector:radar_report", TTL 30min.
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

import redis as sync_redis
import requests

logger = logging.getLogger(__name__)

RADAR_CACHE_KEY = "opportunity_detector:radar_report"
RADAR_CACHE_TTL = 1800  # 30 minutes

# ---------------------------------------------------------------------------
# Curated asset lists
# ---------------------------------------------------------------------------

# Full IBOV + selected mid caps — expanded for BRAPI Pro (no rate limit)
RADAR_ACOES: list[dict] = [
    # Petróleo & Gás
    {"ticker": "PETR4", "name": "Petrobras PN",       "setor": "Petróleo & Gás"},
    {"ticker": "PRIO3", "name": "PRIO",               "setor": "Petróleo & Gás"},
    {"ticker": "RECV3", "name": "PetroRecôncavo",     "setor": "Petróleo & Gás"},
    {"ticker": "VBBR3", "name": "Vibra Energia",      "setor": "Petróleo & Gás"},
    {"ticker": "RAIZ4", "name": "Raízen",             "setor": "Petróleo & Gás"},
    # Mineração & Siderurgia
    {"ticker": "VALE3", "name": "Vale",               "setor": "Mineração"},
    {"ticker": "CSNA3", "name": "CSN",                "setor": "Siderurgia"},
    {"ticker": "GGBR4", "name": "Gerdau PN",          "setor": "Siderurgia"},
    {"ticker": "USIM5", "name": "Usiminas PNA",       "setor": "Siderurgia"},
    # Bancos & Financeiro
    {"ticker": "ITUB4", "name": "Itaú Unibanco",      "setor": "Bancos"},
    {"ticker": "BBAS3", "name": "Banco do Brasil",    "setor": "Bancos"},
    {"ticker": "BBDC4", "name": "Bradesco PN",        "setor": "Bancos"},
    {"ticker": "SANB11","name": "Santander",           "setor": "Bancos"},
    {"ticker": "BPAN4", "name": "Banco Pan",          "setor": "Bancos"},
    {"ticker": "B3SA3", "name": "B3",                 "setor": "Financeiro"},
    {"ticker": "BBSE3", "name": "BB Seguridade",      "setor": "Seguros"},
    {"ticker": "IRBR3", "name": "IRB Brasil RE",      "setor": "Seguros"},
    {"ticker": "CIEL3", "name": "Cielo",              "setor": "Meios de Pagamento"},
    # Energia Elétrica
    {"ticker": "EGIE3", "name": "Engie Brasil",       "setor": "Energia Elétrica"},
    {"ticker": "ELET3", "name": "Eletrobras ON",      "setor": "Energia Elétrica"},
    {"ticker": "CMIG4", "name": "Cemig PN",           "setor": "Energia Elétrica"},
    {"ticker": "CPFE3", "name": "CPFL Energia",       "setor": "Energia Elétrica"},
    {"ticker": "ENEV3", "name": "Eneva",              "setor": "Energia Elétrica"},
    {"ticker": "ENBR3", "name": "Energias BR",        "setor": "Energia Elétrica"},
    {"ticker": "AURE3", "name": "Auren Energia",      "setor": "Energia Elétrica"},
    {"ticker": "TAEE11","name": "Taesa",               "setor": "Energia Elétrica"},
    # Saneamento
    {"ticker": "SBSP3", "name": "Sabesp",             "setor": "Saneamento"},
    {"ticker": "CSAN3", "name": "Cosan",              "setor": "Saneamento"},
    # Consumo & Varejo
    {"ticker": "ABEV3", "name": "Ambev",              "setor": "Bebidas"},
    {"ticker": "JBSS3", "name": "JBS",                "setor": "Alimentos"},
    {"ticker": "BEEF3", "name": "Minerva Foods",      "setor": "Alimentos"},
    {"ticker": "SMTO3", "name": "São Martinho",       "setor": "Açúcar & Álcool"},
    {"ticker": "BEEF3", "name": "Minerva Foods",      "setor": "Alimentos"},
    {"ticker": "SLCE3", "name": "SLC Agrícola",       "setor": "Agro"},
    {"ticker": "LREN3", "name": "Lojas Renner",       "setor": "Varejo"},
    {"ticker": "MGLU3", "name": "Magazine Luiza",     "setor": "Varejo"},
    {"ticker": "PETZ3", "name": "Petz",               "setor": "Varejo"},
    # Locação & Logística
    {"ticker": "RENT3", "name": "Localiza",           "setor": "Locação de Veículos"},
    {"ticker": "MOVI3", "name": "Movida",             "setor": "Locação de Veículos"},
    {"ticker": "LOGG3", "name": "Log Commercial",     "setor": "Logística"},
    # Papel, Celulose & Madeira
    {"ticker": "SUZB3", "name": "Suzano",             "setor": "Papel & Celulose"},
    {"ticker": "KLBN11","name": "Klabin",              "setor": "Papel & Celulose"},
    {"ticker": "DXCO3", "name": "Dexco",              "setor": "Construção"},
    # Industrial & Tecnologia
    {"ticker": "WEGE3", "name": "WEG",                "setor": "Industrial"},
    {"ticker": "EMBR3", "name": "Embraer",            "setor": "Aeronáutica"},
    {"ticker": "TOTS3", "name": "Totvs",              "setor": "Tecnologia"},
    {"ticker": "TOTVS3","name": "Totvs ON",           "setor": "Tecnologia"},
    {"ticker": "LWSA3", "name": "Locaweb",            "setor": "Tecnologia"},
    {"ticker": "GETL3", "name": "Getnet",             "setor": "Tecnologia"},
    # Saúde
    {"ticker": "RDOR3", "name": "Rede D'Or",          "setor": "Saúde"},
    {"ticker": "HAPV3", "name": "Hapvida",            "setor": "Saúde"},
    {"ticker": "FLRY3", "name": "Fleury",             "setor": "Saúde"},
    {"ticker": "RADL3", "name": "Raia Drogasil",      "setor": "Farmácias"},
    {"ticker": "ODPV3", "name": "Odontoprev",         "setor": "Saúde"},
    # Imobiliário
    {"ticker": "MRVE3", "name": "MRV",                "setor": "Construção Civil"},
    {"ticker": "CYRE3", "name": "Cyrela",             "setor": "Construção Civil"},
    {"ticker": "EZTC3", "name": "EZTEC",              "setor": "Construção Civil"},
    {"ticker": "DIRR3", "name": "Direcional",         "setor": "Construção Civil"},
    # Telecomunicações
    {"ticker": "VIVT3", "name": "Vivo",               "setor": "Telecomunicações"},
    {"ticker": "TIMS3", "name": "TIM",                "setor": "Telecomunicações"},
    # Educação
    {"ticker": "COGN3", "name": "Cogna",              "setor": "Educação"},
    {"ticker": "YDUQ3", "name": "Yduqs",              "setor": "Educação"},
    {"ticker": "ANIM3", "name": "Ânima",              "setor": "Educação"},
]

# Top FIIs to scan — expanded to 25 with reference P/VP
RADAR_FIIS: list[dict] = [
    # Papel / CRI (renda fixa imobiliária)
    {"ticker": "KNCR11", "name": "Kinea Rendimentos",       "segmento": "Papel (CRI)",    "pvp_ref": 1.00},
    {"ticker": "MXRF11", "name": "Maxi Renda",              "segmento": "Papel (CRI)",    "pvp_ref": 1.00},
    {"ticker": "IRDM11", "name": "Iridium Recebíveis",      "segmento": "Papel (CRI)",    "pvp_ref": 1.00},
    {"ticker": "XPCA11", "name": "XP Crédito Agrícola",     "segmento": "Papel (CRI)",    "pvp_ref": 1.00},
    {"ticker": "RZTR11", "name": "Riza Terrax",              "segmento": "Papel (CRI)",    "pvp_ref": 1.00},
    {"ticker": "HCTR11", "name": "Hectare CE",              "segmento": "Papel (CRI)",    "pvp_ref": 1.00},
    # Logística
    {"ticker": "HGLG11", "name": "Pátria Logística",        "segmento": "Logística",      "pvp_ref": 1.05},
    {"ticker": "BTLG11", "name": "BTG Pactual Logística",   "segmento": "Logística",      "pvp_ref": 1.05},
    {"ticker": "BRCO11", "name": "Bresco Logística",        "segmento": "Logística",      "pvp_ref": 1.05},
    {"ticker": "XPLG11", "name": "XP Log",                  "segmento": "Logística",      "pvp_ref": 1.05},
    {"ticker": "LVBI11", "name": "VBI Logística",           "segmento": "Logística",      "pvp_ref": 1.00},
    # Shopping / Varejo
    {"ticker": "XPML11", "name": "XP Malls",                "segmento": "Shopping",       "pvp_ref": 1.05},
    {"ticker": "VISC11", "name": "Vinci Shopping Centers",  "segmento": "Shopping",       "pvp_ref": 1.05},
    {"ticker": "HSML11", "name": "HSI Malls",               "segmento": "Shopping",       "pvp_ref": 1.00},
    {"ticker": "MALL11", "name": "Malls Brasil Plural",     "segmento": "Shopping",       "pvp_ref": 1.00},
    # Escritórios
    {"ticker": "HGRE11", "name": "CSHG Real Estate",        "segmento": "Lajes Corporativas","pvp_ref": 0.90},
    {"ticker": "RBRP11", "name": "RBR Properties",          "segmento": "Lajes Corporativas","pvp_ref": 0.90},
    {"ticker": "BRCR11", "name": "BC Fund",                 "segmento": "Lajes Corporativas","pvp_ref": 0.85},
    # Fundo de Fundos (FoF)
    {"ticker": "BCFF11", "name": "BTG Pactual FoF",         "segmento": "Fundo de Fundos", "pvp_ref": 0.95},
    {"ticker": "HFOF11", "name": "Hedge FoF",               "segmento": "Fundo de Fundos", "pvp_ref": 0.95},
    {"ticker": "RBRF11", "name": "RBR Alpha",               "segmento": "Fundo de Fundos", "pvp_ref": 0.95},
    {"ticker": "KNRI11", "name": "Kinea Renda Imóveis",     "segmento": "Híbrido",         "pvp_ref": 1.00},
    # Residencial
    {"ticker": "HASI11", "name": "Habitat Imóveis Aluguel", "segmento": "Residencial",     "pvp_ref": 1.00},
    # Saúde / Outros
    {"ticker": "HCRI11", "name": "Hospital da Criança",     "segmento": "Saúde",           "pvp_ref": 1.00},
    {"ticker": "GGRC11", "name": "GGR Covepi",              "segmento": "Logística",       "pvp_ref": 1.00},
]

# Crypto symbols via Binance (USDT) and CoinGecko IDs
RADAR_CRYPTO: list[dict] = [
    {"symbol": "BTCUSDT", "coingecko_id": "bitcoin",  "name": "Bitcoin (BTC)",  "currency": "USDT"},
    {"symbol": "ETHUSDT", "coingecko_id": "ethereum", "name": "Ethereum (ETH)", "currency": "USDT"},
]

# Tesouro types we want to highlight in the report
TESOURO_PRIORITY = ["PREFIXADO", "IPCA", "SELIC"]


# ---------------------------------------------------------------------------
# Redis helper
# ---------------------------------------------------------------------------

def _get_redis() -> sync_redis.Redis:
    url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    return sync_redis.Redis.from_url(url, decode_responses=True)


def _get_brapi_token() -> str:
    return os.environ.get("BRAPI_TOKEN", "")


# ---------------------------------------------------------------------------
# Ações radar
# ---------------------------------------------------------------------------

def _fetch_brapi_quote_simple(ticker: str, token: str) -> Optional[dict]:
    try:
        resp = requests.get(
            f"https://brapi.dev/api/quote/{ticker}",
            params={"token": token},
            timeout=8,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return results[0] if results else None
    except Exception as exc:
        logger.warning("BRAPI simple quote error %s: %s", ticker, exc)
        return None


def _build_acoes_radar(token: str) -> list[dict]:
    items = []
    for asset in RADAR_ACOES:
        quote = _fetch_brapi_quote_simple(asset["ticker"], token)
        if not quote:
            continue

        current = quote.get("regularMarketPrice")
        high_52w = quote.get("fiftyTwoWeekHigh")
        low_52w = quote.get("fiftyTwoWeekLow")
        pl = quote.get("priceEarnings")

        if not current or not high_52w or high_52w == 0:
            continue

        discount_pct = ((current - high_52w) / high_52w) * 100

        # Score signal: how deep is the discount, is P/L reasonable?
        signal = _acao_signal(discount_pct, pl)

        items.append({
            "ticker": asset["ticker"],
            "name": asset["name"],
            "setor": asset["setor"],
            "current_price": round(current, 2),
            "high_52w": round(high_52w, 2),
            "low_52w": round(low_52w, 2) if low_52w else None,
            "discount_from_high_pct": round(discount_pct, 1),
            "pl": round(pl, 1) if pl else None,
            "signal": signal,
            "logo_url": quote.get("logourl"),
        })

        time.sleep(0.3)  # BRAPI rate limit

    # Sort: biggest discount first
    items.sort(key=lambda x: x["discount_from_high_pct"])
    return items


def _acao_signal(discount_pct: float, pl: Optional[float]) -> str:
    if discount_pct <= -30:
        return "🔴 Queda expressiva — verificar fundamentos"
    elif discount_pct <= -20:
        if pl and pl < 20:
            return "🟢 Desconto histórico + P/L atrativo"
        return "🟡 Desconto relevante — analisar causa"
    elif discount_pct <= -10:
        if pl and pl < 15:
            return "🟢 Desconto moderado + valuation baixo"
        return "🟡 Desconto moderado"
    elif discount_pct <= -5:
        return "⚪ Desconto leve"
    else:
        return "⚪ Próximo da máxima"


# ---------------------------------------------------------------------------
# FIIs radar
# ---------------------------------------------------------------------------

def _build_fiis_radar(token: str) -> list[dict]:
    items = []
    for asset in RADAR_FIIS:
        quote = _fetch_brapi_quote_simple(asset["ticker"], token)
        if not quote:
            continue

        current = quote.get("regularMarketPrice")
        high_52w = quote.get("fiftyTwoWeekHigh")
        low_52w = quote.get("fiftyTwoWeekLow")

        if not current or not high_52w or high_52w == 0:
            continue

        discount_pct = ((current - high_52w) / high_52w) * 100

        # Estimate DY from dividends endpoint
        dy_est = _estimate_fii_dy(asset["ticker"], current, token)

        signal = _fii_signal(discount_pct, dy_est, asset["segmento"])

        items.append({
            "ticker": asset["ticker"],
            "name": asset["name"],
            "segmento": asset["segmento"],
            "current_price": round(current, 2),
            "high_52w": round(high_52w, 2),
            "low_52w": round(low_52w, 2) if low_52w else None,
            "discount_from_high_pct": round(discount_pct, 1),
            "dy_anual_pct": round(dy_est, 1) if dy_est else None,
            "signal": signal,
        })

        time.sleep(0.3)

    items.sort(key=lambda x: x["discount_from_high_pct"])
    return items


def _estimate_fii_dy(ticker: str, current_price: float, token: str) -> Optional[float]:
    """Estimate annual DY from last 12 months dividends via BRAPI."""
    try:
        resp = requests.get(
            f"https://brapi.dev/api/quote/{ticker}",
            params={"token": token, "modules": "dividendsData"},
            timeout=8,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            return None
        dividends = results[0].get("dividendsData", {})
        if not dividends:
            return None
        cash_divs = dividends.get("cashDividends", [])
        if not cash_divs:
            return None

        # Sum dividends from last 12 months
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=365)
        total_div = 0.0
        for div in cash_divs:
            pay_date_str = div.get("paymentDate") or div.get("approvedOn", "")
            if not pay_date_str:
                continue
            try:
                pay_date = datetime.fromisoformat(pay_date_str.replace("Z", "+00:00"))
                if pay_date.tzinfo is None:
                    pay_date = pay_date.replace(tzinfo=timezone.utc)
                if pay_date >= cutoff:
                    total_div += float(div.get("rate", 0))
            except Exception:
                pass

        if total_div > 0 and current_price > 0:
            return (total_div / current_price) * 100
        return None
    except Exception as exc:
        logger.debug("FII DY estimate error %s: %s", ticker, exc)
        return None


def _fii_signal(discount_pct: float, dy: Optional[float], segmento: str) -> str:
    dy_str = f" + DY ~{dy:.1f}%" if dy else ""
    if discount_pct <= -15:
        return f"🔴 Queda forte{dy_str}"
    elif discount_pct <= -8:
        if dy and dy >= 10:
            return f"🟢 Desconto + DY alto{dy_str}"
        return f"🟡 Desconto relevante{dy_str}"
    elif discount_pct <= -3:
        if dy and dy >= 11:
            return f"🟢 DY atrativo{dy_str}"
        return f"⚪ Desconto leve{dy_str}"
    else:
        return f"⚪ Próximo da máxima{dy_str}"


# ---------------------------------------------------------------------------
# Crypto radar
# ---------------------------------------------------------------------------

def _fetch_coingecko_data(coingecko_id: str) -> Optional[dict]:
    """Fetch market data from CoinGecko for a single coin.

    Returns raw market_data dict or None if the API is unavailable.
    Wrapped separately so callers can apply gracious fallback.
    """
    try:
        resp = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{coingecko_id}",
            params={
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "false",
                "developer_data": "false",
            },
            timeout=12,
        )
        resp.raise_for_status()
        return resp.json().get("market_data", {})
    except Exception as exc:
        logger.warning(
            "CoinGecko unavailable for %s (%s) — skipping ATH check",
            coingecko_id,
            exc,
        )
        return None


def _build_crypto_radar() -> list[dict]:
    items = []
    for asset in RADAR_CRYPTO:
        try:
            md = _fetch_coingecko_data(asset["coingecko_id"])

            current_brl = md.get("current_price", {}).get("brl") if md else None
            ath_brl = md.get("ath", {}).get("brl") if md else None
            ath_date = md.get("ath_date", {}).get("brl", "") if md else ""
            current_usd = md.get("current_price", {}).get("usd") if md else None
            ath_usd = md.get("ath", {}).get("usd") if md else None
            change_24h = md.get("price_change_percentage_24h") if md else None
            change_30d = md.get("price_change_percentage_30d") if md else None
            change_1y = md.get("price_change_percentage_1y") if md else None

            if not current_brl:
                # CoinGecko unavailable — include asset with partial data so
                # the radar still returns a row (no ATH info shown)
                if md is None:
                    items.append({
                        "symbol": asset["coingecko_id"].upper()[:3],
                        "name": asset["name"],
                        "current_price_brl": None,
                        "current_price_usd": None,
                        "ath_brl": None,
                        "ath_usd": None,
                        "ath_date": "",
                        "discount_from_ath_pct": None,
                        "change_24h_pct": None,
                        "change_30d_pct": None,
                        "change_1y_pct": None,
                        "signal": "⚠️ CoinGecko indisponível — dados ATH ausentes",
                    })
                continue

            if not ath_brl:
                discount_pct = None
                signal = "⚪ ATH indisponível"
            else:
                discount_pct = ((current_brl - ath_brl) / ath_brl) * 100
                signal = _crypto_signal(discount_pct, change_30d)

            # Format ATH date
            ath_date_fmt = ""
            if ath_date:
                try:
                    dt = datetime.fromisoformat(ath_date.replace("Z", "+00:00"))
                    ath_date_fmt = dt.strftime("%b/%Y")
                except Exception:
                    ath_date_fmt = ath_date[:7]

            items.append({
                "symbol": asset["coingecko_id"].upper()[:3],
                "name": asset["name"],
                "current_price_brl": round(current_brl, 0),
                "current_price_usd": round(current_usd, 0) if current_usd else None,
                "ath_brl": round(ath_brl, 0) if ath_brl else None,
                "ath_usd": round(ath_usd, 0) if ath_usd else None,
                "ath_date": ath_date_fmt,
                "discount_from_ath_pct": round(discount_pct, 1) if discount_pct is not None else None,
                "change_24h_pct": round(change_24h, 1) if change_24h else None,
                "change_30d_pct": round(change_30d, 1) if change_30d else None,
                "change_1y_pct": round(change_1y, 1) if change_1y else None,
                "signal": signal,
            })

            time.sleep(1.5)  # CoinGecko free tier: 30 req/min

        except Exception as exc:
            logger.warning("CoinGecko error for %s: %s", asset["coingecko_id"], exc)

    return items


def _crypto_signal(discount_pct: float, change_30d: Optional[float]) -> str:
    if discount_pct <= -50:
        return "🟢 >50% abaixo do ATH — ciclo histórico de compra"
    elif discount_pct <= -40:
        return "🟢 ~40-50% abaixo do ATH — desconto relevante"
    elif discount_pct <= -25:
        return "🟡 25-40% abaixo do ATH — correção significativa"
    elif discount_pct <= -10:
        return "⚪ Correção leve do ATH"
    else:
        return "🔵 Próximo do ATH"


# ---------------------------------------------------------------------------
# Renda Fixa radar
# ---------------------------------------------------------------------------

def _build_renda_fixa_radar(r: sync_redis.Redis) -> list[dict]:
    """Fetch best Tesouro Direto rates from Redis cache."""
    items = []

    # Try Redis cache from tesouro refresh task
    tesouro_keys = r.keys("tesouro:rates:*")

    # Also fetch live from the API as fallback
    if not tesouro_keys:
        return _fetch_tesouro_live()

    seen_types: dict[str, dict] = {}  # best rate per type

    for key in tesouro_keys:
        try:
            raw = r.get(key)
            if not raw:
                continue
            bond = json.loads(raw)
            bond_name = bond.get("name", "")
            annual_rate = bond.get("annual_rate")
            if not annual_rate:
                continue

            # Group by simplified type
            bond_type = _classify_tesouro(bond_name)
            if bond_type not in seen_types or annual_rate > seen_types[bond_type]["annual_rate"]:
                seen_types[bond_type] = {**bond, "bond_type": bond_type}
        except Exception:
            pass

    for bond_type, bond in seen_types.items():
        annual_rate = bond.get("annual_rate", 0)
        maturity = bond.get("maturity_date") or bond.get("vencimento") or ""
        signal = _renda_fixa_signal(bond_type, annual_rate * 100 if annual_rate < 1 else annual_rate)
        items.append({
            "tipo": bond_type,
            "taxa_pct": round(annual_rate * 100 if annual_rate < 1 else annual_rate, 2),
            "vencimento": maturity,
            "signal": signal,
        })

    if not items:
        return _fetch_tesouro_live()

    items.sort(key=lambda x: -x["taxa_pct"])
    return items[:6]


def _fetch_tesouro_live() -> list[dict]:
    """Fetch Tesouro Direto rates from CKAN CSV (same source as screener_v2)."""
    import csv, io
    CKAN_CSV_URL = (
        "https://www.tesourotransparente.gov.br/ckan/dataset/"
        "df56aa42-484a-4a59-8184-7676580c81e3/resource/"
        "796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv"
    )
    try:
        resp = requests.get(CKAN_CSV_URL, timeout=30)
        resp.raise_for_status()
        all_rows = list(csv.DictReader(io.StringIO(resp.text), delimiter=";"))

        def _parse_date(s: str):
            try:
                p = s.strip().split("/")
                return (int(p[2]), int(p[1]), int(p[0])) if len(p) == 3 else (0, 0, 0)
            except Exception:
                return (0, 0, 0)

        dates = {r.get("Data Base", "").strip() for r in all_rows if r.get("Data Base", "").strip()}
        if not dates:
            return []
        latest_date = max(dates, key=_parse_date)

        seen_types: dict[str, dict] = {}
        for row in all_rows:
            if row.get("Data Base", "").strip() != latest_date:
                continue
            tipo = row.get("Tipo Titulo", "").strip()
            vencimento = row.get("Data Vencimento", "").strip()
            taxa_str = row.get("Taxa Compra Manha", "").strip().replace(",", ".")
            try:
                taxa = float(taxa_str) if taxa_str else 0.0
            except Exception:
                taxa = 0.0
            if taxa <= 0:
                continue
            bond_type = _classify_tesouro(tipo)
            if bond_type not in seen_types or taxa > seen_types[bond_type]["taxa_pct"]:
                seen_types[bond_type] = {
                    "tipo": bond_type,
                    "taxa_pct": round(taxa, 2),
                    "vencimento": vencimento,
                    "signal": _renda_fixa_signal(bond_type, taxa),
                }

        result = list(seen_types.values())
        result.sort(key=lambda x: -x["taxa_pct"])
        return result[:6]
    except Exception as exc:
        logger.warning("Tesouro CKAN fetch error: %s", exc)
        return []


def _classify_tesouro(name: str) -> str:
    n = name.upper()
    if "SELIC" in n:
        return "Tesouro Selic"
    elif "PREFIXADO" in n and "SEMESTRAIS" in n:
        return "Tesouro Prefixado c/ Juros Semestrais"
    elif "PREFIXADO" in n:
        return "Tesouro Prefixado"
    elif "IPCA" in n and "SEMESTRAIS" in n:
        return "Tesouro IPCA+ c/ Juros Semestrais"
    elif "IPCA" in n:
        return "Tesouro IPCA+"
    elif "IGPM" in n:
        return "Tesouro IGPM+"
    elif "EDUCA" in n:
        return "Tesouro Educa+"
    elif "RENDA" in n:
        return "Tesouro Renda+"
    return name[:30]


def _renda_fixa_signal(bond_type: str, taxa: float) -> str:
    if "PREFIXADO" in bond_type:
        if taxa >= 14:
            return "🟢 Taxa historicamente alta — oportunidade de travamento"
        elif taxa >= 12:
            return "🟡 Taxa acima da média histórica"
        return "⚪ Taxa moderada"
    elif "IPCA" in bond_type:
        if taxa >= 7.5:
            return "🟢 Juro real >7.5% — excelente proteção inflacionária"
        elif taxa >= 6:
            return "🟡 Juro real alto"
        return "⚪ Juro real moderado"
    elif "SELIC" in bond_type:
        return "⚪ Segurança máxima + liquidez diária"
    return "⚪ Consulte as condições"


# ---------------------------------------------------------------------------
# Macro snapshot
# ---------------------------------------------------------------------------

def _get_macro_snapshot(r: sync_redis.Redis) -> dict:
    try:
        raw = r.get("macro:snapshot")
        if raw:
            data = json.loads(raw)
            return {
                "selic": float(data.get("selic", 0)),
                "cdi": float(data.get("cdi", 0)),
                "ipca": float(data.get("ipca", 0)),
                "ptax_usd": float(data.get("ptax_usd", 0)),
            }
    except Exception:
        pass
    return {"selic": 14.65, "cdi": 14.65, "ipca": 0.7, "ptax_usd": 5.17}


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def generate_radar_report(force_refresh: bool = False) -> dict:
    """Generate or return cached radar report."""
    r = _get_redis()

    if not force_refresh:
        cached = r.get(RADAR_CACHE_KEY)
        if cached:
            try:
                return json.loads(cached)
            except Exception:
                pass

    logger.info("Generating fresh radar report...")
    token = _get_brapi_token()

    macro = _get_macro_snapshot(r)
    acoes = _build_acoes_radar(token)
    fiis = _build_fiis_radar(token)
    crypto = _build_crypto_radar()
    renda_fixa = _build_renda_fixa_radar(r)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cache_expires_in_minutes": 30,
        "macro": macro,
        "acoes": acoes,
        "fiis": fiis,
        "crypto": crypto,
        "renda_fixa": renda_fixa,
    }

    r.set(RADAR_CACHE_KEY, json.dumps(report), ex=RADAR_CACHE_TTL)
    logger.info(
        "Radar report cached: %d ações, %d FIIs, %d crypto, %d renda fixa",
        len(acoes), len(fiis), len(crypto), len(renda_fixa),
    )
    return report


def get_cached_radar_report() -> Optional[dict]:
    """Return cached report or None."""
    r = _get_redis()
    cached = r.get(RADAR_CACHE_KEY)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass
    return None
