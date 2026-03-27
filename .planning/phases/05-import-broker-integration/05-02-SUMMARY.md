---
phase: 05-import-broker-integration
plan: 02
subsystem: ui
tags: [react, nextjs, tanstack-query, typescript, formdata, polling]

# Dependency graph
requires:
  - phase: 05-01
    provides: FastAPI import endpoints — POST /imports/pdf, /imports/csv, GET /imports/jobs/{id}, POST /imports/jobs/{id}/confirm/cancel/reparse, GET /imports/history, GET /imports/template.csv

provides:
  - /imports page (Next.js Server Component) with AppNav navigation
  - UploadDropzone component — PDF + CSV tabs, FormData upload, inline error handling
  - StagingReviewTable component — polls job status every 2s, shows all 5 status states, duplicate badge
  - ImportHistory component — history table with status badges, re-parse button, skeleton loading
  - ImportContent orchestrator — manages activeJobId state between upload -> review -> history
  - imports feature module — types.ts, api.ts, useImportJob, useImportHistory hooks
  - AppNav updated with /imports link

affects:
  - 06-monetization (uses AppNav pattern)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - FormData upload via raw fetch (NOT apiClient — apiClient sets Content-Type: application/json breaking multipart)
    - TanStack Query polling with refetchInterval stop condition on terminal job statuses
    - queryClient.invalidateQueries for cross-component cache invalidation after mutations
    - Status-machine-style rendering in StagingReviewTable (pending/running/failed/completed/confirmed/cancelled)

key-files:
  created:
    - frontend/src/features/imports/types.ts
    - frontend/src/features/imports/api.ts
    - frontend/src/features/imports/hooks/useImportJob.ts
    - frontend/src/features/imports/hooks/useImportHistory.ts
    - frontend/src/features/imports/components/UploadDropzone.tsx
    - frontend/src/features/imports/components/StagingReviewTable.tsx
    - frontend/src/features/imports/components/ImportHistory.tsx
    - frontend/src/features/imports/components/ImportContent.tsx
    - frontend/src/app/imports/page.tsx
  modified:
    - frontend/src/components/AppNav.tsx

key-decisions:
  - "FormData uploads bypass apiClient — raw fetch required to avoid Content-Type: application/json breaking multipart boundary"
  - "useImportJob stops polling on confirmed and cancelled in addition to completed/failed (4 terminal states vs 2 in useAnalysisJob)"
  - "StagingReviewTable handles all 6 ImportJobStatus variants inline — single component, no sub-routes"

patterns-established:
  - "FormData upload pattern: raw fetch with credentials: include, no Content-Type header, error reads detail or error field from JSON"
  - "Polling stop condition: check 4 terminal statuses (completed/failed/confirmed/cancelled) via refetchInterval returning false"
  - "Duplicate badge: bg-yellow-100 text-yellow-800 for is_duplicate=true rows"

requirements-completed:
  - IMP-01
  - IMP-02
  - IMP-03

# Metrics
duration: 4min
completed: 2026-03-15
---

# Phase 5 Plan 02: Import Frontend Summary

**Next.js /imports page with FormData upload dropzone, TanStack Query polling, staged transaction review table with duplicate flagging, confirm/cancel actions, and import history with re-parse button**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-15T19:34:09Z
- **Completed:** 2026-03-15T19:37:51Z
- **Tasks:** 2 of 3 complete (Task 3 is human-verify checkpoint)
- **Files modified:** 10

## Accomplishments
- Built complete imports feature module (types, API wrappers, hooks) wired to 05-01 backend
- UploadDropzone with PDF + CSV tabs, FormData upload (correctly bypasses apiClient), spinner and error states, CSV template download anchor
- StagingReviewTable polling every 2s via useImportJob, handles all 6 job status states, duplicate badge with yellow styling, confirm/cancel mutations with cache invalidation
- ImportHistory with color-coded status badges, re-parse button, skeleton rows, empty state
- AppNav updated with /imports link

## Task Commits

Each task was committed atomically:

1. **Task 1: Types, API functions, polling hook, import history hook** - `68d783f` (feat)
2. **Task 2: Upload dropzone, staging review table, import history, page** - `74a4894` (feat)
3. **Task 3: Human verify checkpoint** - awaiting human verification

## Files Created/Modified
- `frontend/src/features/imports/types.ts` - ImportJob, StagingRow, ImportJobDetail, ConfirmResponse, ImportJobStatus interfaces
- `frontend/src/features/imports/api.ts` - 7 typed fetch wrappers (uploadPdf/Csv raw fetch, others apiClient)
- `frontend/src/features/imports/hooks/useImportJob.ts` - polling hook stops on 4 terminal statuses
- `frontend/src/features/imports/hooks/useImportHistory.ts` - history query, invalidated after mutations
- `frontend/src/features/imports/components/UploadDropzone.tsx` - PDF + CSV tabs, FormData, CSV template link
- `frontend/src/features/imports/components/StagingReviewTable.tsx` - status machine, review table, duplicate badge
- `frontend/src/features/imports/components/ImportHistory.tsx` - history table, re-parse, status badges, skeletons
- `frontend/src/features/imports/components/ImportContent.tsx` - orchestrates activeJobId state
- `frontend/src/app/imports/page.tsx` - Server Component page
- `frontend/src/components/AppNav.tsx` - added /imports nav link

## Decisions Made
- FormData uploads bypass apiClient — apiClient sets `Content-Type: application/json` which breaks multipart boundary; raw fetch required
- useImportJob stops polling on 4 terminal statuses (completed, failed, confirmed, cancelled) vs 2 in useAnalysisJob — import jobs have 2 extra terminal states
- StagingReviewTable handles all status variants in one component — avoids routing complexity, matches status-machine pattern from dashboard

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None — TypeScript reported zero errors on first check.

## User Setup Required
None — no external service configuration required. Uses existing Docker stack from 05-01.

## Next Phase Readiness
- /imports page ready for end-to-end browser verification (Task 3 checkpoint)
- After human approval: phase 05 complete, ready for phase 06 monetization
- Concern: need real broker PDFs (Clear/XP) to validate parser cascade beyond fixture tests

---
*Phase: 05-import-broker-integration*
*Completed: 2026-03-15*
