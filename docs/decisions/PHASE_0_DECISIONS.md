# Fase 0 — Decisões Consolidadas D1–D8

**Date:** 2026-04-19 (criado após calibragem pós-ciclo)
**Source:** `docs/audit/PHASE_0_AUDIT.md`, `docs/adr/ADR-001-stack-freeze.md`, `docs/reconciliation/TIER_MATRIX.md`
**Purpose:** Fonte única de verdade das 8 decisões travadas na Fase 0. Referenciado por ADR-001 linha 18, `.github/ISSUE_TEMPLATE/phase_ticket.md`, e todo PR de feature nova.

> Toda decisão aqui listada é **imutável** para as Fases 1–4. Reabrir exige novo ADR ou PRD com justificativa explícita.

---

## D1 — Stack sem Django; FastAPI puro

**Decisão:** Backend é FastAPI + SQLAlchemy 2.x async + Alembic. Sem Django, sem Django ORM, sem DRF.

**Evidência:** `grep -rn "django" backend/app/` → zero hits. `backend/app/main.py:53` — `app = FastAPI(...)`. ADR-001 §Decisão.

**Implicação:** Nenhum middleware Django pode ser adicionado. Se surgir necessidade de admin CRUD, usar FastAPI-Admin ou equivalente — não Django admin.

**Status:** ✅ Confirmado (validação 2026-04-19)

---

## D2 — ANBIMA existe como fonte primária do Tesouro Direto

**Decisão:** ANBIMA **é** a fonte primária OAuth2 para taxas do Tesouro Direto. CKAN CSV (dados.gov.br) é fallback automático se ANBIMA falhar.

**Histórico:** Audit original (D2 inicial) afirmava "ANBIMA não existe no repo". Premissa estava **errada** — corrigida na validação de 2026-04-19.

**Evidência:** `backend/app/modules/market_universe/tasks.py:621` — docstring literal: *"Primary source: ANBIMA API (OAuth2). Fallback source: CKAN CSV (public, 13MB, filtered to today)"*. Funções `_fetch_tesouro_from_anbima()` (linha 494) e `_fetch_tesouro_from_ckan()` (linha 534).

**Implicação:** Não há débito técnico de scraping HTML para Tesouro. Integração oficial já em prod. Roadmap V2 não precisa de tarefa "migrar para fonte oficial".

**Status:** ✅ Confirmado + premissa corrigida (2026-04-19)

---

## D3 — v1.5 (Phases 23–26) e v1.7 (Phase 28) já em produção

**Decisão:** Portfolio Health Check, AI Advisor, Smart Screener, Entry Signals, Comparador RF×RV e Simulador de Alocação são **Existente** no codebase — não "em planejamento" como V2 §5 assumia.

**Evidência:**
- `/advisor/health` → `backend/app/modules/advisor/router.py`
- `/advisor/inbox` → `backend/app/modules/advisor/router.py`
- `/screener/acoes`, `/screener/fiis` → `backend/app/modules/screener_v2/router.py`
- `/renda-fixa/catalog`, `/renda-fixa/tesouro` → `backend/app/modules/screener_v2/router.py`
- `/comparador/compare` → `backend/app/modules/comparador/router.py`
- `/simulador/simulate` → `backend/app/modules/simulador/router.py`
- `frontend/app/comparador/page.tsx`, `frontend/app/simulador/page.tsx` — rotas ativas

**Implicação:** Fase 1 do V2 não precisa entregar essas capabilities — precisa integrar com o Decision Engine sem quebrá-las.

**Status:** ✅ Confirmado (validação 2026-04-19)

---

## D4 — Outcomes não é greenfield: `swing_trade_operations` + `detected_opportunities` existem

**Decisão:** As tabelas `swing_trade_operations` e `detected_opportunities` são o "outcomes layer" atual. A Fase 6 do V2 unifica ambas em tabela canônica `signals`/`outcomes` — mas não apaga o que existe.

**Evidência:**
- `backend/app/modules/swing_trade/models.py:28` — `__tablename__ = "swing_trade_operations"`
- `backend/app/modules/opportunity_detector/models.py:23` — `__tablename__ = "detected_opportunities"`
- Migration `0023_add_swing_trade_operations.py` + `0022_add_detected_opportunities.py` — ambas existem

**Implicação:** Fase 6 é refactor de consolidação, não feature nova. Dados históricos precisam ser migrados, não recriados.

**Status:** ✅ Confirmado (validação 2026-04-19)

---

## D5 — Frontend não é greenfield: Next.js 15.2.3 App Router em produção

**Decisão:** Frontend está em Next.js 15.2.3 com App Router. Todas as novas páginas seguem o padrão `frontend/app/[rota]/page.tsx`.

**Evidência:** `frontend/package.json` — `"next": "15.2.3"`. ADR-001 linha 41 confirma. Rotas ativas em `frontend/app/` cobrindo dashboard, portfolio, advisor, screener, comparador, simulador, ir-helper, wizard, renda-fixa, swing-trade, watchlist, etc.

**Implicação:** Nenhuma migração de framework frontend nas Fases 1–6. React Server Components e Client Components seguem convenções do App Router.

**Status:** ✅ Confirmado (validação 2026-04-19)

---

## D6 — Sem staging é red flag P1; deploy direto em VPS

**Decisão:** O estado atual (sem staging, sem GitHub Actions, deploy via plink/PuTTY direto em produção) é um **red flag P1** aceito conscientemente para MVP. Corrigir na Fase 2.

**Evidência:** `ls .github/workflows/` → diretório não existe. `.github/ISSUE_TEMPLATE/` existe mas sem pipeline CI.

**Limitação ativa:** Bug descoberto no ciclo de 2026-04-19 — `deploy-backend.sh` só atualizava `financas-backend-1`, deixando worker e beat com código antigo. Fix aplicado no mesmo ciclo. **Sintoma esperado quando não há staging:** bugs de deploy chegam em prod antes de detectar.

**Implicação:** Todo PR de feature nova segue o checklist de 12 gates em `.github/ISSUE_TEMPLATE/phase_ticket.md` — substituto manual do CI até Fase 2.

**Status:** ⚠️ Gap conhecido, não resolvido. Fase 2 priority.

---

## D7 — 12-gate PR template como substituto manual de CI

**Decisão:** Enquanto não há GitHub Actions, todo PR de feature nova usa `.github/ISSUE_TEMPLATE/phase_ticket.md` como checklist obrigatório de 12 gates.

**Evidência:** `.github/ISSUE_TEMPLATE/phase_ticket.md` — 121 linhas, template com 12 checkboxes cobrindo: testes, type check, deploy script, smoke test, evidência prod, rollback plan, etc.

**Implicação:** PR sem todos os 12 gates não é mergeado. Exceção apenas para hotfixes P0 com aprovação explícita do dono (Alexandre Queiroz).

**Status:** ✅ Template existe e em uso (validação 2026-04-19)

---

## D8 — TIER_MATRIX parametrizado; custo LLM/usuário não excede 30% ARPU

**Decisão:** Capacidades Premium obedecem ao teto: custo LLM/usuário/mês ≤ 30% do ARPU. Free tier: custo LLM total ≤ 15% do orçamento bootstrap. Tudo parametrizado em `docs/reconciliation/TIER_MATRIX.md`.

**Evidência:** `docs/reconciliation/TIER_MATRIX.md` — variáveis `PREMIUM_PRICE_BRL`, `PRO_LLM_BUDGET_PER_USER_USD`, `FREE_LLM_BUDGET_PER_USER_USD` documentadas com derivação explícita.

**Preço atual:**
- Premium: **R$ 29,90/mês** (confirmado via `frontend/app/page.tsx` — landing page. TIER_MATRIX tinha 49,90 como placeholder — corrigido 2026-04-19. **Verificar contra Stripe Dashboard antes de Fase 5.**)
- Enterprise: R$ 199,00 (placeholder — não definido em Stripe ainda)

**Budget LLM derivado com preço correto:**
- `PREMIUM_PRICE_USD` = 29,90 / 5,00 = **R$ 5,98**
- `PRO_LLM_BUDGET_PER_USER_USD` = 5,98 × 0,30 = **$1,79/usuário/mês**
- ⚠️ **Teto menor que o calculado originalmente** (era $3,00 com 49,90). Capabilities premium precisam caber em $1,79/usuário — revisar TIER_MATRIX completa antes de Fase 5.

**Implicação:** Nenhuma capability Premium pode ser adicionada sem evidência de custo LLM dentro do teto D8. Instrumentação `analysis_cost_logs` por `tenant_id` é pré-requisito de Fase 1.

**Status:** ⚠️ Preço corrigido; teto de custo LLM precisa ser recalculado em TIER_MATRIX antes de Fase 5.

---

## D9 — Estratégia de custo LLM definida em ADR-003

**Decisão:** Caps mensais por tier (Free $0.15, Premium $1.79), degradação de modelo por tier (free pool → Haiku → Opus), cache Redis por análise fundamentalista (TTL 6h, chave `llm_cache:{capability}:{ticker_or_hash}:{date_bucket}`), e kill switch a 120% do cap. Toda lógica de custo centralizada em `backend/app/llm/` — agentes recebem modelo como parâmetro e não instanciam diretamente.

**Evidência:** [`docs/adr/ADR-003-llm-cost-strategy.md`](../adr/ADR-003-llm-cost-strategy.md) — derivado de TIER_MATRIX (D8) validando que sem cache o custo Pro estoura o teto $1.79 em ~1.5×. Soft cap $1.79 (log + alerta), hard cap $2.15 (HTTP 429 com `resets_at`).

**Implicação:** Nenhum agente LLM pode ser adicionado à Fase 1 sem o módulo `backend/app/llm/` implementado. Este módulo é pré-requisito arquitetural da Fase 1 do V2.

**Status:** ✅ Decisão deliberada pré-Fase 1 (2026-04-19)

---

*Criado em 2026-04-19. Última validação: 2026-04-19.*
*Referenciado por: ADR-001 §Premissas, `.github/ISSUE_TEMPLATE/phase_ticket.md`, PHASE_0_AUDIT.md §Próximos passos.*
