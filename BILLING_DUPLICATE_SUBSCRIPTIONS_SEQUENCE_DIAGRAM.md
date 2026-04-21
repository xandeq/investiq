# Sequence Diagram: Duplicate Subscription Bug & Fixes

## 🔴 BEFORE: Race Condition (What Happened)

```
User                          Frontend                Backend                  Stripe DB
 │                               │                        │                       │
 ├─ Click "Upgrade"             │                        │                       │
 │                               ├─ GET /me ──────────→  │                       │
 │                               │  (check plan="free")   │                       │
 │                               │←─ 200: plan=free ──┤  │                       │
 │                               │                        │                       │
 │                               ├─ POST /checkout ──→   │                       │
 │                               │                        ├─ create_or_get_customer
 │                               │                        ├─ create_checkout_session
 │                               │                        │←─ session_id="cs_1" ──┤
 │                               │←─ checkout_url ────────┤                       │
 │                               │                        │                       │
 │  Click Stripe Checkout URL    │                        │                       │
 │  (completes payment)          │                        │                        │
 │                               │                        │  checkout.session.complete
 │                               │                        │  (Stripe fires webhook)
 │                               │                        │←── event_1 ───────────┤
 │                               │                        │                        │
 │                               │  Webhook Handler ────→ │                        │
 │                               │  handle_checkout_completed()                    │
 │                               │  ├─ Look up user by customer_id                 │
 │                               │  ├─ Get prior_sub="sub_old" from user           │
 │                               │  ├─ IF prior_sub != new_sub:                   │
 │                               │  │   └─ await cancel_async("sub_old")           │
 │                               │  │       └─ NETWORK TIMEOUT! ✗                 │
 │                               │  │       └─ logger.error(...) [SILENT]         │
 │                               │  │       └─ CONTINUE ANYWAY (BUG!)             │
 │                               │  │                                              │
 │                               │  ├─ Upsert: Subscription(sub_new, active) ✓    │
 │                               │  ├─ Update: User.plan = pro                   │
 │                               │  │          User.stripe_subscription_id = sub_new
 │                               │  │                                              │
 │                               │  RESULT: 2 active subscriptions in DB          │
 │                               │                                              
 │                               │  DB State:                                      
 │                               │  ├─ Subscription(sub_old, active) ← OLD         
 │                               │  ├─ Subscription(sub_new, active) ← NEW          
 │                               │  ├─ User.stripe_subscription_id = sub_new       
 │                               │  └─ User.plan = pro                             
 │                               │                                              
 │  ❌ PROBLEM: Now charged TWICE per month
```

---

## 🟡 INTERMEDIATE: Partial Fix Applied (Current State)

```
User                          Frontend                Backend                  Stripe DB
 │                               │                        │                       │
 ├─ Click "Upgrade"             │                        │                       │
 │                               ├─ GET /me ──────────→  │                       │
 │                               │                        │                       │
 │                               ├─ POST /checkout ──→   │                       │
 │                               │ (rate limited: 3/min)  │  ✓ NEW: Rate limit    │
 │                               │                        │                       │
 │  Click Stripe Checkout        │                        │                       │
 │  (payment succeeds)           │                        │                       │
 │                               │                        │  checkout.session.complete
 │                               │                        │←── event ─────────────┤
 │                               │                        │                        │
 │                               │  Webhook Handler:      │                        │
 │                               │  ├─ Check StripeEvent table ✓ (idempotent)    │
 │                               │  ├─ Look up user                               │
 │                               │  ├─ IF prior_sub != new_sub:                  │
 │                               │  │   └─ await cancel_async("sub_old")         │
 │                               │  │       ├─ NETWORK TIMEOUT!                  │
 │                               │  │       ├─ logger.error(...) [SILENT] ✗      │
 │                               │  │       └─ CONTINUE ANYWAY (STILL BUG!)      │
 │                               │  │                                             │
 │                               │  ├─ Upsert: Subscription(sub_new, active)     │
 │                               │  ├─ Update: User.plan = pro                   │
 │                               │  │                                             │
 │                               │  ├─ ✓ NEW: Check active_count                 │
 │                               │  │  IF active_count > 1:                       │
 │                               │  │    logger.warning("duplicate_sub_detected")│
 │                               │  │    ← ALERTS OPS TO INVESTIGATE             │
 │                               │  │                                             │
 │                               │  DB Write:                                      │
 │                               │  ├─ TRY: INSERT Subscription(sub_new, active) │
 │                               │  └─ ✓ NEW: Unique constraint check            │
 │                               │     ├─ Index: uq_user_one_active_subscription │
 │                               │     │  WHERE status IN ('active', 'trialing')  │
 │                               │     │                                          │
 │                               │     └─ IF sub_old IS STILL active:            │
 │                               │        └─ CONSTRAINT VIOLATION! ✗             │
 │                               │           Webhook handler FAILS               │
 │                               │                                               
 │  ✓ PARTIALLY FIXED:                                                          
 │   • Rate limiting prevents double-click on frontend                          
 │   • Database constraint prevents duplicates on INSERT                       
 │   • Observability canary alerts ops                                         
 │   ✗ STILL BROKEN:                                                           
 │   • If cancel_async fails, old subscription still active                   
 │   • New subscription can't be inserted (constraint)                        
 │   • Webhook dies, customer left in limbo                                   
```

---

## 🟢 RECOMMENDED FIX: Full Solution (Not Yet Applied)

```
User                          Frontend                Backend                  Stripe DB
 │                               │                        │                       │
 ├─ Click "Upgrade"             │                        │                       │
 │                               ├─ GET /me ──────────→  │                       │
 │                               │                        │                       │
 │                               ├─ POST /checkout ──→   │                       │
 │                               │  (rate limited)        │                       │
 │                               │  ✓ NEW: button disabled during POST            │
 │                               │  ✓ NEW: debounce handler                      │
 │                               │                        ├─ Acquire user lock    │
 │                               │                        │  (prevent concurrent)  │
 │                               │                        │                       │
 │                               │                        ├─ Check inflight:      │
 │                               │                        │  ✓ NEW: any pending   │
 │                               │                        │  checkout sessions?   │
 │                               │                        │  └─ If yes, return    │
 │                               │                        │     existing session   │
 │                               │                        │                       │
 │                               │                        ├─ Create session       │
 │                               │                        │  ✓ NEW: idempotency_key
 │                               │                        │        = user_id +    │
 │                               │                        │          timestamp    │
 │                               │                        │←─ session_url (idempotent)
 │                               │←─ checkout_url        │                       │
 │                               │                        │  Release lock ✓       │
 │                               │  [button re-enabled]   │                       │
 │                               │                        │                       │
 │  Click Stripe Checkout        │                        │                       │
 │  (completes payment)          │                        │                       │
 │                               │                        │  checkout.session.complete
 │                               │                        │←── event ─────────────┤
 │                               │                        │                        │
 │                               │  Webhook Handler:      │                        │
 │                               │  ├─ Check StripeEvent (idempotent) ✓           │
 │                               │  ├─ START TRANSACTION ✓ NEW                    │
 │                               │  │                                             │
 │                               │  ├─ Look up user                               │
 │                               │  ├─ IF prior_sub != new_sub:                  │
 │                               │  │   └─ await cancel_async("sub_old")          │
 │                               │  │       ├─ TIMEOUT!                          │
 │                               │  │       └─ RAISE EXCEPTION ✓ NEW              │
 │                               │  │          (don't continue)                   │
 │                               │  │          └─ TRANSACTION ROLLBACK ✓         │
 │                               │  │          └─ Webhook fails, Stripe retries  │
 │                               │  │          └─ Dead-letter queue ✓ NEW        │
 │                               │  │                                             │
 │                               │  │ (Assuming cancel succeeds:)                │
 │                               │  │                                             │
 │                               │  ├─ Upsert: Subscription(sub_new, active)     │
 │                               │  ├─ Record old sub canceled in audit log ✓    │
 │                               │  ├─ Update User.plan = pro (atomic) ✓         │
 │                               │  ├─ Update User.stripe_subscription_id        │
 │                               │  │                                             │
 │                               │  ├─ ✓ Check active_count                      │
 │                               │  │  IF > 1: log warning                       │
 │                               │  │                                             │
 │                               │  ├─ COMMIT TRANSACTION ✓                      │
 │                               │  │  (all-or-nothing)                          │
 │                               │  │                                             │
 │  ✓ FULLY FIXED:                                                              
 │   • Frontend prevents double-click (button disabled, debounced)               
 │   • Idempotency key prevents accidental duplicate sessions                   
 │   • User-level lock prevents concurrent upgrades                            
 │   • Transaction ensures atomicity (cancel + create + update)                
 │   • Failed cancel = webhook failure + Stripe auto-retry                     
 │   • Database constraint final safety net                                    
 │   • Audit log for forensics                                                
 │   • Dead-letter queue for visibility                                       
```

---

## 📊 Failure Modes Comparison

### Scenario 1: User Double-Clicks "Upgrade"

```
BEFORE FIX:
  Click 1: POST /checkout → session_1 → sub_1 created
  Click 2: POST /checkout → session_2 → sub_2 created (duplicate!)
  RESULT: Two subscriptions

AFTER PARTIAL FIX:
  Click 1: POST /checkout (rate limit: 3/min) → OK
  Click 2: POST /checkout within 20 sec → REJECTED (rate limit)
  RESULT: Only one subscription (prevented)

AFTER FULL FIX:
  Click 1: POST /checkout → acquire lock → create session → release lock → OK
  Click 2: POST /checkout (within 1 sec) → acquire lock (waits)
           ├─ Check inflight sessions
           └─ Return session_1 (deduped)
  RESULT: One subscription (prevented + deduped)
```

---

### Scenario 2: Stripe Cancel Times Out

```
BEFORE FIX:
  webhook: cancel_async("sub_old")
    └─ TIMEOUT (network partition)
    └─ except: log error
    └─ continue anyway ← BUG
    └─ upsert sub_new
  RESULT: Two active subscriptions, both charge monthly

AFTER PARTIAL FIX:
  webhook: cancel_async("sub_old")
    └─ TIMEOUT
    └─ except: log error
    └─ continue anyway ← STILL BUG
    └─ try: insert sub_new
       └─ CONSTRAINT VIOLATION! (sub_old is still active)
       └─ webhook fails
       └─ Stripe retries
  RESULT: Webhook fails until cancel succeeds, but still buggy

AFTER FULL FIX:
  webhook: START TRANSACTION
    └─ cancel_async("sub_old")
       └─ TIMEOUT
       └─ except: RAISE ← NEW (don't continue)
       └─ TRANSACTION ROLLBACK
       └─ webhook fails
       └─ Stripe retries
       └─ Dead-letter queue created ← NEW
  RESULT: Webhook fails safely, no orphaned subscription, can retry later
```

---

### Scenario 3: Network Partition During INSERT

```
BEFORE FIX:
  upsert sub_new
  update user (plan = pro, stripe_subscription_id = sub_new)
  └─ Network connection lost mid-update
  RESULT: Subscription created but User.stripe_subscription_id = sub_old
          Next webhook for sub_old won't recognize it's invalid

AFTER PARTIAL FIX:
  Same problem exists (no transaction)
  But database constraint would catch most duplicates

AFTER FULL FIX:
  START TRANSACTION
    ├─ cancel sub_old
    ├─ upsert sub_new
    ├─ update user
    └─ COMMIT
  └─ If network fails mid-commit: entire transaction rolled back
  └─ Subscription unchanged, safe to retry
  RESULT: Atomicity guaranteed
```

---

## 🎯 Root Cause → Fix Mapping

| Root Cause | Affected Component | Before Fix | Partial Fix (Current) | Full Fix |
|-----------|-------------------|-----------|----------------------|----------|
| **Double-click** | Frontend | No protection | Rate limit (3/min) | Rate limit + debounce + button disabled |
| **Duplicate sessions** | Stripe Integration | No deduplication | Unique constraint catches later | Idempotency key prevents creation |
| **Cancel failure silent** | Backend Handler | Continues anyway ← BUG | Still continues ← BUG | Raises exception ← FIXED |
| **No database constraint** | Database | Multiple active allowed | Unique index (active only) ← FIXED | Same (sufficient) |
| **No atomicity** | Database Transaction | Partial writes possible | No transaction (risk remains) | Full ACID transaction |
| **Concurrent upgrades** | Mutual Exclusion | No lock | Rate limit weak | User-level lock |
| **No visibility** | Observability | Silent failures | Canary alert ← FIXED | Same + dead-letter queue |

---

## 🔄 Recovery Flow: Remediation Script

```
Ops discovers: duplicate_sub_detected log
  │
  ├─ python scripts/remediate_duplicate_subscriptions.py --dry-run
  │  ├─ Find affected users:
  │  │  └─ SELECT user_id, COUNT(*) WHERE status='active' GROUP BY user_id HAVING COUNT > 1
  │  │
  │  ├─ For each user:
  │  │  ├─ Identify: keep = most recent active subscription
  │  │  ├─ Identify: cancel = all others
  │  │  └─ Print summary (no changes)
  │  │
  │  └─ Report: "X users affected, Y duplicates found"
  │
  ├─ Review report
  │  └─ "Looks correct, ready to execute"
  │
  ├─ python scripts/remediate_duplicate_subscriptions.py --execute --refund
  │  ├─ For each to_cancel:
  │  │  ├─ Check Stripe status (idempotent)
  │  │  ├─ IF active: call subscriptions.cancel_async()
  │  │  ├─ Update local DB: status = canceled
  │  │  ├─ IF --refund: calculate unused days, emit refund
  │  │  └─ Log: CANCELED + REFUNDED
  │  │
  │  └─ COMMIT transaction to DB
  │
  ├─ Verify:
  │  ├─ Stripe dashboard: verify subscriptions canceled
  │  ├─ Database: verify status = canceled, active_count = 1 per user
  │  ├─ Refunds dashboard: verify refunds processed
  │  └─ Email customers: explain issue + refund applied
  │
  └─ ✓ Resolved
```

---

## 📋 Summary: What Each Fix Addresses

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 0: Frontend (User Interaction)                        │
├─────────────────────────────────────────────────────────────┤
│ Before:  No protection vs double-click                      │
│ Current: Rate limit (3/min)                                 │
│ Full:    Rate limit + debounce + button disabled ✓          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ LAYER 1: API (Request Deduplication)                        │
├─────────────────────────────────────────────────────────────┤
│ Before:  No deduplication                                   │
│ Current: Same (gap)                                         │
│ Full:    Idempotency key + inflight check ✓                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ LAYER 2: Backend (Business Logic)                           │
├─────────────────────────────────────────────────────────────┤
│ Before:  Silent error, continue on cancel fail              │
│ Current: Same (gap) + observability canary                  │
│ Full:    Raise exception, transaction rollback ✓            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ LAYER 3: Database (Schema Enforcement)                      │
├─────────────────────────────────────────────────────────────┤
│ Before:  No constraints, duplicates allowed                 │
│ Current: Unique partial index (active only) ✓               │
│ Full:    Same (sufficient)                                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ LAYER 4: Observability & Recovery                           │
├─────────────────────────────────────────────────────────────┤
│ Before:  No visibility                                      │
│ Current: Duplicate detection logging, remediation script ✓  │
│ Full:    + Dead-letter queue, audit table ✓                │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏁 Conclusion

The **partial hardening applied** (commits 8a47f1e → 64ec1ad) prevents duplicates in most scenarios via:
- Database constraint (prevents INSERT of second active)
- Rate limiting (prevents rapid double-clicks)
- Observability (alerts ops)

**However, the core issue remains**: If `cancel_async()` fails, the webhook continues and encounters the constraint violation, leaving the webhook in a failed state.

The **full fix** requires raising an exception when cancel fails, allowing the webhook to fail cleanly and Stripe to retry.
