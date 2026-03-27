---
status: resolved
trigger: "Next.js frontend broken. /dashboard and /portfolio return blank pages with 500 errors on static assets (layout.css, main-app.js, app-pages-internals.js)"
created: 2026-03-14T00:00:00Z
updated: 2026-03-14T00:10:00Z
---

## Current Focus

hypothesis: CONFIRMED — two separate root causes found and fixed
test: npm run build passes clean, dev server starts without errors, /dashboard redirects to /login correctly
expecting: n/a — resolved
next_action: archive

## Symptoms

expected: /dashboard and /portfolio render correctly
actual: Blank pages with 500 errors on static assets (layout.css, main-app.js, app-pages-internals.js)
errors: 500 errors on layout.css, main-app.js, app-pages-internals.js
reproduction: Navigate to /dashboard or /portfolio
started: Unknown

## Eliminated

- hypothesis: Missing 'use client' directive on chart components
  evidence: All components (AllocationChart, PortfolioChart, BenchmarkChart, DashboardContent, PortfolioContent, MacroIndicators, etc.) already have 'use client' at top
  timestamp: 2026-03-14T00:05:00Z

- hypothesis: SSR-incompatible library imports causing build failure
  evidence: npm run build completes successfully with zero errors
  timestamp: 2026-03-14T00:05:00Z

- hypothesis: Server component using React hooks
  evidence: All hooks (useQuery, useState, useEffect) are in files with 'use client'
  timestamp: 2026-03-14T00:05:00Z

## Evidence

- timestamp: 2026-03-14T00:03:00Z
  checked: npm run build output
  found: Build succeeds cleanly — 11 static pages generated, 0 errors
  implication: No SSR/client directive issues; problem is runtime not build-time

- timestamp: 2026-03-14T00:04:00Z
  checked: Port 3000 — what's running there
  found: A DIFFERENT project (DIAX CRM crm-web at C:\Users\acq20\Desktop\Trabalho\...\crm-web) was serving 500 errors on port 3000. The financas frontend was NOT running at all.
  implication: The 500 errors reported were from an unrelated project occupying port 3000

- timestamp: 2026-03-14T00:06:00Z
  checked: frontend/src/lib/api-client.ts
  found: api-client constructed absolute URLs using NEXT_PUBLIC_API_URL (e.g. http://backend:8000/dashboard/summary). In Docker, NEXT_PUBLIC_API_URL=http://backend:8000 gets baked into the browser bundle — the browser then tries to fetch an internal Docker hostname which is unreachable.
  implication: All API calls fail silently in browser when running in Docker

- timestamp: 2026-03-14T00:07:00Z
  checked: next.config.ts rewrite rule
  found: Rewrite rule proxies /api/:path* → backend. The api-client was NOT using /api prefix — it was calling paths like /dashboard/summary directly, bypassing the proxy entirely.
  implication: Fix is to route all calls through /api prefix so Next.js proxy handles backend routing

- timestamp: 2026-03-14T00:08:00Z
  checked: financas frontend dev server on port 3200
  found: Server starts clean, /dashboard returns 307 redirect to /login (correct middleware auth behavior)
  implication: Frontend itself is healthy — only issue was api-client URL construction

## Resolution

root_cause: |
  TWO ISSUES:
  1. The 500 errors on static assets were from a DIFFERENT Next.js project (DIAX CRM) that was already running on port 3000. The financas frontend was not started at all.
  2. The api-client.ts was constructing absolute URLs (http://backend:8000/...) which get baked into the browser JS bundle via NEXT_PUBLIC_API_URL. In Docker, 'backend' is only resolvable inside the Docker network — the browser cannot reach it. The Next.js rewrite proxy at /api/:path* existed to solve exactly this, but api-client was bypassing it by calling paths without the /api prefix.

fix: |
  Fixed frontend/src/lib/api-client.ts to route all API calls through the Next.js rewrite proxy.
  Changed: const API_BASE = process.env.NEXT_PUBLIC_API_URL → const API_PREFIX = "/api"
  All fetch calls now use relative /api/... URLs which the Next.js rewrite forwards server-side to the backend.

verification: |
  - npm run build: passes clean (11/11 pages generated, 0 errors)
  - Dev server: starts without errors, /dashboard returns 307 to /login (correct auth middleware behavior)
  - All components already had 'use client' — no SSR issues found

files_changed:
  - frontend/src/lib/api-client.ts
