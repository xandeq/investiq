# Runbook — Celery Queue Flush + Macro/Quotes Force Refresh

**Use when**: Macro rates show 0 on dashboard AND/OR `data_stale=true` is persistent.  
**Root cause**: Queue starvation — periodic tasks accumulated faster than consumed.  
**Diagnosis doc**: `docs/audit/P0_INVESTIGATION.md`

---

## Pre-flight

```bash
# Check queue depth (should be near 0 in steady state)
plink -ssh -batch -pw "$VPS_PASSWORD" root@185.173.110.180 \
  "docker exec financas-redis-1 redis-cli LLEN celery"

# Confirm macro keys are absent (if absent → this runbook is needed)
plink -ssh -batch -pw "$VPS_PASSWORD" root@185.173.110.180 \
  "docker exec financas-redis-1 redis-cli KEYS 'market:macro*'"
```

Expected unhealthy output:
```
LLEN celery → 390
KEYS market:macro* → (empty)
```

---

## Step 1 — Flush the stale queue

```bash
plink -ssh -batch -pw "$VPS_PASSWORD" root@185.173.110.180 \
  "docker exec financas-redis-1 redis-cli DEL celery"
```

Expected output:
```
(integer) 1
```

> **Why**: Accumulated tasks are stale — their data would be from minutes/hours ago.
> Discarding them lets the worker start fresh. Expires added in fix commit prevent
> this accumulation from recurring.

---

## Step 2 — Force refresh macro indicators

> Note: `celery call` requires worker threads to be free. If all workers are blocked
> (e.g., by `refresh_screener_universe`), run directly via Python instead.

```bash
# Preferred: run directly in worker container (bypasses queue)
plink -ssh -batch -pw "$VPS_PASSWORD" root@185.173.110.180 \
  "docker exec financas-celery-worker-1 python -c \
   'from app.modules.market_data.tasks import refresh_macro; refresh_macro()'"
```

Expected output:
```
(empty — task logs go to the worker's stdout, not to plink)
```

Then verify via Redis (Step 4).

---

## Step 3 — Force refresh quote prices

```bash
plink -ssh -batch -pw "$VPS_PASSWORD" root@185.173.110.180 \
  "docker exec financas-celery-worker-1 python -c \
   'from app.modules.market_data.tasks import refresh_quotes; refresh_quotes()'"
```

Expected output:
```
(brapi 429 warnings are normal — task continues and writes successful quotes)
```

---

## Step 4 — Verify Redis populated

```bash
plink -ssh -batch -pw "$VPS_PASSWORD" root@185.173.110.180 \
  "docker exec financas-redis-1 redis-cli MGET \
   market:macro:selic market:macro:cdi market:macro:ipca market:macro:ptax_usd"
```

Expected output:
```
1) "14.6499"
2) "14.6499"
3) "0.7000"
4) "5.1655"
```

```bash
plink -ssh -batch -pw "$VPS_PASSWORD" root@185.173.110.180 \
  "docker exec financas-redis-1 redis-cli KEYS 'market:quote:*' | head -5"
```

Expected output: 5 lines like `market:quote:PETR4` etc.

---

## Step 5 — Smoke test live API

```bash
TOKEN=$(curl -s -X POST https://api.investiq.app/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<your-email>","password":"<your-password>"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -H "Authorization: Bearer $TOKEN" \
  https://api.investiq.app/market-data/macro | python -m json.tool
```

Expected: `data_stale: false`, `selic` and `cdi` ≥ 10.0

---

## Permanent fix (already deployed)

`backend/app/celery_app.py` — all beat entries now carry `options.expires`.
Tasks that age past their interval are auto-discarded. Queue depth in steady
state should stay < 20.

Monitor with:
```bash
plink -ssh -batch -pw "$VPS_PASSWORD" root@185.173.110.180 \
  "docker exec financas-redis-1 redis-cli LLEN celery"
```

---

## Execution log — 2026-04-19

```
Pre-flight:
  LLEN celery → 390
  KEYS market:macro* → (empty)

Step 1 — DEL celery:
  (integer) 1

Step 2 — refresh_macro (direct python):
  selic=14.64993185639369690711236420
  cdi=14.64993185639369690711236420
  ipca=0.88
  ptax_usd=4.9695

Step 3 — refresh_quotes (direct python):
  brapi 429 for BBDC4, WEGE3, ABEV3, BOVA11 (brapi rate-limit, separate issue)
  4/8 quotes written: PETR4, VALE3, ITUB4, MGLU3

Step 4 — MGET verify:
  selic=14.64, cdi=14.64, ipca=0.88, ptax_usd=4.97 ✓
  market:quote:* → 4 keys present (PETR4/VALE3/ITUB4/MGLU3)

Note: brapi 429s are a separate rate-limit issue, not part of the macro P0.
All 4 macro keys restored → macro banner now shows live values.
```
