"""Weekly portfolio digest — Celery task.

Runs every Monday at 08:00 BRT.
Sends a portfolio performance email to every verified user
who has at least one open position.

Design:
- Uses sync psycopg2 DB (Celery rule — never asyncpg in tasks)
- Reads portfolio value and 7-day change from portfolio_daily_value table
- Reads current positions from transactions (CMP aggregation)
- Reads current prices from Redis (batch MGET)
- Sends HTML email via core.email.send_email (Resend → Brevo fallback)

Non-fatal: errors per-user are logged and skipped — one bad email
never aborts the rest of the digest run.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date, timedelta
from decimal import Decimal

import redis as sync_redis
from celery import shared_task
from sqlalchemy import text

from app.core.db_sync import get_superuser_sync_db_session
from app.core.email import send_email

logger = logging.getLogger(__name__)

_APP_URL = "https://investiq.com.br"


def _get_redis() -> sync_redis.Redis:
    url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    return sync_redis.Redis.from_url(url, decode_responses=True)


def _parse_price(raw: str | None) -> Decimal | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        price = data.get("price") or data.get("regularMarketPrice")
        return Decimal(str(price)) if price is not None else None
    except Exception:
        return None


def _parse_change_pct(raw: str | None) -> float | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return float(data.get("change_percent") or data.get("regularMarketChangePercent") or 0)
    except Exception:
        return None


def _get_verified_users_with_portfolio(session) -> list[dict]:
    """Return verified users that have at least one open position."""
    rows = session.execute(text("""
        SELECT DISTINCT u.id, u.email, u.tenant_id
        FROM users u
        INNER JOIN transactions t ON t.tenant_id = u.tenant_id
        WHERE u.is_verified = TRUE
          AND t.transaction_type IN ('buy', 'sell')
          AND t.deleted_at IS NULL
        ORDER BY u.email
    """)).fetchall()
    return [{"id": r[0], "email": r[1], "tenant_id": r[2]} for r in rows]


def _get_portfolio_timeseries(session, tenant_id: str, days: int = 8) -> list[dict]:
    """Return last N days of EOD snapshots for a tenant."""
    since = date.today() - timedelta(days=days)
    rows = session.execute(text("""
        SELECT snapshot_date, total_value, total_invested
        FROM portfolio_daily_value
        WHERE tenant_id = :tid AND snapshot_date >= :since
        ORDER BY snapshot_date ASC
    """), {"tid": tenant_id, "since": since}).fetchall()
    return [{"date": r[0], "total_value": Decimal(str(r[1])), "total_invested": Decimal(str(r[2]))} for r in rows]


def _get_positions(session, tenant_id: str) -> list[dict]:
    """Return open positions with CMP."""
    rows = session.execute(text("""
        SELECT
            ticker,
            SUM(CASE WHEN transaction_type = 'buy' THEN quantity ELSE -quantity END) AS net_qty,
            SUM(CASE WHEN transaction_type = 'buy' THEN total_value ELSE 0 END) AS total_bought
        FROM transactions
        WHERE tenant_id = :tid
          AND transaction_type IN ('buy', 'sell')
          AND deleted_at IS NULL
        GROUP BY ticker
        HAVING SUM(CASE WHEN transaction_type = 'buy' THEN quantity ELSE -quantity END) > 0.0001
        ORDER BY ticker
    """), {"tid": tenant_id}).fetchall()

    positions = []
    for r in rows:
        ticker, net_qty, total_bought = r
        net_qty = Decimal(str(net_qty or 0))
        total_bought = Decimal(str(total_bought or 0))
        if net_qty <= 0:
            continue
        cmp = total_bought / net_qty
        positions.append({"ticker": str(ticker).upper(), "quantity": net_qty, "cmp": cmp})
    return positions


def _fmt_brl(value: float) -> str:
    """Format as R$ with Brazilian locale (server-side, no JS)."""
    sign = "" if value >= 0 else "−"
    abs_val = abs(value)
    return f"R$\u00a0{sign}{abs_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_pct(value: float, plus: bool = True) -> str:
    sign = "+" if value >= 0 and plus else ""
    return f"{sign}{value:.2f}%"


def _color(value: float) -> str:
    return "#059669" if value >= 0 else "#dc2626"


def _build_html(
    user_email: str,
    net_worth: float,
    total_invested: float,
    week_change: float | None,
    week_change_pct: float | None,
    positions: list[dict],
    top_movers: list[dict],
    app_url: str,
) -> str:
    total_return = net_worth - total_invested
    total_return_pct = (total_return / total_invested * 100) if total_invested > 0 else 0

    # Week change block
    if week_change is not None and week_change_pct is not None:
        week_html = f"""
        <tr>
          <td style="padding:16px 32px 0;">
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;">
              <tr>
                <td style="padding:16px 20px;">
                  <p style="margin:0;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;color:#94a3b8;">
                    Variação na semana
                  </p>
                  <p style="margin:6px 0 0;font-size:22px;font-weight:700;color:{_color(week_change)};font-variant-numeric:tabular-nums;">
                    {_fmt_brl(week_change)}
                    <span style="font-size:14px;font-weight:600;margin-left:6px;">
                      {_fmt_pct(week_change_pct)}
                    </span>
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>"""
    else:
        week_html = ""

    # Top movers block
    if top_movers:
        mover_rows = ""
        for m in top_movers[:5]:
            chg = m.get("change_pct", 0) or 0
            mover_rows += f"""
            <tr>
              <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;">
                <span style="font-family:monospace;font-weight:700;font-size:13px;color:#1e293b;">{m['ticker']}</span>
              </td>
              <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;text-align:right;">
                <span style="font-weight:600;font-size:13px;color:{_color(chg)};">
                  {_fmt_pct(chg)}
                </span>
              </td>
            </tr>"""
        movers_html = f"""
        <tr>
          <td style="padding:24px 32px 0;">
            <p style="margin:0 0 12px;font-size:13px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;">
              Maiores variações hoje
            </p>
            <table width="100%" cellpadding="0" cellspacing="0">
              {mover_rows}
            </table>
          </td>
        </tr>"""
    else:
        movers_html = ""

    # Position count
    pos_count = len(positions)
    pos_word = "ativo" if pos_count == 1 else "ativos"

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Resumo semanal — InvestIQ</title>
</head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 16px;">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:16px;border:1px solid #e2e8f0;overflow:hidden;max-width:520px;">

        <!-- Header -->
        <tr>
          <td style="background:#0f172a;padding:24px 32px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>
                  <p style="margin:0;color:#fff;font-size:18px;font-weight:800;letter-spacing:-0.5px;">
                    <span style="background:#3b82f6;color:#fff;border-radius:6px;padding:2px 8px;font-size:13px;font-weight:700;margin-right:8px;">IQ</span>
                    InvestIQ
                  </p>
                  <p style="margin:4px 0 0;color:#94a3b8;font-size:12px;">Resumo semanal da sua carteira</p>
                </td>
                <td style="text-align:right;">
                  <p style="margin:0;color:#64748b;font-size:11px;">{date.today().strftime('%d/%m/%Y')}</p>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Net worth -->
        <tr>
          <td style="padding:28px 32px 0;">
            <p style="margin:0;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;color:#94a3b8;font-weight:600;">
              Patrimônio total
            </p>
            <p style="margin:8px 0 4px;font-size:36px;font-weight:800;color:#0f172a;letter-spacing:-1px;font-variant-numeric:tabular-nums;">
              {_fmt_brl(net_worth)}
            </p>
            <p style="margin:0;font-size:13px;color:{_color(total_return)};">
              {_fmt_brl(total_return)} total ({_fmt_pct(total_return_pct)}) · {pos_count} {pos_word}
            </p>
          </td>
        </tr>

        {week_html}

        {movers_html}

        <!-- CTA -->
        <tr>
          <td style="padding:28px 32px;">
            <a href="{app_url}/dashboard"
               style="display:block;text-align:center;padding:14px 28px;background:#3b82f6;color:#fff;
                      border-radius:10px;text-decoration:none;font-weight:700;font-size:15px;">
              Ver carteira completa →
            </a>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:20px 32px;border-top:1px solid #f1f5f9;background:#f8fafc;">
            <p style="margin:0;font-size:11px;color:#94a3b8;line-height:1.6;">
              Você recebeu este resumo porque tem uma conta no InvestIQ ({user_email}).<br>
              Para cancelar, acesse <a href="{app_url}/profile" style="color:#64748b;">Configurações de Perfil</a>.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


@shared_task(name="app.modules.dashboard.digest_tasks.send_weekly_digest")
def send_weekly_digest() -> None:
    """Send weekly portfolio digest email to all verified users with open positions.

    Runs every Monday at 08:00 BRT via Celery Beat.
    Non-fatal: errors per-user are caught and logged individually.
    """
    try:
        from app.core.config import settings
        app_url = settings.APP_URL or _APP_URL
    except Exception:
        app_url = _APP_URL

    r = _get_redis()

    with get_superuser_sync_db_session() as session:
        users = _get_verified_users_with_portfolio(session)

    if not users:
        logger.info("send_weekly_digest: no eligible users")
        return

    logger.info("send_weekly_digest: sending digest to %d users", len(users))

    sent = 0
    errors = 0

    for user in users:
        try:
            _send_digest_for_user(user, r, app_url)
            sent += 1
        except Exception as exc:
            logger.error(
                "send_weekly_digest: failed for user %s: %s",
                user["email"], exc, exc_info=True,
            )
            errors += 1

    logger.info("send_weekly_digest: done — sent=%d errors=%d", sent, errors)


def _send_digest_for_user(user: dict, r: sync_redis.Redis, app_url: str) -> None:
    tenant_id = user["tenant_id"]
    email = user["email"]

    with get_superuser_sync_db_session() as session:
        positions = _get_positions(session, tenant_id)
        timeseries = _get_portfolio_timeseries(session, tenant_id, days=8)

    if not positions:
        return  # user has no open positions — skip

    # Batch-read current prices and daily changes
    tickers = [p["ticker"] for p in positions]
    keys = [f"market:quote:{t}" for t in tickers]
    raw_values = r.mget(keys)

    price_map: dict[str, Decimal | None] = {}
    change_pct_map: dict[str, float | None] = {}
    for ticker, raw in zip(tickers, raw_values):
        price_map[ticker] = _parse_price(raw)
        change_pct_map[ticker] = _parse_change_pct(raw)

    # Compute net worth
    net_worth = Decimal("0")
    total_invested = Decimal("0")
    for p in positions:
        ticker = p["ticker"]
        qty = p["quantity"]
        cmp = p["cmp"]
        price = price_map.get(ticker) or cmp
        net_worth += price * qty
        total_invested += cmp * qty

    if net_worth <= 0:
        return  # nothing to report

    # Weekly change from timeseries (compare latest vs 7 days ago)
    week_change: float | None = None
    week_change_pct: float | None = None
    if len(timeseries) >= 2:
        latest_val = float(timeseries[-1]["total_value"])
        week_ago_val = float(timeseries[0]["total_value"])
        if week_ago_val > 0:
            week_change = latest_val - week_ago_val
            week_change_pct = week_change / week_ago_val * 100

    # Top movers by daily change
    top_movers = [
        {"ticker": t, "change_pct": change_pct_map.get(t) or 0}
        for t in tickers
        if change_pct_map.get(t) is not None
    ]
    top_movers.sort(key=lambda x: abs(x["change_pct"]), reverse=True)

    html = _build_html(
        user_email=email,
        net_worth=float(net_worth),
        total_invested=float(total_invested),
        week_change=week_change,
        week_change_pct=week_change_pct,
        positions=positions,
        top_movers=top_movers,
        app_url=app_url,
    )

    send_email(
        to=email,
        subject=f"InvestIQ — Resumo semanal: {_fmt_brl(float(net_worth))}",
        html=html,
    )
    logger.info("send_weekly_digest: sent to %s (net_worth=%.2f)", email, float(net_worth))
