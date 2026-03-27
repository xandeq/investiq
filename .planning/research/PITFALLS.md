# Pitfalls Research

**Domain:** Investment portfolio SaaS — Brazilian market (v1.1 additions: screeners, renda fixa catalog, allocation simulator, AI wizard)
**Researched:** 2026-03-21
**Confidence:** HIGH (technical) / MEDIUM (CVM regulatory specifics)

## Critical Pitfalls

### Pitfall 1: Tesouro Direto Unofficial JSON API Is Dead

**What goes wrong:**
Code targeting `tesourodireto.com.br/json/.../treasurybondsinfo.json` silently returns 404 (blocked by Cloudflare since August 15, 2025). Any feature depending on this endpoint ships broken.

**Why it happens:**
The unofficial endpoint was widely documented in tutorials and open-source projects but was never official. It was silently killed.

**How to avoid:**
Use ANBIMA official API (`api.anbima.com.br/feed/precos-indices/v1/titulos-publicos/difusao-taxas`) — free developer registration required. Fallback: Tesouro Transparente CKAN CSV downloads (zero auth, batch-only, daily). Do NOT assume any unofficial JSON endpoint is stable.

**Warning signs:**
HTTP 404 or Cloudflare block page response from any `tesourodireto.com.br/json/` path.

**Phase to address:**
v1.1 Phase 1 (infrastructure) — choose data source before building any Tesouro feature.

---

### Pitfall 2: CDB/LCI/LCA "Live Rates" Don't Exist as a Free API

**What goes wrong:**
Claiming "taxas ao vivo" for CDB/LCI/LCA without a commercial data partnership is inaccurate. Open Finance Brasil APIs expose *user positions*, not product catalogs. No free API provides current bank-specific rates.

**Why it happens:**
Developers assume bank rates are as accessible as stock prices. They are not — banks don't publish structured rate data publicly.

**How to avoid:**
Design the `fixed_income_catalog` table as reference rates anchored to CDI/IPCA/SELIC (e.g., "CDB typical: CDI + 0.5% to CDI + 1.2%"). Use python-bcb (already deployed) for live CDI/SELIC. Be transparent in UI: "taxas de referência de mercado" not "oferta ao vivo".

**Warning signs:**
Any plan to "scrape" bank websites for rates — extremely fragile and likely ToS violation.

**Phase to address:**
v1.1 Phase 1 — define catalog model and copy/disclosure language before building the UI.

---

### Pitfall 3: Full-Universe B3 Screener Will Immediately Hit Rate Limits on Per-Request Fetches

**What goes wrong:**
Fetching fundamentals for 400+ B3 tickers on each screener user request hits brapi.dev rate limits in seconds, and produces unacceptable latency (>10s per request).

**Why it happens:**
The existing architecture is optimized for per-user portfolio queries (10-50 tickers). A universe screener is a fundamentally different query pattern.

**How to avoid:**
Build a `screener_snapshot` PostgreSQL table populated by a nightly Celery beat task. All screener API requests query the local snapshot — zero external API calls per user. The nightly rebuild fetches fundamentals in batches with delays. Monitor brapi.dev response on first production run.

**Warning signs:**
Any screener endpoint that calls `brapi_client.fetch_fundamentals()` inside a request handler (not a Celery task).

**Phase to address:**
v1.1 Phase 1 — screener data pipeline must exist and be tested before the screener UI can serve real data.

---

### Pitfall 4: AI Wizard Naming Specific Tickers Violates CVM Suitability Rules

**What goes wrong:**
A wizard that outputs "buy KNRI11 and PETR4" triggers CVM Resolução 30/2021 suitability analysis requirements. CVM's 2026 agenda explicitly targets AI-driven investment recommendation processes.

**Why it happens:**
The line between "analysis" and "recommendation" is easy to cross unintentionally in AI prompts.

**How to avoid:**
Wizard must output asset class percentages only (e.g., "40% ações, 30% FIIs, 30% renda fixa") — never specific tickers. Every wizard screen must display the CVM disclaimer: "Análise informativa — não constitui recomendação de investimento (CVM Res. 19/2021)". Define compliant prompt templates in Phase 1, verify in Phase 2 acceptance criteria.

**Warning signs:**
AI prompt that includes "recomende quais ativos comprar" or any prompt asking for specific ticker suggestions.

**Phase to address:**
v1.1 Phase 1 (define output format) + all wizard phases (enforce disclaimer).

---

### Pitfall 5: Allocation Simulator Without IR Regressivo Is Actively Misleading

**What goes wrong:**
A simulator showing flat rate returns for renda fixa without modeling the IR regressivo table shows inflated returns for short-hold periods (22.5% → 15% regressive schedule based on holding days). LCI/LCA is 0% for PF. FII distributions are 0% (Lei 11.033/2004). Getting this wrong misleads users into wrong allocation decisions.

**Why it happens:**
The IR regressivo rules are complex and easy to simplify away as "just IR 15%".

**How to avoid:**
Implement a `TaxEngine` class with the full 4-tier IR table (22.5% ≤180d, 20% 181-360d, 17.5% 361-720d, 15% >720d) and asset-class exemptions (LCI/LCA = 0%, FII distributions = 0%, ações ≤ R$20k/month = 0%). Store rates as DB config, not hardcoded constants — the 2026 LCI/LCA reform (5% proposed rate) may change this.

**Warning signs:**
Any simulation result showing LCI/LCA and CDB with the same net return. Any code using `ir_rate = 0.15` as a constant without checking asset class and holding period.

**Phase to address:**
v1.1 renda fixa comparison phase — non-negotiable for first release of simulator.

---

### Pitfall 6: Redis Namespace Collision With Existing market:* Schema

**What goes wrong:**
New v1.1 features adding Redis keys like `market:fundamentals:{TICKER}` with a different update cadence or data source than existing `market:*` keys causes stale data or wrong cache invalidation.

**Why it happens:**
The existing Redis schema uses `market:` prefix for portfolio-specific data. Adding screener data to the same namespace without coordination corrupts cache behavior.

**How to avoid:**
Define explicit Redis namespaces before writing any v1.1 cache code:
- `screener:universe:{TICKER}` — daily screener snapshot (different cadence from per-user market data)
- `tesouro:rates:{TYPE}` — Tesouro Direto rates (daily cadence)
- `fii:metadata:{TICKER}` — CVM-sourced FII segment/vacancy (weekly cadence)

**Warning signs:**
Any v1.1 Redis key using `market:` prefix for screener or catalog data.

**Phase to address:**
v1.1 Phase 1 — define Redis namespace schema before any cache code is written.

---

### Pitfall 7: FII P/VP Applied as Universal Threshold Produces Wrong Screener Results

**What goes wrong:**
Tijolo FIIs (real estate) and Papel FIIs (CRI/CRA) have completely different P/VP benchmarks. A P/VP < 1.0 filter that makes sense for Tijolo is meaningless or misleading for Papel FIIs.

**Why it happens:**
P/VP is the most common FII screener filter and is applied uniformly without segment context.

**How to avoid:**
The `fii_metadata` table must include FII segment (Tijolo/Papel/Híbrido/FoF/Agro) from CVM Open Data from day one. Screener UI must display segment and allow filtering by segment before applying P/VP thresholds.

**Warning signs:**
Any screener UI that applies P/VP < X filter without a segment context column visible.

**Phase to address:**
v1.1 FII screener phase — segment must be in the snapshot from the first version.

---

## Open Questions

- **LCI/LCA IR exemption 2026 reform** — Government proposal to tax PF at 5% is pending. The `TaxEngine` must store IR rates as DB config (not constants).
- **brapi.dev rate limits under universe rebuild** — ~900 tickers × 1 req/day. Monitor throttling on first production run; implement exponential backoff with jitter in the Celery task.
- **ANBIMA API auth model** — Check `developers.anbima.com.br` before building Tesouro Direto integration. If OAuth2 client credentials, add `authlib==1.3.x`.
- **Fintz API pricing** — Verify at fintz.com.br before committing as Tesouro fallback.

---
*Research completed: 2026-03-21*
*Scope: v1.1 additions only — see v1.0 SUMMARY.md for foundation pitfalls*
