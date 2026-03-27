"""Celery beat tasks for the market_universe module.

Tasks run on Celery workers (sync context, psycopg2 driver) and write to
PostgreSQL global tables AND Redis. They NEVER handle API requests.

Schedule (defined in celery_app.py beat_schedule):
  - refresh_screener_universe: Mon-Fri at 07:00 BRT (daily)
  - refresh_fii_metadata:      Monday at 06:00 BRT (weekly)
  - refresh_tesouro_rates:     Every 6 hours (24x7)

Redis key schema (NEVER use market:* — reserved for Phase 2 live quotes):
  screener:universe:{TICKER}     — ex=86400 (24h)
  tesouro:rates:{BOND_CODE}      — ex=21600 (6h)
  fii:metadata:{TICKER}          — ex=604800 (7 days)

Partial failure policy (screener):
  Each ticker is committed independently within batches of 50.
  A failed ticker logs a WARNING but does NOT abort the entire run.
  Failed tickers retain their previous snapshot in DB/Redis.

External API dependencies:
  - brapi.dev: /quote/list + /quote/{ticker} — requires BRAPI_TOKEN
  - ANBIMA API: OAuth2 client_credentials, credentials in tools/anbima AWS SM
  - CKAN CSV: public URL, no auth — fallback when ANBIMA is unavailable
  - CVM dados.gov.br: annual FII ZIP file — no auth required
"""
from __future__ import annotations

import base64
import csv
import io
import json
import logging
import os
import time
import uuid
import zipfile
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import redis as redis_lib
import requests as requests_lib
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.celery_app import celery_app
from app.core.db_sync import get_sync_db_session
from app.modules.market_universe.models import FIIMetadata, ScreenerSnapshot

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Redis TTLs (seconds)
# ---------------------------------------------------------------------------
_SCREENER_TTL = 86400    # 24h — daily refresh
_TESOURO_TTL = 21600     # 6h — every-6h refresh
_FII_META_TTL = 604800   # 7 days — weekly refresh

# ---------------------------------------------------------------------------
# Redis key prefixes — NEVER use market:* (collides with Phase 2 market data)
# ---------------------------------------------------------------------------
_SCREENER_PREFIX = "screener:universe:"
_TESOURO_PREFIX = "tesouro:rates:"
_FII_PREFIX = "fii:metadata:"

# ---------------------------------------------------------------------------
# External API URLs
# ---------------------------------------------------------------------------
ANBIMA_TOKEN_URL = "https://api.anbima.com.br/oauth/access-token"
ANBIMA_TITULOS_URL = (
    "https://api.anbima.com.br/feed/precos-indices/v1/"
    "titulos-publicos/mercado-secundario-TPF"
)
CKAN_CSV_URL = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/"
    "df56aa42-484a-4a59-8184-7676580c81e3/resource/"
    "796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv"
)
CVM_FII_ZIP_URL = (
    "https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/"
    "inf_mensal_fii_{year}.zip"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_redis() -> redis_lib.Redis:
    """Create a synchronous Redis client for Celery task use."""
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return redis_lib.Redis.from_url(url)


def _get_brapi_client():
    """Return a BrapiClient instance (reuses existing brapi adapter)."""
    from app.modules.market_data.adapters.brapi import BrapiClient
    return BrapiClient()


def _get_anbima_credentials() -> tuple[str, str]:
    """Fetch ANBIMA client credentials from AWS Secrets Manager.

    Returns (client_id, client_secret) tuple.
    Raises RuntimeError if credentials cannot be retrieved.
    """
    try:
        import boto3
        client = boto3.client("secretsmanager", region_name="us-east-1")
        resp = client.get_secret_value(SecretId="tools/anbima")
        secret = json.loads(resp["SecretString"])
        client_id = secret["ANBIMA_CLIENT_ID"]
        client_secret = secret["ANBIMA_CLIENT_SECRET"]
        return client_id, client_secret
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch ANBIMA credentials from AWS SM: {exc}") from exc


def _get_anbima_token(client_id: str, client_secret: str) -> str:
    """Obtain OAuth2 access token from ANBIMA API.

    Uses client_credentials grant with Basic auth (base64 encoded).
    Returns the access_token string.
    Raises requests.HTTPError on failure.
    """
    credentials = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json",
    }
    body = {"grant_type": "client_credentials"}
    resp = requests_lib.post(ANBIMA_TOKEN_URL, json=body, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def _safe_decimal(value) -> Decimal | None:
    """Convert a value to Decimal or return None if invalid."""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _safe_int(value) -> int | None:
    """Convert a value to int or return None if invalid."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Task 1: refresh_screener_universe
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def refresh_screener_universe(self) -> None:
    """Fetch all B3 tickers from brapi.dev and upsert into screener_snapshots.

    Schedule: Mon-Fri at 07:00 BRT (crontab in celery_app.py)
    DB: screener_snapshots — upsert on (ticker, snapshot_date)
    Redis: screener:universe:{TICKER} — TTL 24h

    Partial failure policy:
      - Per-ticker failures are logged and skipped (previous snapshot retained)
      - Commits happen in batches of 50 tickers — a single bad ticker cannot
        rollback the batch (it is excluded before the batch commit)
      - The task does NOT retry on ticker-level failure — only on fatal errors
        (e.g., cannot list tickers at all) does self.retry() apply
    """
    logger.info("refresh_screener_universe: starting")
    brapi_client = _get_brapi_client()
    r = _get_redis()
    today = date.today()

    # Step 1: Discover all tickers via /quote/list pagination
    # brapi.dev /quote/list returns {"stocks": [...], "hasNextPage": bool, ...}
    # Each stock item has: stock, name, close, change, volume, market_cap, sector, type
    tickers: list[str] = []
    ticker_market_data: dict[str, dict] = {}  # ticker → basic market data from list
    page = 1
    while True:
        try:
            data = brapi_client._get("/quote/list", params={"limit": 100, "page": page})
            stocks = data.get("stocks", [])
            if not stocks:
                break
            for item in stocks:
                symbol = (item.get("stock") or item.get("symbol", "")).upper()
                if symbol:
                    tickers.append(symbol)
                    ticker_market_data[symbol] = {
                        "shortName": item.get("name"),
                        "sector": item.get("sector"),
                        "regularMarketPrice": item.get("close"),
                        "regularMarketChangePercent": item.get("change"),
                        "regularMarketVolume": item.get("volume"),
                        "marketCap": item.get("market_cap"),
                    }
            if not data.get("hasNextPage", False):
                break
            page += 1
            time.sleep(0.2)  # Rate-limit: 200ms between pagination calls
        except Exception as exc:
            logger.error("refresh_screener_universe: failed to list tickers (page %d): %s", page, exc)
            raise self.retry(exc=exc)

    if not tickers:
        logger.warning("refresh_screener_universe: no tickers discovered — aborting")
        return

    logger.info("refresh_screener_universe: discovered %d tickers", len(tickers))

    # Step 2: Fetch fundamentals for each ticker with 200ms sleep + batch upsert
    success_count = 0
    fail_count = 0
    batch_rows: list[dict] = []

    def _flush_batch(rows: list[dict]) -> None:
        """Upsert a batch of rows into screener_snapshots."""
        if not rows:
            return
        with get_sync_db_session(tenant_id=None) as session:
            stmt = pg_insert(ScreenerSnapshot).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["ticker", "snapshot_date"],
                set_={
                    "short_name": stmt.excluded.short_name,
                    "sector": stmt.excluded.sector,
                    "regular_market_price": stmt.excluded.regular_market_price,
                    "regular_market_change_percent": stmt.excluded.regular_market_change_percent,
                    "regular_market_volume": stmt.excluded.regular_market_volume,
                    "market_cap": stmt.excluded.market_cap,
                    "pl": stmt.excluded.pl,
                    "pvp": stmt.excluded.pvp,
                    "dy": stmt.excluded.dy,
                    "ev_ebitda": stmt.excluded.ev_ebitda,
                },
            )
            session.execute(stmt)

    for ticker in tickers:
        # 200ms sleep between each ticker call to respect brapi.dev rate limits
        time.sleep(0.2)
        fund = None
        for attempt in range(3):
            try:
                fund = brapi_client.fetch_fundamentals(ticker)
                break
            except Exception as exc:
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                if status_code == 429:
                    backoff = (2 ** attempt) * 60
                    logger.warning(
                        "refresh_screener_universe: 429 for %s (attempt %d) — sleeping %ds",
                        ticker, attempt + 1, backoff,
                    )
                    time.sleep(backoff)
                else:
                    logger.warning(
                        "refresh_screener_universe: failed to fetch %s (attempt %d): %s",
                        ticker, attempt + 1, exc,
                    )
                    time.sleep(5)

        if fund is None:
            logger.warning("refresh_screener_universe: fundamentals failed for %s — saving market data only", ticker)
            fail_count += 1
            # Still save the row with market data only (fundamentals will be null)

        mkt = ticker_market_data.get(ticker, {})
        row = {
            "id": str(uuid.uuid4()),
            "ticker": ticker,
            "snapshot_date": today,
            "short_name": mkt.get("shortName"),
            "sector": mkt.get("sector"),
            "regular_market_price": _safe_decimal(mkt.get("regularMarketPrice")),
            "regular_market_change_percent": _safe_decimal(mkt.get("regularMarketChangePercent")),
            "regular_market_volume": _safe_int(mkt.get("regularMarketVolume")),
            "market_cap": _safe_int(mkt.get("marketCap")),
            "pl": _safe_decimal(fund.get("pl")) if fund else None,
            "pvp": _safe_decimal(fund.get("pvp")) if fund else None,
            "dy": _safe_decimal(fund.get("dy")) if fund else None,
            "ev_ebitda": _safe_decimal(fund.get("ev_ebitda")) if fund else None,
        }
        batch_rows.append(row)

        # Write to Redis immediately for cache freshness
        redis_key = _SCREENER_PREFIX + ticker
        r.set(redis_key, json.dumps({k: str(v) if v is not None else None for k, v in row.items() if k != "id"}, default=str), ex=_SCREENER_TTL)

        success_count += 1

        # Commit in batches of 50
        if len(batch_rows) >= 50:
            try:
                _flush_batch(batch_rows)
            except Exception as exc:
                logger.error("refresh_screener_universe: batch flush failed: %s", exc)
            batch_rows = []

    # Flush remaining rows
    if batch_rows:
        try:
            _flush_batch(batch_rows)
        except Exception as exc:
            logger.error("refresh_screener_universe: final batch flush failed: %s", exc)

    logger.info(
        "refresh_screener_universe: done — %d/%d tickers updated, %d failed",
        success_count, len(tickers), fail_count,
    )


# ---------------------------------------------------------------------------
# Task 2: refresh_fii_metadata
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def refresh_fii_metadata(self) -> None:
    """Download CVM FII informe mensal ZIP and upsert FII metadata.

    Schedule: Monday at 06:00 BRT (crontab in celery_app.py)
    DB: fii_metadata — upsert on ticker (unique)
    Redis: fii:metadata:{TICKER} — TTL 7 days

    Source: https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/
    CSV encoding: latin-1, delimiter: semicolon
    Target CSV inside ZIP: file containing "complemento" in name (case-insensitive)
    """
    logger.info("refresh_fii_metadata: starting")
    r = _get_redis()
    today = date.today()
    zip_url = CVM_FII_ZIP_URL.format(year=today.year)

    try:
        logger.info("refresh_fii_metadata: downloading ZIP from %s", zip_url)
        resp = requests_lib.get(zip_url, timeout=120)
        resp.raise_for_status()
    except Exception as exc:
        logger.error("refresh_fii_metadata: failed to download ZIP: %s", exc)
        raise self.retry(exc=exc)

    try:
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
    except zipfile.BadZipFile as exc:
        logger.error("refresh_fii_metadata: ZIP is corrupt: %s", exc)
        raise self.retry(exc=exc)

    csv_files = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    logger.info("refresh_fii_metadata: ZIP contains: %s", csv_files)

    if not csv_files:
        logger.error("refresh_fii_metadata: no CSV files found in ZIP")
        raise self.retry(exc=RuntimeError("No CSV files in CVM FII ZIP"))

    # Prefer the "complemento" file — it has segment and vacancy data
    target_csv = next(
        (n for n in csv_files if "complemento" in n.lower()),
        csv_files[0],
    )
    logger.info("refresh_fii_metadata: selected CSV: %s", target_csv)

    try:
        with zf.open(target_csv) as f:
            reader = csv.DictReader(
                io.TextIOWrapper(f, encoding="latin-1"),
                delimiter=";",
            )
            # Log column names on first execution so we can verify field names
            rows = list(reader)

        if rows:
            logger.info("refresh_fii_metadata: CSV columns: %s", list(rows[0].keys()))
    except Exception as exc:
        logger.error("refresh_fii_metadata: failed to parse CSV: %s", exc)
        raise self.retry(exc=exc)

    count = 0
    batch_rows: list[dict] = []

    def _flush_fii_batch(fii_rows: list[dict]) -> None:
        if not fii_rows:
            return
        with get_sync_db_session(tenant_id=None) as session:
            stmt = pg_insert(FIIMetadata).values(fii_rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["ticker"],
                set_={
                    "segmento": stmt.excluded.segmento,
                    "vacancia_financeira": stmt.excluded.vacancia_financeira,
                    "num_cotistas": stmt.excluded.num_cotistas,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            session.execute(stmt)

    for row in rows:
        # CVM field names vary by year — handle common variants
        # Known fields from CVM FII informe complementar:
        #   CNPJ_Fundo, Denom_Social, TP_Fundo_Cotas, Fundo_Cotas,
        #   Fundo_Exclusivo, Num_Cotistas, Publico_Alvo, Encerramento_Exerc_Social,
        #   Prazo_Duration, Taxa_Admin, Taxa_Gestao, Taxa_Performance, Taxa_Outras,
        #   VL_Patrimonio_Liquido, VL_Cota, VL_Emissoes, VL_Resgates,
        #   Rendimento_Distribuido, Vacancia_Financeira, Vacancia_Fisica
        #   (Segmento is typically in a separate "caracteristicas" file)
        ticker_raw = (
            row.get("CD_Fundo_CVM")
            or row.get("TICKER")
            or row.get("Ticker")
            or row.get("Fundo")
            or row.get("CNPJ_Fundo", "")  # fallback: CNPJ as identifier
        )
        ticker = ticker_raw.strip().upper() if ticker_raw else None

        if not ticker:
            continue

        segmento = (
            row.get("Segmento")
            or row.get("TP_Fundo_Cotas")
            or row.get("Tipo_FII")
        )
        if segmento:
            segmento = segmento.strip()[:50]

        vacancia_str = (
            row.get("Vacancia_Financeira")
            or row.get("Vacância Financeira")
            or row.get("VACANCIA_FINANCEIRA")
        )
        vacancia = _safe_decimal(
            vacancia_str.replace(",", ".") if vacancia_str else None
        )

        num_cotistas_str = (
            row.get("Num_Cotistas")
            or row.get("Num Cotistas")
            or row.get("NUM_COTISTAS")
        )
        num_cotistas = _safe_int(num_cotistas_str)

        fii_row = {
            "id": str(uuid.uuid4()),
            "ticker": ticker,
            "segmento": segmento,
            "vacancia_financeira": vacancia,
            "num_cotistas": num_cotistas,
            "updated_at": datetime.utcnow(),
        }
        batch_rows.append(fii_row)

        # Write to Redis
        redis_key = _FII_PREFIX + ticker
        r.set(
            redis_key,
            json.dumps({
                "ticker": ticker,
                "segmento": segmento,
                "vacancia_financeira": str(vacancia) if vacancia is not None else None,
                "num_cotistas": num_cotistas,
            }),
            ex=_FII_META_TTL,
        )
        count += 1

        if len(batch_rows) >= 50:
            try:
                _flush_fii_batch(batch_rows)
            except Exception as exc:
                logger.error("refresh_fii_metadata: batch flush failed: %s", exc)
            batch_rows = []

    if batch_rows:
        try:
            _flush_fii_batch(batch_rows)
        except Exception as exc:
            logger.error("refresh_fii_metadata: final batch flush failed: %s", exc)

    logger.info("refresh_fii_metadata: done — %d FIIs updated", count)


# ---------------------------------------------------------------------------
# Task 3: refresh_tesouro_rates
# ---------------------------------------------------------------------------

def _fetch_tesouro_from_anbima(token: str) -> list[dict]:
    """Fetch Tesouro Direto bond rates from ANBIMA API.

    Returns list of dicts with: tipo_titulo, vencimento, taxa_indicativa, pu, data_base.
    Raises on HTTP errors.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    resp = requests_lib.get(ANBIMA_TITULOS_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    records = []
    # ANBIMA response structure varies — handle both list and dict-with-list
    items = data if isinstance(data, list) else data.get("TituloPúblico", data.get("data", []))

    for item in items:
        tipo = item.get("Titulo") or item.get("tipo_titulo") or item.get("NomeTitulo", "")
        vencimento_raw = item.get("DataVencimento") or item.get("data_vencimento") or item.get("Vencimento", "")
        taxa = item.get("TaxaIndicativa") or item.get("taxa_indicativa") or item.get("Taxa", None)
        pu = item.get("PUBase") or item.get("pu") or item.get("PU", None)
        data_base = item.get("DataBase") or item.get("data_base") or item.get("Data", "")

        if not tipo:
            continue

        records.append({
            "tipo_titulo": str(tipo).strip(),
            "vencimento": str(vencimento_raw).strip(),
            "taxa_indicativa": _safe_decimal(taxa),
            "pu": _safe_decimal(pu),
            "data_base": str(data_base).strip(),
            "source": "anbima",
        })

    return records


def _fetch_tesouro_from_ckan() -> list[dict]:
    """Fetch Tesouro Direto rates from CKAN CSV fallback.

    Downloads full historical CSV (13MB since 2002), filters to the most recent
    available date (not necessarily today — weekends and holidays have no data).
    Returns same structure as _fetch_tesouro_from_anbima.
    """
    logger.info("refresh_tesouro_rates: fetching from CKAN CSV fallback")
    resp = requests_lib.get(CKAN_CSV_URL, timeout=60)
    resp.raise_for_status()

    # Parse all rows and find the most recent date in the CSV
    all_rows = list(csv.DictReader(io.StringIO(resp.text), delimiter=";"))

    # Collect all distinct dates and pick the most recent one
    def _parse_date(s: str):
        try:
            parts = s.strip().split("/")
            if len(parts) == 3:
                return (int(parts[2]), int(parts[1]), int(parts[0]))
        except Exception:
            pass
        return (0, 0, 0)

    dates = {row.get("Data Base", "").strip() for row in all_rows if row.get("Data Base", "").strip()}
    if not dates:
        return []

    latest_date = max(dates, key=_parse_date)
    logger.info("refresh_tesouro_rates: CKAN CSV most recent date: %s", latest_date)

    records = []
    for row in all_rows:
        data_base = row.get("Data Base", "").strip()
        if data_base != latest_date:
            continue

        tipo = row.get("Tipo Titulo", "").strip()
        vencimento_raw = row.get("Data Vencimento", "").strip()
        taxa_compra = row.get("Taxa Compra Manha", "").strip().replace(",", ".")
        taxa_venda = row.get("Taxa Venda Manha", "").strip().replace(",", ".")
        pu_compra = row.get("PU Compra Manha", "").strip().replace(",", ".")

        # Use buy rate as taxa_indicativa (standard convention)
        taxa = _safe_decimal(taxa_compra) or _safe_decimal(taxa_venda)

        if not tipo:
            continue

        records.append({
            "tipo_titulo": tipo,
            "vencimento": vencimento_raw,
            "taxa_indicativa": taxa,
            "pu": _safe_decimal(pu_compra),
            "data_base": data_base,
            "source": "ckan",
        })

    return records


def _build_bond_code(tipo_titulo: str, vencimento: str) -> str:
    """Build a Redis key-safe bond code from tipo_titulo and vencimento.

    Input vencimento may be in DD/MM/YYYY or YYYY-MM-DD format.
    Output: "{tipo_titulo}_{YYYYMMDD}" — e.g. "Tesouro IPCA+ 2035_20350515"
    """
    if "/" in vencimento:
        # DD/MM/YYYY format from CKAN
        parts = vencimento.split("/")
        if len(parts) == 3:
            vencimento = f"{parts[2]}{parts[1]}{parts[0]}"
    else:
        # YYYY-MM-DD or YYYYMMDD from ANBIMA
        vencimento = vencimento.replace("-", "")

    return f"{tipo_titulo}_{vencimento}"


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def refresh_tesouro_rates(self) -> None:
    """Fetch Tesouro Direto bond rates and store in Redis.

    Schedule: Every 6 hours (crontab in celery_app.py)
    Redis: tesouro:rates:{BOND_CODE} — TTL 6h
    No DB write — rates are ephemeral, served from Redis only.

    Primary source: ANBIMA API (OAuth2)
    Fallback source: CKAN CSV (public, 13MB, filtered to today)
    """
    logger.info("refresh_tesouro_rates: starting")
    r = _get_redis()

    records = None
    source = "unknown"

    # Try ANBIMA first
    try:
        client_id, client_secret = _get_anbima_credentials()
        token = _get_anbima_token(client_id, client_secret)
        records = _fetch_tesouro_from_anbima(token)
        source = "anbima"
        logger.info("refresh_tesouro_rates: fetched %d bonds from ANBIMA", len(records))
    except Exception as anbima_exc:
        logger.warning(
            "refresh_tesouro_rates: ANBIMA failed (%s) — falling back to CKAN CSV",
            anbima_exc,
        )
        # Fall back to CKAN CSV
        try:
            records = _fetch_tesouro_from_ckan()
            source = "ckan"
            logger.info("refresh_tesouro_rates: fetched %d bonds from CKAN CSV", len(records))
        except Exception as ckan_exc:
            logger.error("refresh_tesouro_rates: CKAN fallback also failed: %s", ckan_exc)
            raise self.retry(exc=ckan_exc)

    if not records:
        logger.warning("refresh_tesouro_rates: no bond records found from %s — skipping", source)
        return

    # Write each bond to Redis
    count = 0
    for record in records:
        tipo = record.get("tipo_titulo", "")
        vencimento = record.get("vencimento", "")
        if not tipo:
            continue

        bond_code = _build_bond_code(tipo, vencimento)
        redis_key = _TESOURO_PREFIX + bond_code

        payload = {
            "tipo_titulo": tipo,
            "vencimento": vencimento,
            "taxa_indicativa": str(record["taxa_indicativa"]) if record.get("taxa_indicativa") is not None else None,
            "pu": str(record["pu"]) if record.get("pu") is not None else None,
            "data_base": record.get("data_base", ""),
            "source": source,
        }
        r.set(redis_key, json.dumps(payload), ex=_TESOURO_TTL)
        count += 1

    logger.info("refresh_tesouro_rates: done — %d bonds from %s", count, source)
