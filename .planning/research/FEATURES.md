# Feature Research

**Domain:** Investment portfolio SaaS — Brazilian market v1.1 (screeners, renda fixa catalog, allocation simulator, AI wizard)
**Researched:** 2026-03-21
**Confidence:** MEDIUM-HIGH

## Executive Summary

InvestIQ v1.1's competitive advantage is NOT broader screeners — StatusInvest already has those. The moat is **portfolio integration**: showing the user what to buy *given what they already own*. The "Onde Investir" wizard (AI-powered allocation from real portfolio context) is genuinely unoccupied territory. No competitor offers this. Build for integration, not raw screener parity.

## Feature Categories

### Screener de Ações

**Table stakes (every competitor has this):**
- Filter by DY (dividend yield), P/L (P/E ratio), P/VP (P/B ratio), EV/EBITDA
- Filter by sector/segmento B3
- Filter by liquidez média (average daily volume)
- Filter by market cap (small/mid/large cap)
- Sort by any column, paginate results
- Results table with ticker, nome, preço, variação

**Differentiators (InvestIQ advantage):**
- "Ativos que não tenho" toggle — filter universe by tickers not in user's portfolio
- Destaque para ativos complementares à carteira atual (baixa correlação)
- Screener salvo como watchlist (reutilizável)

**Anti-features (don't build for v1.1):**
- Backtesting screener results — high complexity, misleads users
- Social screening (top picks by other users) — regulatory risk + out of scope
- Real-time screener (sub-second) — brapi.dev delay 15min; consistency with portfolio data

**Complexity:** Medium. The data pipeline (nightly `screener_snapshots` rebuild) is the hardest part. The filter UI is a standard table.

**Depends on:** `screener_snapshots` Celery task (new), no dependency on user portfolio for basic screener.

---

### Screener de FIIs

**Table stakes:**
- Filter by P/VP, DY (dividend yield mensal/anual), liquidez diária
- Filter by segmento (Tijolo, Papel, Híbrido, FoF, Agro)
- Filter by número de cotistas (proxy for liquidity/stability)
- Vacância financeira (where available)
- Results table with ticker, nome, segmento, cotação, variação

**Differentiators:**
- Same "ativos que não tenho" toggle as ações screener
- Comparação DY vs CDI (FII rendering CDI+ return vs renda fixa alternative)
- Segment-aware P/VP benchmark (Tijolo < 1.0 = desconto; Papel different benchmark)

**Anti-features:**
- Análise qualitativa dos imóveis no fundo — requires proprietary data
- Vacância física (different from financeira) — rarely available via public APIs

**Complexity:** Medium-High. FII metadata (vacância, segmento) requires CVM Open Data ingestion — new Celery task downloading monthly informes periódicos CSV.

**Depends on:** `fii_metadata` CVM ingestion task (new), `screener_snapshots` for price/DY.

---

### Catálogo de Renda Fixa

**Table stakes:**
- Tesouro Direto: SELIC, IPCA+, IPCA+ com Juros Semestrais, Prefixado — com taxa, vencimento, preço unitário
- CDB/LCI/LCA: faixas de referência de mercado (não oferta ao vivo — sem API pública)
- Indicadores de referência ao vivo: CDI, SELIC, IPCA (já deployed via python-bcb)
- IR regressivo por prazo (22.5% ≤180d → 15% >720d); isenções (LCI/LCA PF = 0%)

**Differentiators:**
- Cálculo de retorno líquido IR por prazo ajustado (nenhum concorrente apresenta isso claramente)
- Link para comparadores especializados (Yubb, Renda Fixa BR) para taxas ao vivo de emissores

**Anti-features:**
- Taxas ao vivo por emissor (banco por banco) — sem API pública; scraping = ToS violation
- Liquidez diária de CDB específico — requer parceria comercial

**Complexity:** Low-Medium. Tesouro via Tesouro Transparente CSV (Celery daily). CDB/LCI/LCA = curated reference rates table (admin-maintained, rare updates). All IR math is static rules.

**Data model note:** `TaxEngine` must store IR rates as DB config — LCI/LCA exemption reform (lei 15.270/25) pending.

---

### Comparação Renda Fixa vs Renda Variável

**Table stakes:**
- Comparação retorno líquido IR: CDB vs LCA vs Tesouro SELIC vs IBOVESPA histórico
- Tabela por prazo (6m, 1a, 2a, 5a) mostrando retorno real (descontado IPCA) e nominal
- Rentabilidade histórica IBOVESPA e CDI já disponíveis via v1.0 infrastructure

**Differentiators:**
- Integração com carteira atual: "seu portfólio rendeu X% — equivalente a CDB de Y% ao ano"
- Cenários: conservador (Tesouro SELIC) / moderado (50/50) / arrojado (ações)

**Anti-features:**
- Projeção de rentabilidade futura de ações — especulativo, CVM risk
- Comparação com produtos específicos de banco — sem dados ao vivo

**Complexity:** Low. Pure calculation using data already deployed (python-bcb + brapi.dev historical prices).

---

### Simulador de Alocação

**Table stakes:**
- Input: R$X disponível para investir + prazo + perfil (conservador/moderado/arrojado)
- Output: mix percentual por classe (ações, FIIs, renda fixa, caixa)
- Projeção de rentabilidade esperada e volatilidade por mix
- IR regressivo aplicado por classe no resultado final

**Differentiators:**
- Considera carteira atual (rebalanceamento vs nova posição)
- Sugestão de alocação incremental ("dado que você já tem 60% em ações, invista mais em RF")
- Três cenários por mix (pessimista/base/otimista)

**Anti-features:**
- Otimização por Modern Portfolio Theory (Markowitz) — requires covariance matrix, much higher complexity
- Backtesting de estratégia de alocação — fora de escopo

**Complexity:** Medium. All backend math (IR, projections). Frontend is a simple form + results card. No Celery needed — synchronous computation < 500ms.

---

### Wizard "Onde Investir"

**Table stakes (for basic viability):**
- Input: valor disponível → perfil → prazo
- AI output: alocação recomendada em percentuais por classe (never specific tickers — CVM risk)
- CVM disclaimer BEFORE output is displayed (not after)
- Mandatory: "análise informativa, não recomendação de investimento (CVM Res. 19/2021)"

**Differentiators (the actual moat):**
- Lê carteira atual do usuário e considera o que já tem
- Compara carteira atual vs alocação ideal sugerida ("você está com 70% em ações, ideal seria 50%")
- Sugere TIPO de ativo por classe (ex: "para FIIs, priorize Tijolo de alta liquidez > R$1M/dia")
- Contexto macro integrado (SELIC atual, tendência de juros) informa a sugestão

**Anti-features:**
- Tickers específicos na output de IA — viola CVM Res. 30/2021 (suitability)
- Chat livre de perguntas sobre investimentos — escopo maior, fase futura

**Complexity:** High. Aggregates context from portfolio + screener top-10 + macro data + Tesouro rates into ~8-12KB LLM prompt. Async pattern (202 + polling), same as existing Goldman Screener. Depends on ALL other v1.1 features.

**CVM note:** Output MUST be asset class percentages only, never tickers. Pre-output disclaimer is mandatory.

---

## Competitor Gap Analysis

| Feature | StatusInvest | Kinvo | Gorila | InvestIQ v1.1 |
|---------|-------------|-------|--------|---------------|
| Screener ações (filtros básicos) | ✓ | ✗ | ✗ | ✓ (com integração carteira) |
| Screener FIIs | ✓ | ✗ | ✗ | ✓ (segmento-aware) |
| Tesouro Direto taxas | ✓ | ✓ | ✓ | ✓ |
| CDB/LCI/LCA catálogo | Parcial | Parcial | ✗ | Referência + link |
| Comparação RF vs RV | Parcial | ✗ | ✗ | ✓ (IR-adjusted) |
| Simulador de alocação | ✗ | ✗ | ✗ | ✓ (primeira plataforma) |
| Wizard IA com carteira real | ✗ | ✗ | ✗ | ✓ (diferencial único) |

## Recommended Build Order (v1.1 internal)

1. `screener_snapshots` data pipeline + screener ações endpoint
2. `fii_metadata` CVM ingestion + screener FIIs endpoint
3. Tesouro Direto catalog + renda fixa catalog endpoint
4. Comparador RF vs RV
5. Simulador de alocação
6. Wizard "Onde Investir" (depends on 1-5)

Steps 1-3 can start in parallel. Steps 4-5 depend on step 3. Step 6 depends on all.

---
*Research completed: 2026-03-21*
*Scope: v1.1 additions only*
