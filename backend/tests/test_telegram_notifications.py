"""Tests for Phase 39 Telegram notifications (TG-01, TG-02, TG-03)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select, update

from app.modules.auth.models import User
from tests.conftest import register_verify_and_login

# ---------------------------------------------------------------------------
# Sample signal dict used across tests
# ---------------------------------------------------------------------------
_SAMPLE_SIGNAL = {
    "ticker": "PETR4",
    "grade": "A+",
    "score": 0.9,
    "passed_gates": 5,
    "total_gates": 5,
    "setup": {
        "pattern": "bull_flag",
        "direction": "long",
        "entry": 38.50,
        "stop": 36.00,
        "target_1": 43.00,
        "target_2": 46.00,
        "rr": 2.8,
        "grade": "A+",
    },
    "confluences": ["multi_tf_aligned", "above_ema200"],
    "indicators": {},
}


# =============================================================================
# TG-01: GET /profile/telegram
# =============================================================================

@pytest.mark.asyncio
async def test_get_telegram_returns_null_when_not_set(client, db_session, email_stub):
    """GET /profile/telegram returns {"telegram_chat_id": null} when not set."""
    await register_verify_and_login(client, email_stub, email="tg_get_null@test.com")
    resp = await client.get("/profile/telegram")
    assert resp.status_code == 200
    assert resp.json() == {"telegram_chat_id": None}


# =============================================================================
# TG-01: PATCH /profile/telegram - pro user can save
# =============================================================================

@pytest.mark.asyncio
async def test_patch_telegram_saves_chat_id_for_pro_user(client, db_session, email_stub):
    """Pro user PATCH /profile/telegram saves chat_id and returns it."""
    user_id = await register_verify_and_login(client, email_stub, email="tg_pro_save@test.com")

    # Upgrade to pro
    await db_session.execute(
        update(User).where(User.id == user_id).values(plan="pro")
    )
    await db_session.flush()

    resp = await client.patch("/profile/telegram", json={"telegram_chat_id": "123456789"})
    assert resp.status_code == 200
    assert resp.json()["telegram_chat_id"] == "123456789"

    # Verify in DB
    result = await db_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    assert user.telegram_chat_id == "123456789"


# =============================================================================
# TG-03: PATCH /profile/telegram - disconnect with null
# =============================================================================

@pytest.mark.asyncio
async def test_patch_telegram_disconnect_with_null(client, db_session, email_stub):
    """Pro user with chat_id set can clear it by sending null (TG-03 disconnect)."""
    user_id = await register_verify_and_login(client, email_stub, email="tg_disconnect@test.com")

    # Upgrade to pro and pre-set chat_id
    await db_session.execute(
        update(User).where(User.id == user_id).values(plan="pro", telegram_chat_id="999111999")
    )
    await db_session.flush()

    resp = await client.patch("/profile/telegram", json={"telegram_chat_id": None})
    assert resp.status_code == 200
    assert resp.json()["telegram_chat_id"] is None

    # Verify DB column is NULL
    result = await db_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    assert user.telegram_chat_id is None


# =============================================================================
# TG-01 PRO GATE: free user blocked
# =============================================================================

@pytest.mark.asyncio
async def test_patch_telegram_free_user_returns_403(client, db_session, email_stub):
    """Free user (no trial) PATCH /profile/telegram returns 403 REQUIRES_PRO."""
    user_id = await register_verify_and_login(client, email_stub, email="tg_free_gate@test.com")

    # Ensure free plan, no trial
    await db_session.execute(
        update(User).where(User.id == user_id).values(plan="free", trial_ends_at=None)
    )
    await db_session.flush()

    resp = await client.patch("/profile/telegram", json={"telegram_chat_id": "123456789"})
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["code"] == "REQUIRES_PRO"
    assert detail["upgrade_url"] == "/planos"


# =============================================================================
# TG-03 DISCONNECT: free user can always disconnect
# =============================================================================

@pytest.mark.asyncio
async def test_patch_telegram_free_user_can_disconnect(client, db_session, email_stub):
    """Free user with existing chat_id (e.g. after plan downgrade) can still clear it."""
    user_id = await register_verify_and_login(client, email_stub, email="tg_free_disconnect@test.com")

    # Free user with chat_id pre-set (simulating post-downgrade state)
    await db_session.execute(
        update(User).where(User.id == user_id).values(
            plan="free", trial_ends_at=None, telegram_chat_id="555444333"
        )
    )
    await db_session.flush()

    resp = await client.patch("/profile/telegram", json={"telegram_chat_id": None})
    assert resp.status_code == 200
    assert resp.json()["telegram_chat_id"] is None

    # Verify DB column is NULL
    result = await db_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    assert user.telegram_chat_id is None


# =============================================================================
# TG-01 TRIAL: trial users get pro access
# =============================================================================

@pytest.mark.asyncio
async def test_patch_telegram_trial_user_allowed(client, db_session, email_stub):
    """Free user with active trial can set telegram_chat_id."""
    user_id = await register_verify_and_login(client, email_stub, email="tg_trial@test.com")

    # Set active trial (plan=free but trial_ends_at in future)
    future = datetime.now(tz=timezone.utc) + timedelta(days=7)
    await db_session.execute(
        update(User).where(User.id == user_id).values(plan="free", trial_ends_at=future)
    )
    await db_session.flush()

    resp = await client.patch("/profile/telegram", json={"telegram_chat_id": "987654321"})
    assert resp.status_code == 200

    result = await db_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    assert user.telegram_chat_id == "987654321"


# =============================================================================
# TG-01 VALIDATION: invalid chat_id format returns 422
# =============================================================================

@pytest.mark.asyncio
async def test_patch_telegram_rejects_invalid_format(client, db_session, email_stub):
    """PATCH /profile/telegram with non-numeric chat_id returns 422."""
    user_id = await register_verify_and_login(client, email_stub, email="tg_invalid@test.com")

    # Upgrade to pro so the pro gate doesn't block us first
    await db_session.execute(
        update(User).where(User.id == user_id).values(plan="pro")
    )
    await db_session.flush()

    resp = await client.patch("/profile/telegram", json={"telegram_chat_id": "abc"})
    assert resp.status_code == 422


# =============================================================================
# TG-02: notify_users_for_signal fan-out
# =============================================================================

def test_notify_users_for_signal_sends_to_pro_with_chat_id():
    """notify_users_for_signal calls send_telegram_notification once for pro user with chat_id.

    Users: (a) pro+chat_id="111" → gets notified; (b) pro+chat_id=None → skipped;
           (c) free+chat_id="222" → skipped.
    DB query is patched at the source module (local import inside function).
    """
    from app.modules.telegram_bot.tasks import notify_users_for_signal

    # Mock DB query to return only user (a) — only pro user with chat_id
    fake_rows = [("111",)]  # Only the eligible user

    mock_session = MagicMock()
    mock_session.execute.return_value.fetchall.return_value = fake_rows

    with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test_token"}):
        # Patch at the source module where it's defined (local import uses the module-level name)
        with patch("app.core.db_sync.get_superuser_sync_db_session") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            with patch("app.modules.telegram_bot.tasks.send_telegram_notification") as mock_send:
                mock_send.return_value = True
                result = notify_users_for_signal([_SAMPLE_SIGNAL])

    mock_send.assert_called_once()
    call_args = mock_send.call_args
    assert call_args[0][0] == "111"  # chat_id
    assert result["status"] == "ok"
    assert result["notified"] == 1


def test_notify_users_for_signal_skips_empty_signals():
    """notify_users_for_signal([]) returns ok with notified=0 without any DB/HTTP call."""
    from app.modules.telegram_bot.tasks import notify_users_for_signal

    with patch("app.modules.telegram_bot.tasks.send_telegram_notification") as mock_send:
        result = notify_users_for_signal([])

    mock_send.assert_not_called()
    assert result == {"status": "ok", "notified": 0}


def test_notify_users_for_signal_continues_on_send_failure():
    """notify_users_for_signal continues to next user if one send returns False."""
    from app.modules.telegram_bot.tasks import notify_users_for_signal

    # Two pro users with chat_ids "111" and "222"
    fake_rows = [("111",), ("222",)]
    mock_session = MagicMock()
    mock_session.execute.return_value.fetchall.return_value = fake_rows

    call_count = {"n": 0}

    def side_effect(chat_id, text):
        call_count["n"] += 1
        if chat_id == "111":
            return False  # First call fails (returns False, does not raise)
        return True

    with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test_token"}):
        with patch("app.core.db_sync.get_superuser_sync_db_session") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            with patch("app.modules.telegram_bot.tasks.send_telegram_notification", side_effect=side_effect):
                result = notify_users_for_signal([_SAMPLE_SIGNAL])

    # Both calls were attempted
    assert call_count["n"] == 2
    # Only the second succeeded
    assert result["notified"] == 1
    assert result["status"] == "ok"


# =============================================================================
# Task 3: scan_and_store_signals dispatches notify_users_for_signal.delay
# =============================================================================

def test_scan_and_store_signals_dispatches_fanout():
    """scan_and_store_signals dispatches notify_users_for_signal.delay when new signals found.

    scan_and_store_signals calls asyncio.run(_run_scan_and_store()).
    We mock _run_scan_and_store to be a coroutine function (side_effect returns a coroutine).
    """
    from app.modules.signal_engine.tasks import scan_and_store_signals

    fake_signals = [_SAMPLE_SIGNAL]

    async def _fake_coroutine():
        return fake_signals

    with patch("app.modules.signal_engine.tasks._run_scan_and_store", side_effect=_fake_coroutine) as mock_scan:
        with patch("app.modules.signal_engine.tasks._send_telegram_signals") as mock_send_admin:
            with patch("app.modules.telegram_bot.tasks.notify_users_for_signal") as mock_fanout:
                mock_fanout.delay = MagicMock()
                result = scan_and_store_signals()

    # Admin alert sent first
    mock_send_admin.assert_called_once_with(fake_signals)
    # Fan-out dispatched exactly once with the signals list
    mock_fanout.delay.assert_called_once_with(fake_signals)
    assert result["status"] == "ok"


def test_scan_and_store_signals_no_dispatch_on_empty():
    """scan_and_store_signals does NOT call notify_users_for_signal.delay when no new signals."""
    from app.modules.signal_engine.tasks import scan_and_store_signals

    async def _fake_coroutine_empty():
        return []

    with patch("app.modules.signal_engine.tasks._run_scan_and_store", side_effect=_fake_coroutine_empty):
        with patch("app.modules.telegram_bot.tasks.notify_users_for_signal") as mock_fanout:
            mock_fanout.delay = MagicMock()
            result = scan_and_store_signals()

    # Fan-out NOT called when no signals
    mock_fanout.delay.assert_not_called()
    assert result["status"] == "ok"
