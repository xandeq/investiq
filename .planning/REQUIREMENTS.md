# Requirements: InvestIQ v1.6 — Comparador RF vs RV

**Defined:** 2026-04-18
**Core Value:** O usuário controla toda sua carteira em um lugar só, com análise financeira de nível institucional integrada — sem precisar de planilha, sem abrir mil plataformas.

## v1.4 Requirements (Complete)

### Screener de Ações

- [x] **SCRA-01**: Usuário pode ver tabela de ações com colunas Ticker, Nome, Setor, Preço Atual, Variação 12m%, DY 12m, P/L e Market Cap — ordenável por qualquer coluna
- [x] **SCRA-02**: Usuário pode filtrar ações por DY mínimo (slider), P/L máximo (input), Setor B3 (dropdown) e Market Cap (small/mid/large cap)
- [x] **SCRA-03**: Usuário clica em qualquer ticker da tabela e é levado para `/stock/[ticker]` (página de análise completa já existente)
- [x] **SCRA-04**: Tabela suporta paginação

### Catálogo Renda Fixa

- [x] **RF-01**: Usuário pode ver catálogo com Tesouro Direto, CDB, LCI/LCA agrupados por tipo, mostrando taxa, vencimento e valor mínimo de aplicação
- [x] **RF-02**: Cada produto exibe retorno líquido IR por prazo (90d, 1a, 2a, 5a) calculado via TaxEngine — LCI/LCA têm destaque visual de isenção IR
- [x] **RF-03**: Usuário pode filtrar catálogo por tipo e prazo mínimo, ordenar por retorno líquido, e ver indicador visual se produto bate CDI/IPCA no prazo

## v1.6 Requirements

### Comparador RF vs RV

- [ ] **COMP-01**: Usuário informa valor, prazo e produto RF (CDB/LCI/LCA/Tesouro Direto) e vê tabela comparativa de retorno líquido nominal do produto vs benchmarks CDI, SELIC e IPCA+ no prazo selecionado — IR regressivo calculado via TaxEngine, dados macro do Redis
- [ ] **COMP-02**: Tabela comparativa inclui coluna de rentabilidade real (retorno nominal descontado IPCA) para cada alternativa, e gráfico de evolução do patrimônio acumulado ao longo do prazo

## Future Requirements (Deferred)

### Simulador de Alocação (v1.7)

- **SIM-01**: Usuário informa valor a investir e recebe 3 cenários de alocação (conservador/moderado/arrojado)
- **SIM-02**: Simulador mostra delta entre cenário sugerido e carteira atual
- **SIM-03**: Usuário pode ajustar parâmetros do cenário (prazo, tolerância a risco)

### Outros

- **MON-04**: Admin dashboard (assinantes, status Stripe, churn)
- **AUTH-05**: PostgreSQL RLS enforcement no nível DB

## Out of Scope (v1.6)

| Feature | Reason |
|---------|--------|
| Comparação com carteira real do usuário | Standalone tool — usuário define inputs sem precisar ter portfólio cadastrado |
| Simulador de alocação | Milestone próprio — v1.7 |
| Rating de risco do emissor CDB | Sem API pública confiável para ratings em tempo real |
| Comparação com IBOVESPA histórico | Sem feed histórico de índice disponível — CDI/SELIC/IPCA são suficientes como benchmark |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCRA-01 | Phase 21 | Complete |
| SCRA-02 | Phase 21 | Complete |
| SCRA-03 | Phase 21 | Complete |
| SCRA-04 | Phase 21 | Complete |
| RF-01 | Phase 22 | Complete |
| RF-02 | Phase 22 | Complete |
| RF-03 | Phase 22 | Complete |
| COMP-01 | Phase TBD | Pending |
| COMP-02 | Phase TBD | Pending |

**Coverage:**
- v1.4 requirements: 7 total — all complete ✓
- v1.6 requirements: 2 total — phases TBD (roadmapper will assign)

---
*Requirements defined: 2026-04-12*
*Last updated: 2026-04-18 — v1.6 COMP-01/02 promoted from deferred; SIM moved to v1.7*
