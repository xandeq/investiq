# Deferred Items — Phase 20 Swing Trade Page

Items discovered during execution that are out of scope for this plan.

## Pre-existing TypeScript error (not introduced by 20-02)

**File:** `frontend/src/features/watchlist/components/WatchlistContent.tsx:84`
**Error:**
```
error TS2322: Type 'string | null' is not assignable to type 'number | null | undefined'.
  Type 'string' is not assignable to type 'number'.
```

**Discovered during:** Task 20-02-07 `npx tsc --noEmit` verification run.
**Status:** Pre-existing — not caused by any changes in Phase 20 Plan 02.
The watchlist feature is untouched by this plan. Left as-is per scope
boundary rules ("only auto-fix issues DIRECTLY caused by the current task's
changes"). Should be fixed in a dedicated watchlist cleanup plan.
