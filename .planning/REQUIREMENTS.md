# Requirements: InvestIQ v1.4 — Ferramentas de Análise

**Defined:** 2026-04-12
**Core Value:** O usuário controla toda sua carteira em um lugar só, com análise financeira de nível institucional integrada — sem precisar de planilha, sem abrir mil plataformas.

## v1.4 Requirements

### Screener de Ações

- [x] **SCRA-01**: Usuário pode ver tabela de ações com colunas Ticker, Nome, Setor, Preço Atual, Variação 12m%, DY 12m, P/L e Market Cap — ordenável por qualquer coluna
- [x] **SCRA-02**: Usuário pode filtrar ações por DY mínimo (slider), P/L máximo (input), Setor B3 (dropdown) e Market Cap (small/mid/large cap)
- [x] **SCRA-03**: Usuário clica em qualquer ticker da tabela e é levado para `/stock/[ticker]` (página de análise completa já existente)
- [x] **SCRA-04**: Tabela suporta paginação

### Catálogo Renda Fixa

- [ ] **RF-01**: Usuário pode ver catálogo com Tesouro Direto, CDB, LCI/LCA agrupados por tipo, mostrando taxa, vencimento e valor mínimo de aplicação
- [ ] **RF-02**: Cada produto exibe retorno líquido IR por prazo (90d, 1a, 2a, 5a) calculado via TaxEngine — LCI/LCA têm destaque visual de isenção IR
- [ ] **RF-03**: Usuário pode filtrar catálogo por tipo e prazo mínimo, ordenar por retorno líquido, e ver indicador visual se produto bate CDI/IPCA no prazo

## v2 Requirements (Deferred)

### AI Portfolio Advisor (v1.5)

- **ADVI-01**: Usuário vê Portfolio Health Check automático (concentração por setor/tipo, exposição individual, renda passiva projetada, ativos underperforming)
- **ADVI-02**: Usuário recebe recomendações IA personalizadas referenciando ativos que ele tem na carteira
- **ADVI-03**: Smart Screener filtra ativos que complementam a carteira atual do usuário
- **ADVI-04**: Entry Signals com RSI + médias móveis + contexto fundamentalista para cada ativo

### Comparador e Simulador (v1.6)

- **COMP-01**: Usuário compara retorno líquido histórico da RF vs carteira de RV por prazo
- **COMP-02**: Comparador mostra rentabilidade real (descontando inflação)
- **SIM-01**: Usuário informa valor a investir e recebe 3 cenários de alocação (conservador/moderado/arrojado)
- **SIM-02**: Simulador mostra delta entre cenário sugerido e carteira atual
- **SIM-03**: Usuário pode ajustar parâmetros do cenário (prazo, tolerância a risco)

### Outros

- **MON-04**: Admin dashboard (assinantes, status Stripe, churn)
- **AUTH-05**: PostgreSQL RLS enforcement no nível DB

## Out of Scope (v1.4)

| Feature | Reason |
|---------|--------|
| Rating de risco do emissor CDB | Sem API pública confiável para ratings em tempo real |
| Comparador RF vs RV | Depende do catálogo RF — v1.6 |
| Simulador de alocação | Requer advisor layer — v1.5/v1.6 |
| AI Portfolio Advisor | Milestone próprio — v1.5 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCRA-01 | Phase 21 | Complete |
| SCRA-02 | Phase 21 | Complete |
| SCRA-03 | Phase 21 | Complete |
| SCRA-04 | Phase 21 | Complete |
| RF-01 | Phase 22 | Pending |
| RF-02 | Phase 22 | Pending |
| RF-03 | Phase 22 | Pending |

**Coverage:**
- v1.4 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-12*
*Last updated: 2026-04-12 — Traceability assigned by roadmapper (Phase 21: SCRA-01–04, Phase 22: RF-01–03)*
