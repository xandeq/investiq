"""Portfolio health computation service (Phase 23 — ADVI-01) + Action Inbox v1.

compute_portfolio_health():
  - Reads buy/sell/dividend/jscp transactions from tenant DB (RLS-scoped)
  - Joins with screener_snapshots (global DB) to get sector + variacao_12m_pct
  - Returns PortfolioHealth with 4 metrics + health_score (deterministic formula)
  - No AI, no Redis, no external calls — pure SQL, target <200ms

Score formula (starts at 100, deductions additive):
  biggest_sector_pct > 50%    → -20
  biggest_asset_pct   > 30%   → -25
  distinct_assets     < 5     → -15
  underperformer cost > 30%   → -20
  passive_income_ttm  == 0    → -10
  (floor: 10)

compute_inbox():
  - Aggregates 5 existing sources into ranked decision cards
  - Per-source try/except → graceful degradation (failed source listed in meta)
  - No new tables, no new Celery, no new LLM
  - Caps at 10 cards, sorted by priority desc
"""
from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.advisor.schemas import (
    InboxCard,
    InboxCardCTA,
    InboxMeta,
    InboxResponse,
    InboxSeverity,
    PortfolioHealth,
)
from app.modules.market_universe.models import ScreenerSnapshot
from app.modules.portfolio.models import Transaction

logger = logging.getLogger(__name__)

_UNDERPERFORM_THRESHOLD = Decimal("-10")   # variacao_12m_pct < -10% = underperformer
_CONCENTRATION_SECTOR = 50.0               # sector > 50% triggers biggest_risk
_CONCENTRATION_ASSET = 30.0               # single asset > 30% triggers biggest_risk
_MIN_ASSETS = 5                           # fewer than 5 distinct assets → alert


async def compute_portfolio_health(
    tenant_db: AsyncSession,
    global_db: AsyncSession,
    tenant_id: str,
) -> PortfolioHealth:
    """Compute portfolio health synchronously.

    tenant_db: RLS-scoped session (reads only this tenant's transactions)
    global_db: unscoped session (reads screener_snapshots — global table)
    """
    # ── 1. Load buy/sell transactions ──────────────────────────────────────
    tx_result = await tenant_db.execute(
        select(
            Transaction.ticker,
            Transaction.transaction_type,
            Transaction.total_value,
            Transaction.asset_class,
        ).where(
            Transaction.tenant_id == tenant_id,
            Transaction.transaction_type.in_(["buy", "sell"]),
            Transaction.deleted_at.is_(None),
        )
    )
    txs = tx_result.all()

    if not txs:
        return PortfolioHealth(
            health_score=0,
            biggest_risk=None,
            passive_income_monthly_brl=Decimal("0"),
            underperformers=[],
            data_as_of=None,
            total_assets=0,
            has_portfolio=False,
        )

    # ── 2. Net cost-basis position per ticker ──────────────────────────────
    positions: dict[str, Decimal] = {}
    for row in txs:
        delta = Decimal(str(row.total_value))
        if row.transaction_type == "sell":
            delta = -delta
        positions[row.ticker] = positions.get(row.ticker, Decimal("0")) + delta

    active = {t: v for t, v in positions.items() if v > Decimal("0")}
    if not active:
        return PortfolioHealth(
            health_score=0,
            biggest_risk=None,
            passive_income_monthly_brl=Decimal("0"),
            underperformers=[],
            data_as_of=None,
            total_assets=0,
            has_portfolio=True,
        )

    total_cost = sum(active.values())

    # ── 3. Passive income TTM (dividends + jscp, last 12 months) ──────────
    ttm_cutoff = date.today() - timedelta(days=365)
    income_result = await tenant_db.execute(
        select(func.sum(Transaction.total_value)).where(
            Transaction.tenant_id == tenant_id,
            Transaction.transaction_type.in_(["dividend", "jscp"]),
            Transaction.transaction_date >= ttm_cutoff,
            Transaction.deleted_at.is_(None),
        )
    )
    passive_ttm = income_result.scalar() or Decimal("0")
    passive_monthly = (Decimal(str(passive_ttm)) / 12).quantize(Decimal("0.01"))

    # ── 4. Fetch screener snapshots for active tickers ─────────────────────
    tickers = list(active.keys())

    # Subquery: latest snapshot_date per ticker
    latest_dates_sq = (
        select(
            ScreenerSnapshot.ticker,
            func.max(ScreenerSnapshot.snapshot_date).label("max_date"),
        )
        .where(ScreenerSnapshot.ticker.in_(tickers))
        .group_by(ScreenerSnapshot.ticker)
        .subquery()
    )

    snap_result = await global_db.execute(
        select(ScreenerSnapshot).join(
            latest_dates_sq,
            (ScreenerSnapshot.ticker == latest_dates_sq.c.ticker)
            & (ScreenerSnapshot.snapshot_date == latest_dates_sq.c.max_date),
        )
    )
    snaps = {s.ticker: s for s in snap_result.scalars().all()}
    data_as_of: datetime | None = None
    if snaps:
        latest_snap = max(snaps.values(), key=lambda s: s.snapshot_date)
        data_as_of = datetime.combine(latest_snap.snapshot_date, datetime.min.time()).replace(
            tzinfo=timezone.utc
        )

    # ── 5. Sector exposure ─────────────────────────────────────────────────
    sector_map: dict[str, Decimal] = {}
    for ticker, cost in active.items():
        snap = snaps.get(ticker)
        sector = (snap.sector or "Outros") if snap else "Outros"
        sector_map[sector] = sector_map.get(sector, Decimal("0")) + cost

    biggest_sector, biggest_sector_val = max(sector_map.items(), key=lambda x: x[1])
    biggest_sector_pct = float(biggest_sector_val / total_cost * 100)

    # ── 6. Asset concentration ─────────────────────────────────────────────
    biggest_ticker, biggest_asset_val = max(active.items(), key=lambda x: x[1])
    biggest_asset_pct = float(biggest_asset_val / total_cost * 100)

    # ── 7. Underperformers (variacao_12m_pct < -10%) ──────────────────────
    underperformer_entries: list[tuple[str, Decimal]] = []
    underperformer_cost = Decimal("0")
    for ticker, cost in active.items():
        snap = snaps.get(ticker)
        if snap and snap.variacao_12m_pct is not None:
            if snap.variacao_12m_pct < _UNDERPERFORM_THRESHOLD:
                underperformer_entries.append((ticker, snap.variacao_12m_pct))
                underperformer_cost += cost

    # Sort by worst performance, cap at 3
    underperformer_entries.sort(key=lambda x: x[1])
    underperformers = [
        f"{t} ({float(v):.1f}%)" for t, v in underperformer_entries[:3]
    ]
    underperformer_ratio = float(underperformer_cost / total_cost) if total_cost > 0 else 0.0

    # ── 8. Health score (deterministic) ───────────────────────────────────
    score = 100
    if biggest_sector_pct > _CONCENTRATION_SECTOR:
        score -= 20
    if biggest_asset_pct > _CONCENTRATION_ASSET:
        score -= 25
    if len(active) < _MIN_ASSETS:
        score -= 15
    if underperformer_ratio > 0.30:
        score -= 20
    if passive_ttm == 0:
        score -= 10
    score = max(score, 10)

    # ── 9. Biggest risk (single sentence) ─────────────────────────────────
    biggest_risk: str | None = None
    if biggest_sector_pct > _CONCENTRATION_SECTOR:
        biggest_risk = f"{biggest_sector_pct:.0f}% concentrado em {biggest_sector}"
    elif biggest_asset_pct > _CONCENTRATION_ASSET:
        biggest_risk = f"{biggest_asset_pct:.0f}% em um único ativo ({biggest_ticker})"
    elif len(active) < _MIN_ASSETS:
        biggest_risk = f"Apenas {len(active)} ativo(s) distinto(s) — baixa diversificação"

    return PortfolioHealth(
        health_score=score,
        biggest_risk=biggest_risk,
        passive_income_monthly_brl=passive_monthly,
        underperformers=underperformers,
        data_as_of=data_as_of,
        total_assets=len(active),
        has_portfolio=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Action Inbox v1 (Phase 1)
# ─────────────────────────────────────────────────────────────────────────────

_INBOX_MAX_CARDS = 10
_OPP_LOOKBACK_HOURS = 48
_INSIGHT_LOOKBACK_DAYS = 7
_WATCHLIST_LOOKBACK_HOURS = 48
_SWING_MAX_CARDS = 3

_SOURCE_WEIGHT: dict[str, float] = {
    "concentration_risk": 0.95,
    "watchlist_alert": 0.90,
    "opportunity_detected": 0.80,
    "swing_signal": 0.65,
    "underperformer": 0.60,
    "insight": 0.50,
    "low_diversification": 0.45,
    "no_passive_income": 0.30,
}
_SEVERITY_SCORE: dict[str, float] = {"alert": 1.0, "warn": 0.6, "info": 0.3}


def _stable_id(*parts: str) -> str:
    """Short stable id derived from inputs — used as React key + dedup."""
    raw = "|".join(parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _recency_score(created_at: datetime) -> float:
    now = datetime.now(tz=timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    delta = now - created_at
    if delta <= timedelta(hours=24):
        return 1.0
    if delta <= timedelta(days=7):
        return 0.6
    return 0.3


def _priority(kind: str, severity: InboxSeverity, created_at: datetime) -> float:
    sw = _SOURCE_WEIGHT.get(kind, 0.5)
    sev = _SEVERITY_SCORE.get(severity, 0.3)
    rec = _recency_score(created_at)
    score = 0.5 * sw + 0.3 * sev + 0.2 * rec
    return max(0.0, min(1.0, score))


def _make_card(
    *,
    kind: str,
    title: str,
    body: str,
    severity: InboxSeverity,
    created_at: datetime,
    ticker: str | None = None,
    cta: InboxCardCTA | None = None,
    id_parts: tuple[str, ...] = (),
) -> InboxCard:
    cid = _stable_id(kind, *id_parts) if id_parts else _stable_id(kind, title, str(created_at))
    return InboxCard(
        id=cid,
        kind=kind,  # type: ignore[arg-type]
        priority=_priority(kind, severity, created_at),
        title=title[:80],
        body=body[:200],
        ticker=ticker,
        severity=severity,
        cta=cta,
        created_at=created_at,
    )


def _health_to_cards(health: PortfolioHealth) -> list[InboxCard]:
    """Derive up to 4 cards from one PortfolioHealth snapshot."""
    if not health.has_portfolio or health.total_assets == 0:
        return []
    now = datetime.now(tz=timezone.utc)
    cards: list[InboxCard] = []
    risk = health.biggest_risk or ""

    if "concentrado em" in risk or "em um único ativo" in risk:
        cards.append(_make_card(
            kind="concentration_risk",
            title="Reduzir concentração da carteira",
            body=risk,
            severity="alert",
            created_at=now,
            cta=InboxCardCTA(label="Ver detalhes da carteira", href="/portfolio"),
            id_parts=("health", "concentration", risk),
        ))
    if "Apenas" in risk and "ativo" in risk:
        cards.append(_make_card(
            kind="low_diversification",
            title="Aumentar diversificação",
            body=risk,
            severity="warn",
            created_at=now,
            cta=InboxCardCTA(label="Explorar ações", href="/screener/acoes"),
            id_parts=("health", "diversification", risk),
        ))
    for u in health.underperformers[:3]:
        ticker = u.split(" ")[0] if u else None
        cards.append(_make_card(
            kind="underperformer",
            title=f"Reavaliar {ticker}" if ticker else "Reavaliar ativo",
            body=f"{u} — variação 12m abaixo de -10%. Considere reavaliar a tese.",
            severity="warn",
            created_at=now,
            ticker=ticker,
            cta=InboxCardCTA(label="Ver análise do ativo", href=f"/stock/{ticker}") if ticker else None,
            id_parts=("health", "underperformer", u),
        ))
    if health.passive_income_monthly_brl == Decimal("0"):
        cards.append(_make_card(
            kind="no_passive_income",
            title="Carteira sem renda passiva nos últimos 12 meses",
            body="Considere FIIs ou ações pagadoras de dividendos para gerar fluxo de caixa mensal.",
            severity="info",
            created_at=now,
            cta=InboxCardCTA(label="Ver FIIs ranqueados", href="/fii/screener"),
            id_parts=("health", "no_income"),
        ))
    return cards


async def _opps_to_cards(global_db: AsyncSession) -> list[InboxCard]:
    """Latest detected opportunities flagged is_opportunity=True (last 48h, max 5).

    `detected_opportunities` is a global table — same data feeds /opportunity-detector/radar.
    """
    from app.modules.opportunity_detector.models import DetectedOpportunity

    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=_OPP_LOOKBACK_HOURS)
    result = await global_db.execute(
        select(DetectedOpportunity)
        .where(
            DetectedOpportunity.detected_at >= cutoff,
            DetectedOpportunity.is_opportunity.is_(True),
        )
        .order_by(desc(DetectedOpportunity.detected_at))
        .limit(5)
    )
    rows = result.scalars().all()
    cards: list[InboxCard] = []
    for o in rows:
        sev: InboxSeverity = "alert" if (o.risk_level or "").lower() in ("baixo", "medio") else "warn"
        body = (o.cause_explanation or f"{o.ticker} caiu {abs(float(o.drop_pct)):.1f}% ({o.period}).")[:200]
        cards.append(_make_card(
            kind="opportunity_detected",
            title=f"Oportunidade detectada: {o.ticker}",
            body=body,
            severity=sev,
            created_at=o.detected_at,
            ticker=o.ticker,
            cta=InboxCardCTA(label="Ver oportunidades", href="/opportunity-detector"),
            id_parts=("opp", o.id),
        ))
    return cards


async def _insights_to_cards(tenant_db: AsyncSession, tenant_id: str) -> list[InboxCard]:
    """Unread insights last 7 days, max 5."""
    from app.modules.insights.models import UserInsight

    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=_INSIGHT_LOOKBACK_DAYS)
    result = await tenant_db.execute(
        select(UserInsight)
        .where(
            UserInsight.tenant_id == tenant_id,
            UserInsight.created_at >= cutoff,
            UserInsight.seen.is_(False),
        )
        .order_by(desc(UserInsight.created_at))
        .limit(5)
    )
    rows = result.scalars().all()
    cards: list[InboxCard] = []
    for ins in rows:
        # user_insights.severity uses {"alert","warning","info"} — normalize "warning" → "warn"
        raw = (ins.severity or "info").lower()
        sev: InboxSeverity = "warn" if raw == "warning" else (raw if raw in ("alert", "warn", "info") else "info")  # type: ignore[assignment]
        cards.append(_make_card(
            kind="insight",
            title=ins.title,
            body=ins.body,
            severity=sev,
            created_at=ins.created_at,
            ticker=ins.ticker,
            cta=InboxCardCTA(label="Ver todos os insights", href="/insights"),
            id_parts=("insight", ins.id),
        ))
    return cards


async def _alerts_to_cards(tenant_db: AsyncSession, tenant_id: str) -> list[InboxCard]:
    """Watchlist items whose price alert was triggered in the last 48h."""
    from app.modules.watchlist.models import WatchlistItem

    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=_WATCHLIST_LOOKBACK_HOURS)
    result = await tenant_db.execute(
        select(WatchlistItem)
        .where(
            WatchlistItem.tenant_id == tenant_id,
            WatchlistItem.alert_triggered_at.is_not(None),
            WatchlistItem.alert_triggered_at >= cutoff,
        )
        .order_by(desc(WatchlistItem.alert_triggered_at))
    )
    rows = result.scalars().all()
    cards: list[InboxCard] = []
    for w in rows:
        target = float(w.price_alert_target) if w.price_alert_target is not None else None
        body = (
            f"{w.ticker} atingiu seu alerta de preço (R$ {target:.2f})." if target is not None
            else f"{w.ticker} atingiu o alerta da watchlist."
        )
        cards.append(_make_card(
            kind="watchlist_alert",
            title=f"Alerta atingido: {w.ticker}",
            body=body,
            severity="alert",
            created_at=w.alert_triggered_at,  # type: ignore[arg-type]
            ticker=w.ticker,
            cta=InboxCardCTA(label="Abrir watchlist", href="/watchlist"),
            id_parts=("watchlist", w.id),
        ))
    return cards


async def _signals_to_cards(redis_client, db: AsyncSession, tenant_id: str) -> list[InboxCard]:
    """Top swing-trade BUY signals (portfolio + radar) — max _SWING_MAX_CARDS."""
    from app.modules.portfolio.service import PortfolioService
    from app.modules.swing_trade.service import compute_signals

    portfolio_svc = PortfolioService()
    positions = await portfolio_svc.get_positions(db, tenant_id, redis_client)
    portfolio_tickers = [p.ticker for p in positions]
    portfolio_quantities = {p.ticker: p.quantity for p in positions}

    signals = await compute_signals(
        redis_client=redis_client,
        portfolio_tickers=portfolio_tickers,
        portfolio_quantities=portfolio_quantities,
    )

    # Prefer portfolio BUYs first, then radar BUYs; cap to _SWING_MAX_CARDS overall.
    buy_items = [s for s in signals.portfolio_signals if s.signal == "buy"]
    buy_items += [s for s in signals.radar_signals if s.signal == "buy"]
    buy_items = buy_items[:_SWING_MAX_CARDS]

    now = datetime.now(tz=timezone.utc)
    cards: list[InboxCard] = []
    for s in buy_items:
        location = "(carteira)" if s.in_portfolio else "(radar)"
        body = (
            f"{s.ticker} {abs(s.discount_pct):.1f}% abaixo da máxima de 30 dias "
            f"{location}. Sinal de entrada técnico."
        )
        cards.append(_make_card(
            kind="swing_signal",
            title=f"Sinal de entrada: {s.ticker}",
            body=body,
            severity="info",
            created_at=now,
            ticker=s.ticker,
            cta=InboxCardCTA(label="Ver swing trade", href="/swing-trade"),
            id_parts=("swing", s.ticker, "portfolio" if s.in_portfolio else "radar"),
        ))
    return cards


def _rank(cards: list[InboxCard]) -> list[InboxCard]:
    """Sort cards desc by priority, then by recency. Cap at _INBOX_MAX_CARDS."""
    cards.sort(key=lambda c: (c.priority, c.created_at), reverse=True)
    return cards[:_INBOX_MAX_CARDS]


async def compute_inbox(
    *,
    tenant_db: AsyncSession,
    global_db: AsyncSession,
    tenant_id: str,
    redis_client=None,
) -> InboxResponse:
    """Aggregate 5 existing sources into a ranked InboxResponse.

    Per-source try/except: a failure in one source must not break the inbox.
    Failed sources are listed in `meta.sources_failed` and the response is still 200.

    `redis_client` may be None in environments where swing signals can't run
    (e.g., minimal smoke tests). When None, swing_signals source is silently skipped
    (recorded as failed for transparency).
    """
    sources_ok: list[str] = []
    sources_failed: list[str] = []
    cards: list[InboxCard] = []

    # 1. Health-derived cards
    try:
        health = await compute_portfolio_health(
            tenant_db=tenant_db, global_db=global_db, tenant_id=tenant_id,
        )
        cards.extend(_health_to_cards(health))
        sources_ok.append("health")
    except Exception as exc:
        logger.warning("inbox.health_failed tenant_id=%s err=%s", tenant_id, exc)
        sources_failed.append("health")

    # 2. Detected opportunities (global)
    try:
        cards.extend(await _opps_to_cards(global_db))
        sources_ok.append("opportunity_detector")
    except Exception as exc:
        logger.warning("inbox.opps_failed tenant_id=%s err=%s", tenant_id, exc)
        sources_failed.append("opportunity_detector")

    # 3. Unread insights (tenant)
    try:
        cards.extend(await _insights_to_cards(tenant_db, tenant_id))
        sources_ok.append("insights")
    except Exception as exc:
        logger.warning("inbox.insights_failed tenant_id=%s err=%s", tenant_id, exc)
        sources_failed.append("insights")

    # 4. Watchlist alerts triggered (tenant)
    try:
        cards.extend(await _alerts_to_cards(tenant_db, tenant_id))
        sources_ok.append("watchlist_alerts")
    except Exception as exc:
        logger.warning("inbox.watchlist_failed tenant_id=%s err=%s", tenant_id, exc)
        sources_failed.append("watchlist_alerts")

    # 5. Swing signals (Redis-only — degrades silently if redis missing/error)
    if redis_client is None:
        sources_failed.append("swing_signals")
    else:
        try:
            cards.extend(await _signals_to_cards(redis_client, tenant_db, tenant_id))
            sources_ok.append("swing_signals")
        except Exception as exc:
            logger.warning("inbox.swing_failed tenant_id=%s err=%s", tenant_id, exc)
            sources_failed.append("swing_signals")

    return InboxResponse(
        generated_at=datetime.now(tz=timezone.utc),
        cards=_rank(cards),
        meta=InboxMeta(sources_ok=sources_ok, sources_failed=sources_failed),
    )
