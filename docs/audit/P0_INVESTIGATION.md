# P0 Investigation — Macro Rates Zeroed + data_stale Persistent

**Investigator**: Claude Code  
**Date**: 2026-04-19  
**Status**: ROOT CAUSE CONFIRMED — ready for Fase 3 (fix)

---

## Fase 1 — Evidências (7 perguntas)

### Q1 — Configuração do `refresh_macro`

| Campo | Valor |
|-------|-------|
| Arquivo | `backend/app/celery_app.py:72-76` |
| Task name | `app.modules.market_data.tasks.refresh_macro` |
| Schedule | `crontab(minute=0, hour="*/6")` — a cada 6 horas |
| Queue | `celery` (padrão, sem fila dedicada) |
| Expires | **não configurado** |

### Q2 — Celery Beat e Worker rodando em prod

```
financas-celery-beat-1    Up 14 hours    (iniciado ~01:00 UTC 2026-04-19)
financas-celery-worker-1  Up 21 hours    (iniciado ~18:30 UTC 2026-04-18)
```

Ambos RUNNING. Beat enviou `refresh-macro-every-6h` às **09:00** e **15:00** hoje.

### Q3 — `refresh_macro` executando sem erro

**ÚLTIMA execução bem-sucedida: 2026-04-05 15:00 UTC** (14 dias atrás).

```
[2026-04-05 15:00:00,216] Task app.modules.market_data.tasks.refresh_macro[defb9702] received
[2026-04-05 15:00:32,991] refresh_macro: wrote SELIC=14.6499 CDI=14.6499 IPCA=0.7000 PTAX=5.1655
[2026-04-05 15:00:33,185] Task ...refresh_macro[defb9702] succeeded in 32.89s: None
```

Hoje (2026-04-19): Beat enfileirou 8 instâncias de `refresh_macro` às 09:00 e 15:00.
**Nenhuma foi recebida ou executada pelo worker.** As tarefas estão presas na fila.

### Q4 — Estado do Redis para chaves macro

```
redis-cli KEYS 'market:macro*'  → (empty)
redis-cli KEYS 'market:quote*'  → (empty)
redis-cli KEYS 'market:*'       → (empty)
redis-cli DBSIZE                → 2278 (todas screener:universe:*)
```

**Chaves `market:macro:*` e `market:quote:*` não existem.** Expiraram após TTL.

### Q5 — TTL configurado no código

| Chave | TTL | Arquivo |
|-------|-----|---------|
| `market:macro:*` | `_MACRO_TTL = 25200` (7h) | `backend/app/modules/market_data/tasks.py` |
| `market:quote:*` | `_QUOTE_TTL = 1200` (20min) | `backend/app/modules/market_data/tasks.py` |

TTLs expirados após 14 dias sem `refresh_macro` e com `refresh_quotes` também presa.

### Q6 — BCB reachable do container

```bash
docker exec financas-backend-1 python -c "import httpx; r = httpx.get('https://api.bcb.gov.br/dados/serie/bcdata.sgs.11/dados/ultimos/1?formato=json', timeout=10); print(r.status_code, r.text[:80])"
# → 200 [{"data":"17/04/2026","valor":"0.054266"}]
```

**BCB responde HTTP 200 com dados válidos.** Não é problema de rede/DNS.

### Q7 — Origem do `data_stale=true` em `/dashboard/summary`

**Arquivo**: `backend/app/modules/dashboard/service.py:83`

```python
data_stale = any(p.current_price_stale for p in positions)
```

`current_price_stale` é definido em `portfolio/service.py:153`:

```python
price_stale = True  # default
if redis_client is not None:
    quote = await mds.get_quote(ticker)  # reads market:quote:{TICKER}
    if not quote.data_stale:
        price_stale = False
```

`get_quote()` retorna `data_stale=True` quando a chave Redis está ausente (`market_data/service.py:63-72`).

**Chain**: sem `market:quote:*` no Redis → `current_price_stale=True` em todas posições → `data_stale=True` no dashboard summary.

Da mesma forma, `get_macro()` (`service.py:115-124`) retorna `selic=0, cdi=0, ipca=0, ptax_usd=0` quando os 4 keys estão ausentes.

---

## Fase 2 — Diagnóstico

### Classificação: **Causa E — Starvation de fila Celery**

**Root cause único para ambos os P0s**: A fila Celery (`celery`) acumula tarefas mais rápido do que o worker consegue processar.

#### Evidência

```
redis-cli LLEN celery → 390 tarefas pendentes
```

Composição da fila:

| Task | Count | Schedule | Por dia |
|------|-------|----------|---------|
| `opportunity_detector.scan_crypto` | 173 | */15min **24/7** | 96 |
| `screener.cleanup_stale_runs` | 171 | */15min **24/7** | 96 |
| `refresh_macro` | 8 | */6h | 4 |
| `refresh_tesouro_rates` | 8 | */6h | 4 |
| `refresh_screener_universe` | 3 | 1×/dia | 1 |
| outros | 27 | — | — |

#### Mecanismo de falha

```
[Worker] refresh_screener_universe em execução
    ↓ brapi.dev retorna 429 para cada ticker
    ↓ retry after 5s, 3 tentativas = ~15s/ticker × centenas de tickers
    ↓ task ocupa worker por 30-120 minutos
    
[Beat] scan_crypto + cleanup_stale_runs adicionam 2 tarefas por minuto (24/7)
    ↓ Workers ocupados com screener não consomem a fila
    ↓ Queue cresce ~2 tasks/min > throughput do worker
    
[Resultado] refresh_macro e refresh_quotes nunca saem da fila
    → market:macro:* e market:quote:* expiram e não são renovados
    → macro API retorna selic=0, cdi=0, ipca=0
    → dashboard summary retorna data_stale=true
```

#### Por que Nenhuma das outras causas se aplica

| Causa | Descartada porque |
|-------|-------------------|
| A — Beat não rodando | Beat está UP, envia `refresh_macro` às 09:00 e 15:00 |
| B — Task falha na execução | Última execução bem-sucedida (Apr 5), BCB responde 200 |
| C — Chave Redis errada | Key schema confirmado em service.py, tarefas históricas escreveram corretamente |
| D — TTL muito curto | TTL 7h é razoável para tarefa 6h; o problema é que a tarefa nunca roda |
| F — Código do endpoint errado | `get_macro()` funciona corretamente; retorna 0 por design quando key ausente |
| G — Problema de rede/DNS | BCB confirma HTTP 200 de dentro do container |

---

## Proposta de Fix (Fase 3)

### Fix imediato (restaurar dados agora)

```bash
# 1. Flush fila acumulada (remove os 390 tasks presos)
docker exec financas-redis-1 redis-cli DEL celery

# 2. Trigger manual de refresh_macro
docker exec financas-celery-worker-1 celery -A app.celery_app.celery call app.modules.market_data.tasks.refresh_macro

# 3. Trigger manual de refresh_quotes
docker exec financas-celery-worker-1 celery -A app.celery_app.celery call app.modules.market_data.tasks.refresh_quotes
```

### Fix root cause (prevenir recorrência)

**Opção R1 — Adicionar `expires` a tarefas periódicas** (mínima invasividade)

Adicionar `expires` em `celery_app.py` para evitar acúmulo:

```python
"opportunity-detector-crypto": {
    "task": "opportunity_detector.scan_crypto",
    "schedule": crontab(minute="*/15"),
    "options": {"expires": 14 * 60},  # descarta se não processado em 14min
},
"cleanup-stale-screener-runs": {
    "task": "screener.cleanup_stale_runs",
    "schedule": crontab(minute="*/15"),
    "options": {"expires": 14 * 60},
},
"refresh-macro-every-6h": {
    "task": "app.modules.market_data.tasks.refresh_macro",
    "schedule": crontab(minute=0, hour="*/6"),
    "options": {"expires": 6 * 60 * 60},  # descarta se não processado antes da próxima
},
```

**Opção R2 — Fila dedicada `critical` para macro/quotes** (mais robusto)

```python
# celery_app.py — task_routes
app.conf.task_routes = {
    "app.modules.market_data.tasks.refresh_macro": {"queue": "critical"},
    "app.modules.market_data.tasks.refresh_quotes": {"queue": "critical"},
}
```

```yaml
# docker-compose.yml — worker command
celery-worker:
  command: celery -A app.celery_app.celery worker -Q critical,celery -c 4
```

**Opção R3 — Limitar `scan_crypto` a horário de mercado ou aumentar intervalo**

```python
"opportunity-detector-crypto": {
    "schedule": crontab(minute="*/30"),  # 30min em vez de 15min — 48/dia vs 96/dia
},
```

### Recomendação

Implementar **R1 + R3** agora (menor risco, sem mudança de infraestrutura).  
Planejar **R2** para o próximo milestone como melhoria arquitetural.

---

## Impacto observado

| Sintoma | Causa direta |
|---------|-------------|
| CDI/IPCA/SELIC = 0 no banner do dashboard | `market:macro:*` ausente → `get_macro()` retorna 0 |
| `data_stale=true` persistente | `market:quote:*` ausente → `current_price_stale=True` em todas posições |
| Ambos presentes desde ~Apr 5 | Último `refresh_macro` bem-sucedido: 2026-04-05 15:00 UTC |
