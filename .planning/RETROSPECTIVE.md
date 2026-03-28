# InvestIQ — Retrospective

---

## Milestone: v1.1 — Onde Investir

**Shipped:** 2026-03-28
**Phases:** 2 (7, 11) | **Plans:** 4 | **Commits:** 9 (v1.1 range)

### What Was Built

- Global DB infrastructure: 4 tables + TaxEngine IR regressivo (22.5%→15%) with DB-stored rates
- 3 autonomous Celery beat pipelines: screener universe (~900 tickers), FII metadata, Tesouro rates
- Screener Goldman Sachs deployado e funcional em produção
- Wizard "Onde Investir": backend Celery async + LLM provider + CVM disclaimer + portfolio delta
- WizardContent.tsx: 3-step UX (Valor → Prazo → Perfil), progress indicator, Voltar navigation
- Landing page marketing completa (features, pricing, FAQ, LandingNav sticky + mobile)
- Billing emails transacionais (welcome, payment, failure, cancellation) via Brevo
- Correpy brokerage fee fix: distribuição proporcional vs duplicação por transação

### What Worked

- **docker cp file-by-file approach** — evitou OOM do VPS na hora de copiar módulos grandes
- **paramiko em vez de plink** — resolveu problema de host key + travamento no Windows
- **yolo mode** — sem gates desnecessários em fases bem-definidas
- **Separar `get_global_db` de `get_db`** — evitou complexidade de RLS em dados públicos do screener
- **TaxEngine rates em DB** — design decision certa: reforma LCI/LCA em 2026 não vai precisar de deploy
- **Wizard CVM disclaimer como primeiro filho** — UX correto e compliance-first

### What Was Inefficient

- **Phases 8, 9, 10 planejadas mas nunca executadas** — roadmap foi otimista; screener foi hotfixado, comparador e simulador ficaram de fora
- **VPS instability** — ClearDesk crash loop causou VPS down, postgres/redis stopped, deploy atrasou
- **AWS SM inacessível** — credenciais não tinham fallback local; resolvido agora com .env.local + ~/.secrets
- **Múltiplos formatos de deploy tentados** — tar → docker cp dir → OOM → file-by-file; poderia ir direto para file-by-file
- **STATE.md inconsistente** — marcava 6 phases/19 plans mas só existiam 2 phases v1.1 no disco

### Patterns Established

- **Deploy backend**: sftp put → docker cp file-by-file (nunca docker compose build no VPS)
- **Deploy frontend**: npm run build local → tar pipe SSH → docker cp → docker restart
- **SSH no Windows**: paramiko (não plink — plink trava por host key)
- **Secrets fallback**: .env.local projeto → ~/.secrets → AWS SM (nesta ordem)
- **Migrations**: sempre `docker exec backend alembic upgrade head` (nunca por rebuild)
- **VPS down**: https://hpanel.hostinger.com/vps/961004/overview → Iniciar

### Key Lessons

1. **Não planejar phases que não vai executar** — phases 8/9/10 no ROADMAP criaram ruído; melhor scope menor e entregar
2. **Fallback de secrets é crítico** — AWS SM inacessível é situação normal nesta máquina; sempre ter Plan B local
3. **Global tables != tenant tables** — `get_global_db` vs `get_db` foi boa decisão; replicar pattern em v1.2
4. **CVM disclaimer first** — padrão arquitetural: sempre renderizar disclaimer antes de qualquer output de IA

### Cost Observations

- Sessions: ~3-4 sessões para v1.1
- Fases executadas: 2 (7 e 11) vs 5 planejadas — 40% do plano original
- Bugs fixados no meio do milestone adicionaram ~4 commits extras fora do plano

---

## Cross-Milestone Trends

| Milestone | Phases | Plans | Ratio Planned/Shipped | VPS Issues |
|-----------|--------|-------|-----------------------|------------|
| v1.0 | 6 | ~15 | ~90% | 1 (worker OOM) |
| v1.1 | 5 planned / 2 shipped | 4 | 40% | 3 (ClearDesk, postgres stopped, AWS SM) |

**Trend:** Roadmap otimismo → scope real é ~50-60% do planejado. Considerar escopes menores em v1.2.
