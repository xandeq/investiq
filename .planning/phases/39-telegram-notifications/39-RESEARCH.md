# Phase 39: Notificações Telegram por Usuário - Research

**Researched:** 2026-05-17
**Domain:** Telegram Bot API, FastAPI PATCH endpoint, Alembic migration, Celery task, React settings card
**Confidence:** HIGH

---

## Summary

This phase connects three existing systems: (1) the Telegram bot infrastructure already in the codebase, (2) the profile router that already has the PATCH pattern established, and (3) the signal engine scan task that already fires on A+ signals. The work is additive and contained — no existing logic needs to be rewritten.

The codebase already has `python-telegram-bot==21.9` in requirements and a working `_send_message()` helper in `app/modules/telegram_bot/tasks.py`. However, every existing send function targets the global admin `TELEGRAM_CHAT_ID` env var. Phase 39 adds a per-user `telegram_chat_id` column to `users` and fans out notifications from the signal engine to each pro user that has configured it.

The profile router already has a consistent pattern for PATCH endpoints on the `users` table (see `/email-prefs` and `/ai-mode`). The frontend already has a consistent card pattern (`EmailPrefsCard`, `AIModeCard`) that is self-contained with its own `useQuery`/`useMutation`. Adding a `TelegramCard` component follows this exact pattern without touching `ProfileContent`'s form wizard.

**Primary recommendation:** 2-plan delivery. Plan 1 = backend (migration 0038, PATCH/GET endpoint, `app/core/telegram.py` shared sender, Celery task hook, unit tests). Plan 2 = frontend (`TelegramCard.tsx` component, Playwright E2E).

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TG-01 | Usuário pro pode informar seu Telegram chat_id em `/profile` — instrucao @userinfobot + campo de texto + botão salvar — campo persiste e reaparece ao recarregar | Migration 0038 adds `telegram_chat_id` to `users`; PATCH `/profile/telegram` persists it; GET `/profile/telegram` returns it; TelegramCard mirrors EmailPrefsCard pattern |
| TG-02 | Backend envia mensagem Telegram automática para cada usuário pro com `telegram_chat_id` quando novo sinal de entrada é gerado — inclui ticker, tipo, preço, grau, link | `signal_engine.tasks.scan_and_store_signals` is the hook point; after `store_signals()` a new Celery task `notify_users_for_signal` queries all pro users with non-null `telegram_chat_id` and calls shared `send_telegram_notification()` |
| TG-03 | Usuário pode desconectar o Telegram (limpar chat_id) via botão "Desconectar" | Same PATCH endpoint with `{"telegram_chat_id": null}` clears the column; TelegramCard shows "Desconectar" button when connected |

</phase_requirements>

---

## 1. Existing Telegram Integration

**Confidence: HIGH** — verified by direct code inspection.

### What Already Exists

| File | What it Does | Reuse for Phase 39 |
|------|-------------|---------------------|
| `backend/requirements.txt` line 30 | `python-telegram-bot==21.9` installed | No need to add dependency; use `requests` directly (lighter) |
| `app/modules/telegram_bot/tasks.py` | `_send_message(text)` — sends to global `TELEGRAM_CHAT_ID` env var via `requests.post` | Pattern to copy; Phase 39 needs a version that accepts a dynamic `chat_id` arg |
| `app/modules/signal_engine/tasks.py` | `_send_telegram_signals(signals)` — sends A+ signal alerts to admin chat | This is the hook point; after this call, also fan out to per-user chats |
| `app/modules/outcome_tracker/tasks.py` | `_send_telegram_notification(message)` — same admin-only pattern | Same pattern, admin-only |

### Send Pattern (Verified)

```python
# Source: backend/app/modules/telegram_bot/tasks.py
import requests
url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
resp = requests.post(
    url,
    json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
    timeout=10,
)
resp.raise_for_status()
```

The pattern is `requests.post` (sync), not the `python-telegram-bot` async SDK — consistent with Celery sync workers. Phase 39 creates `app/core/telegram.py` with a `send_telegram_notification(chat_id: str, text: str) -> None` function using this same pattern.

### TELEGRAM_BOT_TOKEN

Already in `.secrets.env` and set in production environment. The roadmap note confirms: `telegram_chat_id 721438452` is the admin chat (in `TELEGRAM_CHAT_ID` env var). Phase 39 does NOT touch the admin channel. It reads `TELEGRAM_BOT_TOKEN` (same token) but sends to user-supplied `chat_id` values from the DB.

---

## 2. Signal Generation Hook Point

**Confidence: HIGH** — verified by direct code inspection.

### Hook Location

**File:** `backend/app/modules/signal_engine/tasks.py`
**Function:** `scan_and_store_signals()` — the `@shared_task(name="signal_engine.scan_signals")` Celery task
**Schedule:** Every 30 minutes, Mon-Fri, 10h-17h BRT (registered in `celery_app.py` line ~211)

### Exact Hook Point

```python
# backend/app/modules/signal_engine/tasks.py — scan_and_store_signals()
new_signals = asyncio.run(_run_scan_and_store())   # stores in Redis
if new_signals:
    _send_telegram_signals(new_signals)             # sends to admin
    # HOOK: call notify_users_for_signal.delay(new_signals) HERE
    logger.info("signal_engine: %d new A+ signal(s) found and alerted", len(new_signals))
```

The `new_signals` list contains dicts with structure:
```python
{
    "ticker": str,
    "grade": str,       # "A+"
    "score": float,
    "passed_gates": int,
    "total_gates": int,
    "setup": {
        "pattern": str,
        "direction": str,  # "long" | "short"
        "entry": float,
        "stop": float,
        "target_1": float,
        "target_2": float,
        "rr": float,
        "grade": str,
    },
    "confluences": list[str],
    "indicators": dict,
}
```

### Deduplication

The `scan_and_store_signals` task already deduplicates at the signal level: it compares `new_signals` against the Redis-cached `previous_tickers` set and only passes `truly_new` to `_send_telegram_signals`. The per-user notification task receives the same `truly_new` list — no additional deduplication needed beyond what the scan already does.

The ROADMAP notes "Rate limit: 1 notificação por sinal por usuário (evitar duplicatas com Redis lock)" — this is satisfied by the `truly_new` filter (signals that weren't in Redis 30 minutes ago). Adding a Redis dedup key per user per ticker per day (matching `_STOP_DEDUP_PREFIX` pattern in `signal_engine/tasks.py`) is an option but may be over-engineering given the `truly_new` filter already handles it.

---

## 3. User Model Schema

**Confidence: HIGH** — verified by reading `auth/models.py` directly.

### Current `users` Table Columns

| Column | Type | Notes |
|--------|------|-------|
| `id` | String(36) | PK, UUID |
| `tenant_id` | String(36) | Index |
| `email` | String(255) | Unique, Index |
| `hashed_password` | String(255) | |
| `is_verified` | Boolean | |
| `plan` | String(50) | "free" \| "pro" \| "enterprise" |
| `created_at` | DateTime(tz) | |
| `updated_at` | DateTime(tz) | |
| `trial_ends_at` | DateTime(tz) \| None | |
| `trial_used` | Boolean | |
| `trial_warning_sent` | Boolean | |
| `email_digest_enabled` | Boolean | server_default="true" |
| `ai_mode` | String(10) | server_default="standard" |
| `stripe_customer_id` | String(50) \| None | |
| `stripe_subscription_id` | String(50) \| None | |
| `subscription_status` | String(30) \| None | |
| `subscription_current_period_end` | DateTime(tz) \| None | |

### What Migration 0038 Adds

```sql
ALTER TABLE users ADD COLUMN telegram_chat_id VARCHAR(32) DEFAULT NULL;
```

**SQLAlchemy column to add to `User` model:**
```python
telegram_chat_id: Mapped[str | None] = mapped_column(
    String(32), nullable=True, server_default=sa.text("NULL")
)
```

VARCHAR(32) is sufficient: Telegram chat IDs are integers (positive for users, negative for groups), max ~20 digits. VARCHAR(32) matches the ROADMAP spec.

### Migration Template (from 0037 pattern)

```python
"""add telegram_chat_id to users

Revision ID: 0038
Revises: 0037
Create Date: 2026-05-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("users", sa.Column("telegram_chat_id", sa.String(32), nullable=True))

def downgrade() -> None:
    op.drop_column("users", "telegram_chat_id")
```

No dialect guard needed — `ADD COLUMN ... nullable=True` works on both SQLite (tests) and PostgreSQL (prod).

---

## 4. Profile Router — Existing Endpoints and Where to Add

**Confidence: HIGH** — verified by reading `profile/router.py` in full.

### Existing Endpoints

| Method | Path | What it does |
|--------|------|-------------|
| GET | `/profile` | Returns `InvestorProfile` (from `investor_profiles` table, NOT `users`) |
| POST | `/profile` | Upsert `InvestorProfile` |
| GET | `/profile/email-prefs` | Returns `email_digest_enabled` from `users` |
| PATCH | `/profile/email-prefs` | Updates `email_digest_enabled` on `users` |
| GET | `/profile/ai-mode` | Returns `ai_mode` + `plan` from `users` |
| PATCH | `/profile/ai-mode` | Updates `ai_mode` on `users` (pro-gated) |

### Where to Add

Add two new endpoint functions to `profile/router.py` following the exact pattern of `/email-prefs`:

**GET `/profile/telegram`** — returns `{"telegram_chat_id": str | None}`
**PATCH `/profile/telegram`** — accepts `{"telegram_chat_id": str | None}`, persists on `users`

The PATCH endpoint also includes plan-gating (only pro users can save a chat_id). Free users get a 403 with an upgrade URL.

### PATCH Pattern to Follow

```python
# Exact pattern from PATCH /profile/ai-mode — verified in router.py
@router.patch("/telegram", response_model=TelegramResponse)
async def update_telegram(
    data: TelegramUpdate,
    db: AsyncSession = Depends(get_authed_db),
    current_user: dict = Depends(get_current_user),
) -> TelegramResponse:
    result = await db.execute(select(User).where(User.id == current_user["user_id"]))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    # Pro gate — only pro users can configure Telegram
    if data.telegram_chat_id is not None and user.plan != "pro":
        raise HTTPException(
            status_code=403,
            detail={"code": "REQUIRES_PRO", "message": "Notificações Telegram requerem plano Pro.", "upgrade_url": "/planos"}
        )

    await db.execute(
        update(User)
        .where(User.id == current_user["user_id"])
        .values(telegram_chat_id=data.telegram_chat_id)
    )
    await db.flush()
    return TelegramResponse(telegram_chat_id=data.telegram_chat_id)
```

Note: The PATCH endpoint also includes plan-gating logic. Trial users with active trial should count as pro (consistent with `get_user_plan` in `plan_gate.py`). Rather than re-implementing trial elevation, use `get_user_plan` as a Depends instead of checking `user.plan` directly.

**Important:** `GET /profile` currently returns `InvestorProfile` (from `investor_profiles` table). It does NOT include `telegram_chat_id`. The new `GET /profile/telegram` endpoint reads from `users`. The ROADMAP says `GET /profile` should return `telegram_chat_id` — this is achievable by extending `GET /profile` as well, but simpler to keep it a separate `/profile/telegram` GET to avoid changing the existing `InvestorProfileResponse` schema. The ROADMAP acceptance criterion #2 says "GET /profile retorna telegram_chat_id" — the safest approach is to add it as a separate endpoint, matching the email-prefs and ai-mode patterns.

---

## 5. Celery Task Pattern

**Confidence: HIGH** — verified by reading `signal_engine/tasks.py` and `db_sync.py`.

### New Task: `notify_users_for_signal`

```python
# app/modules/telegram_bot/tasks.py (extend existing file)
@celery_app.task(name="telegram_bot.notify_users_for_signal")
def notify_users_for_signal(signals: list[dict]) -> dict:
    """Fan out A+ signal notifications to all pro users with telegram_chat_id set."""
    if not signals:
        return {"status": "ok", "notified": 0}

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        logger.warning("notify_users_for_signal: TELEGRAM_BOT_TOKEN not set")
        return {"status": "skipped"}

    from app.core.db_sync import get_superuser_sync_db_session
    from sqlalchemy import text as sa_text

    with get_superuser_sync_db_session() as db:
        rows = db.execute(
            sa_text(
                "SELECT telegram_chat_id FROM users "
                "WHERE plan = 'pro' AND telegram_chat_id IS NOT NULL AND telegram_chat_id != ''"
            )
        ).fetchall()

    chat_ids = [row[0] for row in rows]
    if not chat_ids:
        return {"status": "ok", "notified": 0}

    from app.core.telegram import send_telegram_notification
    message = _build_signal_message(signals)
    notified = 0
    for chat_id in chat_ids:
        try:
            send_telegram_notification(chat_id, message)
            notified += 1
        except Exception as exc:
            logger.warning("notify_users_for_signal: failed for chat_id=%s: %s", chat_id, exc)

    return {"status": "ok", "notified": notified}
```

### Critical: Trial Users

The DB query `WHERE plan = 'pro'` misses trial users who are effectively pro. The correct query:

```sql
SELECT telegram_chat_id FROM users
WHERE telegram_chat_id IS NOT NULL AND telegram_chat_id != ''
  AND (plan = 'pro' OR (plan = 'free' AND trial_ends_at IS NOT NULL AND trial_ends_at > NOW()))
```

### New Shared Module: `app/core/telegram.py`

```python
# app/core/telegram.py
import logging
import os
import requests

logger = logging.getLogger(__name__)

def send_telegram_notification(chat_id: str, text: str) -> None:
    """Send a Telegram message to a specific chat_id."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        logger.warning("send_telegram_notification: TELEGRAM_BOT_TOKEN not set")
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=10,
    )
    resp.raise_for_status()
```

### Hook into scan_and_store_signals

```python
# signal_engine/tasks.py — existing scan_and_store_signals task
if new_signals:
    _send_telegram_signals(new_signals)   # existing admin alert
    # NEW: fan out to per-user Telegram
    from app.modules.telegram_bot.tasks import notify_users_for_signal
    notify_users_for_signal.delay(new_signals)
```

Use `.delay()` (async Celery dispatch) so the scan task is not blocked by the fan-out.

### NO Beat Schedule Needed

`notify_users_for_signal` is event-driven (called by `scan_and_store_signals`), not time-driven. No new entry in `celery_app.py` beat schedule. `app/modules/telegram_bot.tasks` is already in `celery_app.py include` list (line 54) — the task is auto-discovered.

---

## 6. Frontend Profile Page Structure

**Confidence: HIGH** — verified by reading all profile feature files.

### Current Layout (ProfileContent.tsx)

When `showForm == false` (profile exists and not editing), `ProfileContent` renders in this order:

```
ProfileSummary (wizard summary card)
AIModeCard
EmailPrefsCard
```

Phase 39 adds `TelegramCard` after `EmailPrefsCard`:

```
ProfileSummary
AIModeCard
EmailPrefsCard
TelegramCard      ← NEW
```

### TelegramCard Component

Create `frontend/src/features/profile/components/TelegramCard.tsx` following the `AIModeCard` pattern exactly:

- Self-contained: own `useQuery` for GET `/profile/telegram`, own `useMutation` for PATCH `/profile/telegram`
- Handles loading state with pulse skeleton
- Handles pro gate: shows "Disponível no Plano Pro" CTA for free users
- Two states: (a) not connected — shows text input + "Conectar" button, (b) connected — shows masked chat_id + "Desconectar" button
- Instructions: how to get chat_id via @userinfobot (TG-01 requires this)
- Import `MessageCircle` from `lucide-react` as icon

### No Changes to ProfileContent.tsx in Form Mode

The Telegram card is only shown in the summary view (not editing mode). This means no new wizard step — consistent with how `AIModeCard` and `EmailPrefsCard` are implemented (they're outside the form wizard entirely).

### Profile API Extension

Add to `frontend/src/features/profile/api.ts`:

```typescript
// Telegram preferences
export async function getTelegramPrefs(): Promise<{ telegram_chat_id: string | null }> {
  return apiClient<{ telegram_chat_id: string | null }>("/profile/telegram");
}

export async function updateTelegramPrefs(telegram_chat_id: string | null): Promise<{ telegram_chat_id: string | null }> {
  return apiClient<{ telegram_chat_id: string | null }>("/profile/telegram", {
    method: "PATCH",
    body: JSON.stringify({ telegram_chat_id }),
  });
}
```

---

## 7. Migration Pattern from 0037

**Confidence: HIGH** — verified by reading `0037_add_fundo_asset_class_and_fund_tables.py`.

### Pattern Template

```python
"""add telegram_chat_id to users

Revision ID: 0038
Revises: 0037
Create Date: 2026-05-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("users", sa.Column("telegram_chat_id", sa.String(32), nullable=True))

def downgrade() -> None:
    op.drop_column("users", "telegram_chat_id")
```

**No dialect gate needed.** `ADD COLUMN ... nullable=True` without a server_default works on both SQLite (tests) and PostgreSQL. SQLAlchemy ORM treats missing column as `None` until upgraded, which is safe.

**File naming:** `0038_add_telegram_chat_id.py`

---

## 8. Recommended Implementation — 2 Plans

### Plan 39-01: Backend (migration + endpoint + Celery task + tests)

1. `backend/alembic/versions/0038_add_telegram_chat_id.py` — migration (ADD COLUMN)
2. `backend/app/modules/auth/models.py` — add `telegram_chat_id` to `User` model
3. `backend/app/core/telegram.py` — new shared `send_telegram_notification(chat_id, text)` function
4. `backend/app/modules/profile/router.py` — add `GET /profile/telegram` + `PATCH /profile/telegram` endpoints with pro gate
5. `backend/app/modules/telegram_bot/tasks.py` — add `notify_users_for_signal` Celery task
6. `backend/app/modules/signal_engine/tasks.py` — add `.delay()` call to `scan_and_store_signals` after `_send_telegram_signals`
7. `backend/tests/test_telegram_notifications.py` — unit tests covering:
   - TG-01: PATCH /profile/telegram saves chat_id (pro user)
   - TG-01: GET /profile/telegram returns chat_id after save
   - TG-01: PATCH /profile/telegram with null clears chat_id (TG-03)
   - TG-01: Free user PATCH returns 403
   - TG-02: `notify_users_for_signal` sends to correct users (mock `send_telegram_notification`)
   - TG-02: `notify_users_for_signal` skips free users
   - TG-02: `notify_users_for_signal` with empty signals returns early

### Plan 39-02: Frontend + E2E

1. `frontend/src/features/profile/components/TelegramCard.tsx` — new card component
2. `frontend/src/features/profile/components/ProfileContent.tsx` — add `<TelegramCard />` after `<EmailPrefsCard />`
3. `frontend/src/features/profile/api.ts` — add `getTelegramPrefs` + `updateTelegramPrefs`
4. `frontend/e2e/v1.9-telegram-notifications.spec.ts` — Playwright E2E:
   - Navigate to `/profile`
   - Telegram section visible
   - Enter chat_id + click "Conectar" → success state
   - Reload → chat_id persisted
   - Click "Desconectar" → null state

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP call to Telegram API | Custom HTTP wrapper | `requests.post` (already the project pattern) | Consistent with every other Telegram send in the codebase |
| Fan-out per-user queries | Async query inside FastAPI | `get_superuser_sync_db_session` + raw SQL | Celery task — must use sync engine, never asyncpg |
| Telegram deduplication | Custom lock system | `truly_new` filter already in `scan_and_store_signals` | The scan already prevents re-alerting the same signals |
| Pro-plan check | Custom plan logic | `get_user_plan` Depends or check `user.plan` + trial | `plan_gate.py` has trial elevation logic already |

---

## Common Pitfalls

### Pitfall 1: asyncpg in Celery Task
**What goes wrong:** Importing `async_session_factory` from `app.core.db` inside `notify_users_for_signal` crashes the worker.
**Why it happens:** Celery workers are synchronous; asyncpg requires an event loop that doesn't exist in Celery's default execution context.
**How to avoid:** Use `get_superuser_sync_db_session` from `app.core.db_sync` with raw `sa_text` queries — the exact pattern used in `signal_engine/tasks.py` line ~113 (`_get_user_email_sync`).
**Warning signs:** `RuntimeError: no running event loop` in Celery worker logs.

### Pitfall 2: Migration Missing from `User` Model
**What goes wrong:** Migration runs in DB but `User.telegram_chat_id` attribute doesn't exist in SQLAlchemy model, causing `AttributeError` when the PATCH endpoint tries to `update(User).values(telegram_chat_id=...)`.
**How to avoid:** Update `auth/models.py` in the same plan as the migration. Both must ship together.

### Pitfall 3: Pro Gate Using `user.plan` Directly (Missing Trial Elevation)
**What goes wrong:** Trial users (plan="free", trial_ends_at in future) are blocked from saving their chat_id even though they have pro access.
**How to avoid:** Use `get_user_plan` dependency (from `plan_gate.py`) in the PATCH endpoint, or manually check `trial_ends_at > now()` in the endpoint.

### Pitfall 4: Celery Task Not Registered
**What goes wrong:** `notify_users_for_signal` is defined in `telegram_bot/tasks.py` but calling `.delay()` raises `celery.exceptions.NotRegistered`.
**How to avoid:** `app/modules/telegram_bot.tasks` is already in `celery_app.py` include list. Confirm the task name matches `name="telegram_bot.notify_users_for_signal"`.

### Pitfall 5: Telegram API Rate Limit (429)
**What goes wrong:** With many pro users, sending individual messages in a tight loop hits Telegram's 30 msg/sec limit.
**How to avoid:** For v1, add `time.sleep(0.05)` (50ms) between sends inside the loop. At production scale (unlikely in v1), use `asyncio.gather` with semaphore or Telegram's batch API. The ROADMAP says "Sem histórico de notificações em v1 (só envio)" — 50ms sleep is acceptable.

### Pitfall 6: Frontend Card in Form Mode
**What goes wrong:** Adding `<TelegramCard />` inside the form wizard renders it during editing, creating confusing UX.
**How to avoid:** `TelegramCard` is rendered only in the `!showForm` branch of `ProfileContent` (the summary view), exactly like `AIModeCard` and `EmailPrefsCard`.

---

## Code Examples

### Existing Send Pattern (Canonical)
```python
# Source: backend/app/modules/telegram_bot/tasks.py:15-29
def _send_message(text: str) -> None:
    """Send a message to the configured Telegram chat."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id:
        logger.warning("_send_message: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("_send_message failed: %s", exc)
```

### Superuser DB Query in Celery (Canonical)
```python
# Source: backend/app/modules/signal_engine/tasks.py:113-127
def _get_user_email_sync(tenant_id: str) -> str | None:
    from sqlalchemy import text as sa_text
    from app.core.db_sync import get_superuser_sync_db_session
    try:
        with get_superuser_sync_db_session() as db:
            row = db.execute(
                sa_text("SELECT email FROM users WHERE id = :uid LIMIT 1"),
                {"uid": tenant_id},
            ).fetchone()
            return row[0] if row else None
    except Exception as exc:
        logger.error("check_stop_loss: failed to get email for %s: %s", tenant_id, exc)
        return None
```

### PATCH Endpoint on `users` Table (Canonical)
```python
# Source: backend/app/modules/profile/router.py:113-129
@router.patch("/email-prefs", response_model=EmailPrefsResponse)
async def update_email_prefs(
    data: EmailPrefsUpdate,
    db: AsyncSession = Depends(get_authed_db),
    current_user: dict = Depends(get_current_user),
) -> EmailPrefsResponse:
    await db.execute(
        update(User)
        .where(User.id == current_user["user_id"])
        .values(email_digest_enabled=data.email_digest_enabled)
    )
    await db.flush()
    return EmailPrefsResponse(email_digest_enabled=data.email_digest_enabled)
```

### Frontend Self-Contained Settings Card (Canonical)
```typescript
// Source: frontend/src/features/profile/components/AIModeCard.tsx (pattern)
export function AIModeCard() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery<AIModeData>({
    queryKey: ["profile", "ai-mode"],
    queryFn: fetchAIMode,
    staleTime: 60_000,
    retry: false,
  });
  const mutation = useMutation({
    mutationFn: (mode: string) => updateAIMode(mode),
    onSuccess: (updated) => {
      queryClient.setQueryData(["profile", "ai-mode"], updated);
    },
  });
  // ... card JSX
}
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (backend) / Playwright (E2E) |
| Config file | `backend/pytest.ini` or inferred from `pyproject.toml` |
| Quick run command | `cd backend && python -m pytest tests/test_telegram_notifications.py -x -q` |
| Full suite command | `cd backend && python -m pytest -x -q` |
| E2E command | `cd frontend && npx playwright test e2e/v1.9-telegram-notifications.spec.ts` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| TG-01 | PATCH /profile/telegram persists chat_id for pro user | unit | `pytest tests/test_telegram_notifications.py::test_patch_telegram_saves_chat_id -x` | No — Wave 0 |
| TG-01 | GET /profile/telegram returns chat_id after save | unit | `pytest tests/test_telegram_notifications.py::test_get_telegram_returns_chat_id -x` | No — Wave 0 |
| TG-01 | Free user PATCH returns 403 | unit | `pytest tests/test_telegram_notifications.py::test_patch_telegram_free_user_403 -x` | No — Wave 0 |
| TG-01 | Field persists after logout/login | E2E | `playwright test e2e/v1.9-telegram-notifications.spec.ts` | No — Wave 0 |
| TG-02 | notify_users_for_signal calls send for pro users with chat_id | unit | `pytest tests/test_telegram_notifications.py::test_notify_users_sends_to_pro -x` | No — Wave 0 |
| TG-02 | notify_users_for_signal skips free users | unit | `pytest tests/test_telegram_notifications.py::test_notify_users_skips_free -x` | No — Wave 0 |
| TG-02 | Empty signals list returns early | unit | `pytest tests/test_telegram_notifications.py::test_notify_empty_signals -x` | No — Wave 0 |
| TG-03 | PATCH with null clears chat_id | unit | `pytest tests/test_telegram_notifications.py::test_patch_telegram_disconnect -x` | No — Wave 0 |
| TG-03 | Disconnect button in UI clears field | E2E | `playwright test e2e/v1.9-telegram-notifications.spec.ts` | No — Wave 0 |

### Sampling Rate

- Per task commit: `pytest tests/test_telegram_notifications.py -x -q`
- Per wave merge: `pytest -x -q` (full backend suite, 257+ tests)
- Phase gate: full backend suite green + `playwright test e2e/v1.9-telegram-notifications.spec.ts` passing

### Wave 0 Gaps

- [ ] `backend/tests/test_telegram_notifications.py` — covers TG-01, TG-02, TG-03 unit tests
- [ ] `backend/app/core/telegram.py` — shared sender module (needed before tests can mock it)
- [ ] `frontend/e2e/v1.9-telegram-notifications.spec.ts` — Playwright E2E for TG-01 + TG-03

---

## Open Questions

1. **Trial user fan-out in Celery task**
   - What we know: `get_user_plan` in `plan_gate.py` handles trial elevation in FastAPI context. In Celery (sync DB), trial elevation requires a SQL check (`trial_ends_at > NOW()`).
   - What's unclear: Whether trial users should receive signal notifications.
   - Recommendation: Include them — the query should be `WHERE plan = 'pro' OR (plan = 'free' AND trial_ends_at > NOW())`. This is consistent with the trial elevation philosophy throughout the codebase.

2. **Message format for per-user Telegram signal**
   - What we know: Admin message uses HTML parse_mode with ticker, pattern, entry, stop, target, R/R.
   - What's unclear: Whether to include a link to `https://investiq.com.br/stock/{ticker}` (ROADMAP says "link para a página do ativo").
   - Recommendation: Include the link. Format: `<a href="https://investiq.com.br/stock/{ticker}">{ticker}</a>`.

3. **Validate chat_id format on PATCH**
   - What we know: Telegram chat IDs are integers (can be negative for groups). VARCHAR(32) stores them as strings.
   - What's unclear: Whether to validate format server-side (regex for digits + optional leading minus).
   - Recommendation: Add Pydantic validator: `pattern=r'^-?\d{1,20}$'` — rejects obviously malformed values without making a live Telegram API call on save.

---

## Sources

### Primary (HIGH confidence)

- Direct inspection: `backend/app/modules/telegram_bot/tasks.py` — existing send pattern
- Direct inspection: `backend/app/modules/signal_engine/tasks.py` — hook point + dedup pattern
- Direct inspection: `backend/app/modules/auth/models.py` — User model columns
- Direct inspection: `backend/app/modules/profile/router.py` — PATCH endpoint pattern
- Direct inspection: `backend/app/core/db_sync.py` — Celery sync DB session pattern
- Direct inspection: `frontend/src/features/profile/components/AIModeCard.tsx` — frontend card pattern
- Direct inspection: `backend/alembic/versions/0037_add_fundo_asset_class_and_fund_tables.py` — migration pattern

### Secondary (MEDIUM confidence)

- ROADMAP.md Phase 39 section — implementation notes (spec written by prior planning session)
- REQUIREMENTS.md TG-01/TG-02/TG-03 — acceptance criteria

---

## Metadata

**Confidence breakdown:**
- Existing Telegram integration: HIGH — verified by reading every send function
- Signal hook point: HIGH — exact file and line identified
- User model schema: HIGH — all columns enumerated from source
- Profile router pattern: HIGH — confirmed by reading full router
- Celery task pattern: HIGH — confirmed by reading existing analogous tasks
- Frontend card pattern: HIGH — confirmed by reading AIModeCard verbatim
- Migration pattern: HIGH — confirmed by reading 0037

**Research date:** 2026-05-17
**Valid until:** 2026-06-17 (stable codebase — no fast-moving dependencies)
