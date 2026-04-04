# Requirements: InvestIQ v1.3 — FII Screener

**Defined:** 2026-04-04
**Core Value:** O usuário encontra os melhores FIIs para o seu perfil em segundos — ranqueados por score composto, filtráveis por segmento e DY, com página de detalhe e análise IA

## v1.3 Requirements

### FII Screener

- [ ] **SCRF-01**: Usuário pode ver tabela de FIIs ranqueados por score composto calculado a partir de DY 12m, P/VP e liquidez diária
- [ ] **SCRF-02**: Usuário pode filtrar FIIs por segmento (Logística, Lajes Corporativas, Shopping, CRI/CRA, FoF, Híbrido, Residencial)
- [ ] **SCRF-03**: Usuário pode filtrar FIIs por DY mínimo dos últimos 12 meses (slider ou input numérico)
- [ ] **SCRF-04**: Usuário pode ver página de detalhe de um FII (`/fii/[ticker]`) com histórico de DY, P/VP, dados básicos do portfólio e análise IA assíncrona (narrativa sobre qualidade de dividendo, P/VP e sustentabilidade dos proventos)

## v2 Requirements (Deferred)

### FII Screener Avançado

- **SCRF-05**: Usuário pode filtrar FIIs por vacância física máxima
- **SCRF-06**: Usuário pode filtrar FIIs por número mínimo de imóveis no portfólio
- **SCRF-07**: Usuário pode comparar 2-3 FIIs lado a lado

### Screener Ações Avançado

- **SCRA-01**: Usuário pode filtrar screener de ações por DY mínimo
- **SCRA-02**: Usuário pode filtrar screener de ações por P/L máximo
- **SCRA-03**: Usuário pode filtrar screener de ações por setor B3

### Outros

- **RF-01–03**: Catálogo Renda Fixa frontend
- **COMP-01–02**: Comparador RF vs RV
- **SIM-01–03**: Simulador de Alocação
- **MON-04**: Admin Dashboard
- **AUTH-05**: PostgreSQL RLS enforcement

## Out of Scope (v1.3)

| Feature | Reason |
|---------|--------|
| Vacância física em tempo real | Sem API pública confiável — FIIs.community inconsistente; adiar para v1.4+ |
| Comparação multi-FII | Aumenta complexidade sem ser bloqueante para o screener |
| Alertas de DY por FII | Infraestrutura de notificação existe mas escopo não inclui FIIs ainda |
| FII vs benchmark (IFIX) | Útil mas não crítico para o screener inicial |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCRF-01 | Phase 17 | Pending |
| SCRF-02 | Phase 17 | Pending |
| SCRF-03 | Phase 17 | Pending |
| SCRF-04 | Phase 18 | Pending |

**Coverage:**
- v1.3 requirements: 4 total
- Mapped to phases: 4
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-04*
*Last updated: 2026-04-04 after v1.3 milestone start*
