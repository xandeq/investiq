"""Tests for the check_price_alerts Celery task (Phase 6 + Phase 46).

Coverage:
  ALERT-01: Task fires alert when price is exactly at target
  ALERT-02: Task fires alert when price is within 2% tolerance (below target)
  ALERT-03: Task fires alert when price is within 2% tolerance (above target)
  ALERT-04: Task does NOT fire when price is outside tolerance band
  ALERT-05: Dedup — no double alert within 23h (Redis dedup key)
  ALERT-06: Task skips item when no Redis quote available
  ALERT-07: Task saves UserInsight record on alert
  ALERT-08: Email contains ticker, target, and current price
  ALERT-09: No items with price_alert_target → task is a no-op
  ALERT-10: check-price-alerts is in Celery beat schedule
  ALERT-11: Task handles invalid/negative target gracefully
  ALERT-12: Dedup key is set with correct TTL after first alert
  ALERT-13: Per-user Telegram sent when user has telegram_chat_id
  ALERT-14: No Telegram sent when user has no telegram_chat_id
"""
from __future__ import annotations

import json
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch, call

import fakeredis
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_redis_with_quote(ticker: str, price: float) -> fakeredis.FakeRedis:
    r = fakeredis.FakeRedis(decode_responses=True)
    r.set(f"market:quote:{ticker.upper()}", json.dumps({"regularMarketPrice": price}), ex=1200)
    return r


# ---------------------------------------------------------------------------
# ALERT-01: Exact match fires alert
# ---------------------------------------------------------------------------

def test_alert_fires_on_exact_price_match():
    tenant_id = str(uuid.uuid4())
    r = _make_redis_with_quote("PETR4", 38.00)

    items = [{"tenant_id": tenant_id, "ticker": "PETR4", "target": Decimal("38.00")}]
    emails_sent = []

    with patch("app.modules.watchlist.tasks._get_watchlist_items_with_alerts", return_value=items), \
         patch("app.modules.watchlist.tasks._get_user_contact", return_value=("user@example.com", None)), \
         patch("app.modules.watchlist.tasks._send_alert_email", side_effect=lambda *a: emails_sent.append(a)), \
         patch("app.modules.watchlist.tasks._save_alert_insight"), \
         patch("redis.Redis.from_url", return_value=r):

        from app.modules.watchlist.tasks import check_price_alerts
        check_price_alerts.apply()

    assert len(emails_sent) == 1
    _, ticker, target, price = emails_sent[0]
    assert ticker == "PETR4"
    assert target == Decimal("38.00")
    assert abs(price - Decimal("38.00")) < Decimal("0.01")


# ---------------------------------------------------------------------------
# ALERT-02: Within 2% tolerance (price below target)
# ---------------------------------------------------------------------------

def test_alert_fires_when_price_slightly_below_target():
    tenant_id = str(uuid.uuid4())
    # 38.00 target, 37.30 price → diff = 0.70/38 = 1.84% < 2%
    r = _make_redis_with_quote("VALE3", 37.30)

    items = [{"tenant_id": tenant_id, "ticker": "VALE3", "target": Decimal("38.00")}]
    emails_sent = []

    with patch("app.modules.watchlist.tasks._get_watchlist_items_with_alerts", return_value=items), \
         patch("app.modules.watchlist.tasks._get_user_contact", return_value=("user@example.com", None)), \
         patch("app.modules.watchlist.tasks._send_alert_email", side_effect=lambda *a: emails_sent.append(a)), \
         patch("app.modules.watchlist.tasks._save_alert_insight"), \
         patch("redis.Redis.from_url", return_value=r):

        from app.modules.watchlist.tasks import check_price_alerts
        check_price_alerts.apply()

    assert len(emails_sent) == 1


# ---------------------------------------------------------------------------
# ALERT-03: Within 2% tolerance (price above target)
# ---------------------------------------------------------------------------

def test_alert_fires_when_price_slightly_above_target():
    tenant_id = str(uuid.uuid4())
    # 38.00 target, 38.70 price → diff = 0.70/38 = 1.84% < 2%
    r = _make_redis_with_quote("WEGE3", 38.70)

    items = [{"tenant_id": tenant_id, "ticker": "WEGE3", "target": Decimal("38.00")}]
    emails_sent = []

    with patch("app.modules.watchlist.tasks._get_watchlist_items_with_alerts", return_value=items), \
         patch("app.modules.watchlist.tasks._get_user_contact", return_value=("user@example.com", None)), \
         patch("app.modules.watchlist.tasks._send_alert_email", side_effect=lambda *a: emails_sent.append(a)), \
         patch("app.modules.watchlist.tasks._save_alert_insight"), \
         patch("redis.Redis.from_url", return_value=r):

        from app.modules.watchlist.tasks import check_price_alerts
        check_price_alerts.apply()

    assert len(emails_sent) == 1


# ---------------------------------------------------------------------------
# ALERT-04: Outside tolerance band → no alert
# ---------------------------------------------------------------------------

def test_no_alert_when_price_outside_tolerance():
    tenant_id = str(uuid.uuid4())
    # 38.00 target, 35.00 price → diff = 3.00/38 = 7.9% > 2%
    r = _make_redis_with_quote("ABEV3", 35.00)

    items = [{"tenant_id": tenant_id, "ticker": "ABEV3", "target": Decimal("38.00")}]
    emails_sent = []

    with patch("app.modules.watchlist.tasks._get_watchlist_items_with_alerts", return_value=items), \
         patch("app.modules.watchlist.tasks._get_user_contact", return_value=("user@example.com", None)), \
         patch("app.modules.watchlist.tasks._send_alert_email", side_effect=lambda *a: emails_sent.append(a)), \
         patch("app.modules.watchlist.tasks._save_alert_insight"), \
         patch("redis.Redis.from_url", return_value=r):

        from app.modules.watchlist.tasks import check_price_alerts
        check_price_alerts.apply()

    assert len(emails_sent) == 0


# ---------------------------------------------------------------------------
# ALERT-05: Dedup — second run within 23h does not resend
# ---------------------------------------------------------------------------

def test_no_duplicate_alert_within_dedup_ttl():
    tenant_id = str(uuid.uuid4())
    r = _make_redis_with_quote("ITUB4", 25.00)
    # Pre-set the dedup key to simulate "already alerted today"
    r.set(f"price_alert:sent:{tenant_id}:ITUB4", "1", ex=82800)

    items = [{"tenant_id": tenant_id, "ticker": "ITUB4", "target": Decimal("25.00")}]
    emails_sent = []

    with patch("app.modules.watchlist.tasks._get_watchlist_items_with_alerts", return_value=items), \
         patch("app.modules.watchlist.tasks._get_user_contact", return_value=("user@example.com", None)), \
         patch("app.modules.watchlist.tasks._send_alert_email", side_effect=lambda *a: emails_sent.append(a)), \
         patch("app.modules.watchlist.tasks._save_alert_insight"), \
         patch("redis.Redis.from_url", return_value=r):

        from app.modules.watchlist.tasks import check_price_alerts
        check_price_alerts.apply()

    assert len(emails_sent) == 0, "Should not resend alert within dedup TTL"


# ---------------------------------------------------------------------------
# ALERT-06: No quote in Redis → skip
# ---------------------------------------------------------------------------

def test_no_alert_when_quote_not_in_redis():
    tenant_id = str(uuid.uuid4())
    r = fakeredis.FakeRedis(decode_responses=True)  # Empty Redis — no quote

    items = [{"tenant_id": tenant_id, "ticker": "BBDC4", "target": Decimal("20.00")}]
    emails_sent = []

    with patch("app.modules.watchlist.tasks._get_watchlist_items_with_alerts", return_value=items), \
         patch("app.modules.watchlist.tasks._get_user_contact", return_value=("user@example.com", None)), \
         patch("app.modules.watchlist.tasks._send_alert_email", side_effect=lambda *a: emails_sent.append(a)), \
         patch("app.modules.watchlist.tasks._save_alert_insight"), \
         patch("redis.Redis.from_url", return_value=r):

        from app.modules.watchlist.tasks import check_price_alerts
        check_price_alerts.apply()

    assert len(emails_sent) == 0


# ---------------------------------------------------------------------------
# ALERT-07: UserInsight saved on alert
# ---------------------------------------------------------------------------

def test_insight_saved_on_alert():
    tenant_id = str(uuid.uuid4())
    r = _make_redis_with_quote("PETR4", 38.00)

    items = [{"tenant_id": tenant_id, "ticker": "PETR4", "target": Decimal("38.00")}]
    insights_saved = []

    with patch("app.modules.watchlist.tasks._get_watchlist_items_with_alerts", return_value=items), \
         patch("app.modules.watchlist.tasks._get_user_contact", return_value=("user@example.com", None)), \
         patch("app.modules.watchlist.tasks._send_alert_email"), \
         patch("app.modules.watchlist.tasks._save_alert_insight", side_effect=lambda *a: insights_saved.append(a)), \
         patch("redis.Redis.from_url", return_value=r):

        from app.modules.watchlist.tasks import check_price_alerts
        check_price_alerts.apply()

    assert len(insights_saved) == 1
    saved_tenant, saved_ticker = insights_saved[0][0], insights_saved[0][1]
    assert saved_tenant == tenant_id
    assert saved_ticker == "PETR4"


# ---------------------------------------------------------------------------
# ALERT-08: Email content includes ticker, target, price
# ---------------------------------------------------------------------------

def test_email_content_contains_key_info():
    from app.modules.watchlist.tasks import _send_alert_email
    from unittest.mock import patch

    sent = []

    with patch("app.core.email.send_email", side_effect=lambda to, subject, html: sent.append({"to": to, "subject": subject, "html": html})):
        _send_alert_email("user@example.com", "PETR4", Decimal("38.00"), Decimal("38.10"))

    assert len(sent) == 1
    msg = sent[0]
    assert msg["to"] == "user@example.com"
    assert "PETR4" in msg["subject"]
    assert "38." in msg["subject"]
    assert "PETR4" in msg["html"]
    assert "38.00" in msg["html"]


# ---------------------------------------------------------------------------
# ALERT-09: No items with alert target → no-op
# ---------------------------------------------------------------------------

def test_no_op_when_no_items_with_target():
    r = fakeredis.FakeRedis(decode_responses=True)

    with patch("app.modules.watchlist.tasks._get_watchlist_items_with_alerts", return_value=[]), \
         patch("app.modules.watchlist.tasks._send_alert_email") as mock_send, \
         patch("redis.Redis.from_url", return_value=r):

        from app.modules.watchlist.tasks import check_price_alerts
        check_price_alerts.apply()

    mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# ALERT-10: check-price-alerts in beat schedule
# ---------------------------------------------------------------------------

def test_check_price_alerts_in_beat_schedule():
    from app.celery_app import celery_app
    assert "check-price-alerts" in celery_app.conf.beat_schedule
    entry = celery_app.conf.beat_schedule["check-price-alerts"]
    assert entry["task"] == "app.modules.watchlist.tasks.check_price_alerts"


# ---------------------------------------------------------------------------
# ALERT-11: Zero/negative target is skipped gracefully
# ---------------------------------------------------------------------------

def test_zero_target_is_skipped():
    tenant_id = str(uuid.uuid4())
    r = _make_redis_with_quote("BOVA11", 115.00)

    items = [{"tenant_id": tenant_id, "ticker": "BOVA11", "target": Decimal("0")}]
    emails_sent = []

    with patch("app.modules.watchlist.tasks._get_watchlist_items_with_alerts", return_value=items), \
         patch("app.modules.watchlist.tasks._get_user_contact", return_value=("user@example.com", None)), \
         patch("app.modules.watchlist.tasks._send_alert_email", side_effect=lambda *a: emails_sent.append(a)), \
         patch("app.modules.watchlist.tasks._save_alert_insight"), \
         patch("redis.Redis.from_url", return_value=r):

        from app.modules.watchlist.tasks import check_price_alerts
        check_price_alerts.apply()

    assert len(emails_sent) == 0, "Zero target must not trigger alert"


# ---------------------------------------------------------------------------
# ALERT-12: Dedup key is set with correct TTL after first alert
# ---------------------------------------------------------------------------

def test_dedup_key_set_after_alert():
    tenant_id = str(uuid.uuid4())
    r = _make_redis_with_quote("WEGE3", 50.00)

    items = [{"tenant_id": tenant_id, "ticker": "WEGE3", "target": Decimal("50.00")}]

    with patch("app.modules.watchlist.tasks._get_watchlist_items_with_alerts", return_value=items), \
         patch("app.modules.watchlist.tasks._get_user_contact", return_value=("user@example.com", None)), \
         patch("app.modules.watchlist.tasks._send_alert_email"), \
         patch("app.modules.watchlist.tasks._save_alert_insight"), \
         patch("redis.Redis.from_url", return_value=r):

        from app.modules.watchlist.tasks import check_price_alerts
        check_price_alerts.apply()

    dedup_key = f"price_alert:sent:{tenant_id}:WEGE3"
    assert r.exists(dedup_key), "Dedup key must be set after first alert"
    ttl = r.ttl(dedup_key)
    # TTL should be close to 23h (82800 seconds)
    assert 82700 <= ttl <= 82800, f"Expected TTL ~82800, got {ttl}"


# ---------------------------------------------------------------------------
# ALERT-13: Per-user Telegram sent when telegram_chat_id is set (Phase 46)
# ---------------------------------------------------------------------------

def test_telegram_sent_to_user_chat_id_when_set():
    tenant_id = str(uuid.uuid4())
    r = _make_redis_with_quote("PETR4", 38.00)
    items = [{"tenant_id": tenant_id, "ticker": "PETR4", "target": Decimal("38.00")}]

    tg_calls = []

    with patch("app.modules.watchlist.tasks._get_watchlist_items_with_alerts", return_value=items), \
         patch("app.modules.watchlist.tasks._get_user_contact", return_value=("user@example.com", "999888777")), \
         patch("app.modules.watchlist.tasks._send_alert_email"), \
         patch("app.modules.watchlist.tasks._save_alert_insight"), \
         patch("app.modules.watchlist.tasks.send_telegram_notification",
               side_effect=lambda chat_id, msg: tg_calls.append((chat_id, msg)) or True), \
         patch("redis.Redis.from_url", return_value=r):

        from app.modules.watchlist.tasks import check_price_alerts
        check_price_alerts.apply()

    assert len(tg_calls) == 1, "Telegram must be sent exactly once"
    chat_id, msg = tg_calls[0]
    assert chat_id == "999888777", "Must send to the user's own chat_id, not admin"
    assert "PETR4" in msg
    assert "38.00" in msg


# ---------------------------------------------------------------------------
# ALERT-14: No Telegram sent when user has no telegram_chat_id (Phase 46)
# ---------------------------------------------------------------------------

def test_no_telegram_when_user_has_no_chat_id():
    tenant_id = str(uuid.uuid4())
    r = _make_redis_with_quote("VALE3", 70.00)
    items = [{"tenant_id": tenant_id, "ticker": "VALE3", "target": Decimal("70.00")}]

    with patch("app.modules.watchlist.tasks._get_watchlist_items_with_alerts", return_value=items), \
         patch("app.modules.watchlist.tasks._get_user_contact", return_value=("user@example.com", None)), \
         patch("app.modules.watchlist.tasks._send_alert_email"), \
         patch("app.modules.watchlist.tasks._save_alert_insight"), \
         patch("app.modules.watchlist.tasks.send_telegram_notification") as mock_tg, \
         patch("redis.Redis.from_url", return_value=r):

        from app.modules.watchlist.tasks import check_price_alerts
        check_price_alerts.apply()

    mock_tg.assert_not_called()
