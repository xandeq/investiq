# InvestIQ — Inventário de Funcionalidades

**Visão**: o que a aplicação faz por você hoje, em produção.
**Audiência**: Alexandre (dono do produto).
**Regra**: só funcionalidades vivas. Branch/backlog/código morto não entra.
**Atualizado**: 2026-04-19

---

## Planos disponíveis

| Plano | Preço | Período trial |
|---|---|---|
| **Free** | Grátis | 14 dias com acesso Premium completo no cadastro |
| **Premium** | R$ 29,90/mês | — |

Limites do Free após trial: máx 50 transações na carteira, máx 3 importações por mês, análises de IA bloqueadas, Screener Goldman bloqueado.

---

## 1. Carteira — registro e acompanhamento

### 1.1 Registrar operações

**O que faz?** Você registra compras, vendas, dividendos, JCP e amortizações de qualquer ativo de B3 (ações, FIIs, ETFs, BDRs) e crypto.

**O que facilita?** Uma fonte única da verdade da sua carteira. Sem depender de planilha, sem perder o histórico.

**Onde acessa?** `/portfolio/transactions` — botão "Nova operação" ou via importação de corretora.

**Limitação**: Free limitado a 50 transações totais.

---

### 1.2 Importar notas de corretagem

**O que faz?** Você faz upload de PDF de nota de corretagem, CSV ou arquivo XLSX da Clear. O sistema processa automaticamente, exibe as operações encontradas para revisão e — após você confirmar — insere na sua carteira.

**O que facilita?** Migrar histórico antigo sem redigitar operação por operação. Funciona com os formatos mais comuns do mercado brasileiro.

**Onde acessa?** `/imports`

**Limitação**: Free limitado a 3 uploads por mês.

---

### 1.3 Posições em tempo real

**O que faz?** Lista todas as suas posições atuais com preço de mercado, custo médio, P&L em reais e em percentual, e percentual de alocação na carteira.

**O que facilita?** Você sabe em segundos quanto está ganhando ou perdendo em cada posição — sem abrir o home broker.

**Onde acessa?** `/portfolio`

---

### 1.4 Histórico de dividendos

**O que faz?** Mostra todos os dividendos, JCP e amortizações recebidos no período, com data e valor por ativo.

**O que facilita?** Controlar renda passiva recebida sem precisar consultar extrato de corretora.

**Onde acessa?** `/portfolio` (aba dividendos)

---

## 2. Dashboard — visão consolidada

**O que faz?** Uma tela única com: patrimônio total, variação do dia, alocação por classe de ativo (ações, FIIs, renda fixa, etc.), P&L histórico em gráfico, e indicadores macroeconômicos (SELIC, CDI, IPCA, PTAX).

**O que facilita?** Você abre o app e em 10 segundos sabe onde está o seu patrimônio, como está performando e qual o contexto do mercado.

**Onde acessa?** `/dashboard`

**Limitação**: Macro pode mostrar valores desatualizados se o worker Celery estiver com fila congestionada (normalizado com o fix de 2026-04-19).

---

### 2.1 Histórico do patrimônio

**O que faz?** Gráfico do valor total da carteira ao longo do tempo (1m, 3m, 6m, 1a, ou tudo). Calculado todo dia útil após o fechamento da B3 às 18h30.

**O que facilita?** Ver a trajetória real do patrimônio, não só o saldo do dia.

**Onde acessa?** `/dashboard` — seletor de período no gráfico.

**Limitação**: dependente do Celery Beat — se a fila ficar congestionada (como ocorreu em 2026-04), o snapshot diário pode atrasar. Sem watchdog dedicado ainda (candidato a próximo fix P1 de observabilidade).

---

## 3. Monitoramento automático (funciona sem você pedir)

### 3.1 Alertas de preço na watchlist

**O que faz?** Você adiciona um ativo à watchlist e define um preço-alvo. Quando o ativo chega a ±2% do seu alvo durante o pregão, você recebe um e-mail de alerta automaticamente.

**O que facilita?** Você não precisa ficar olhando o preço. O app vigia por você e avisa na hora certa.

**Onde acessa?** `/watchlist` — adicionar ativo e preencher "Preço-alvo".

---

### 3.2 Alertas de portfólio (Insights)

**O que faz?** Todo dia de manhã o sistema analisa sua carteira e gera alertas automáticos quando detecta: concentração acima de 30% em um único ativo, poucos ativos (menos de 3), carteira 100% em ações sem diversificação, SELIC acima de 12% (aviso de risco de renda variável vs renda fixa), e concentração acima de 70% em uma classe.

**O que facilita?** Você recebe o diagnóstico antes de abrir o app — sem precisar calcular nada.

**Onde acessa?** `/insights` (contador de não-lidos no menu).

---

### 3.3 Digest semanal por e-mail

**O que faz?** Toda segunda-feira de manhã você recebe um e-mail com: patrimônio atual, variação da semana, e os maiores movedores da sua carteira.

**O que facilita?** Acompanhamento passivo — você fica informado mesmo sem abrir o app.

**Como ativar?** `/profile` — ativar "Receber digest semanal".

---

### 3.4 Detector de oportunidades

**O que faz?** Varre automaticamente ações de B3, crypto e renda fixa o dia todo em busca de ativos com desconto técnico ou fundamentalista. As oportunidades encontradas ficam salvas no histórico.

**O que facilita?** Você tem um analista varrendo o mercado o tempo todo, sem custo adicional.

**Onde acessa?** `/opportunity-detector`

**Nota**: Ações varrem a cada 15 min no pregão; crypto a cada 30 min 24/7; renda fixa a cada 6h.

---

## 4. Watchlist

**O que faz?** Lista de ativos que você quer monitorar sem necessariamente ter na carteira. Mostra cotação ao vivo, P&L teórico, DY e P/VP. Permite adicionar notas pessoais e alertas de preço (ver 3.1).

**O que facilita?** Um painel de acompanhamento de ativos do seu radar, separado da carteira real.

**Onde acessa?** `/watchlist`

---

## 5. Análise de ativos

### 5.1 Detalhe de ação

**O que faz?** Exibe indicadores fundamentalistas (P/L, P/VP, DY, EV/EBITDA), gráfico histórico de preço, e botão para disparar análise de IA.

**O que facilita?** Informação essencial sobre qualquer ação de B3 em um único lugar.

**Onde acessa?** `/stock/[TICKER]` (ex: `/stock/ITUB4`)

---

### 5.2 Detalhe de FII

**O que faz?** Exibe DY, P/VP, segmento (logística/shopping/papel/etc.), vacância, número de cotistas, e metadados CVM do fundo. Botão para disparar análise de IA.

**O que facilita?** Informação completa de FII com dados regulatórios (CVM), não só cotação.

**Onde acessa?** `/fii/[TICKER]` (ex: `/fii/MXRF11`)

---

### 5.3 Análises de IA: DCF, valuation, earnings, dividendos, setor *(Premium)*

**O que faz?** Conjunto de análises profundas geradas por IA para qualquer ativo: DCF (fluxo de caixa descontado), qualidade de lucros, sustentabilidade de dividendos, comparação com peers do setor. Resultado disponível em minutos.

**O que facilita?** O tipo de análise que custos uma hora de consultor — disponível on-demand para qualquer ativo.

**Onde acessa?** `/ai` ou na página `/stock/[TICKER]` → "Analisar com IA".

**Nota**: Sempre acompanha disclaimers CVM — material informativo, não recomendação.

---

## 6. Screeners — encontrar ativos

### 6.1 Screener de ações (snapshot) — filtros básicos

**O que faz?** Filtra o universo completo de ~900 ações da B3 por DY, P/L, P/VP, EV/EBITDA, setor, volume e market cap. Atualizado todo dia útil às 7h.

**O que facilita?** Encontrar ações baratas ou com alto DY sem pagar Bloomberg.

**Onde acessa?** `/screener/acoes`

**Limitação**: `sector` pode aparecer como "Outros" para tickers sem metadado de setor no brapi.dev.

---

### 6.2 Screener de ações — universo completo

**O que faz?** Exibe todos os ~900 tickers de B3 com filtro livre no lado do cliente.

**Onde acessa?** `/acoes/screener`

---

### 6.3 Screener de FIIs (snapshot) — filtros básicos

**O que faz?** Filtra FIIs por segmento (logística, shopping, papel, etc.), DY, P/VP, vacância e número de cotistas. Dados CVM atualizados semanalmente.

**O que facilita?** Comparar FIIs por critérios que importam pro investidor de renda.

**Onde acessa?** `/screener/fiis`

---

### 6.4 Screener de FIIs — ranking por score composto

**O que faz?** Lista todos os FIIs ranqueados por um score composto: DY (50%) + P/VP invertido (30%) + liquidez (20%). Recalculado todo dia.

**O que facilita?** Uma única lista ordenada do "melhor custo-benefício" de FIIs — sem você precisar ponderar critérios manualmente.

**Onde acessa?** `/fii/screener`

---

### 6.5 Screener Goldman Sachs AI *(Premium)*

**O que faz?** Análise de screening estilo Goldman Sachs executada por IA — mais sofisticado que os filtros de snapshot. Resultado em minutos, histórico salvo.

**O que facilita?** Framework de seleção de ativos de qualidade institucional acessível ao investidor individual.

**Onde acessa?** `/screener`

---

## 7. Renda fixa

### 7.1 Catálogo de renda fixa

**O que faz?** Lista CDBs, LCIs e LCAs disponíveis com rentabilidade bruta e retorno líquido ajustado por IR nos prazos de 6m, 1a, 2a e 5a. Rates de CDI e IPCA embutidos no cálculo.

**O que facilita?** Comparar papéis de renda fixa já com imposto de renda calculado — sem precisar fazer a conta na mão.

**Onde acessa?** `/renda-fixa`

---

### 7.2 Tesouro Direto

**O que faz?** Taxas atuais do Tesouro Direto (Selic, IPCA+, Prefixado) atualizadas a cada 6h via ANBIMA.

**Onde acessa?** `/renda-fixa` (aba Tesouro Direto)

---

### 7.3 Comparador RF vs RV

**O que faz?** Você informa prazo e valor e o comparador mostra, lado a lado, o retorno líquido de: CDB/LCI/LCA, Tesouro Direto, CDI, IBOVESPA histórico — tudo ajustado por IR no prazo escolhido.

**O que facilita?** Responder a pergunta "faz sentido sair de ações para CDB agora?" com números reais, não intuição.

**Onde acessa?** `/comparador`

---

## 8. Ferramentas de planejamento

### 8.1 Simulador de alocação

**O que faz?** Você informa perfil de risco (conservador/moderado/arrojado), prazo e valor a investir. O simulador gera 3 cenários (pessimista/base/otimista) com projeção de retorno ajustada por IR, e mostra o delta entre sua alocação atual e a alocação ideal para o perfil.

**O que facilita?** Ver em números o impacto de cada decisão de alocação antes de executar.

**Onde acessa?** `/simulador`

---

### 8.2 Onde Investir (Wizard) *(Premium)*

**O que faz?** Você informa perfil, horizonte e quanto quer investir. A IA recomenda uma alocação personalizada entre ações, FIIs e renda fixa, com justificativa.

**O que facilita?** Um ponto de partida concreto para alocação — especialmente útil quando você tem capital novo e não sabe onde colocar.

**Onde acessa?** `/wizard`

**Nota**: Sempre acompanha disclaimer CVM — sugestão educativa, não recomendação de investimento.

---

## 9. IR Helper

**O que faz?** Três funcionalidades de apoio ao IR:
1. **DARF**: calcula o imposto de renda devido em swing trade no mês selecionado, aplicando isenção de R$ 20k, alíquota de 15%, e carregamento de prejuízo de meses anteriores.
2. **Histórico mensal**: visão mês a mês de lucro/prejuízo realizado e DARF gerado.
3. **Declaração DIRPF**: gera a posição de bens e direitos em 31/12 com os códigos ReceitaNet corretos, pronta para copiar na declaração.

**O que facilita?** Você fecha o IR sem precisar calcular manualmente ou pagar contador para a parte mecânica.

**Onde acessa?** `/ir-helper`

---

## 10. Advisor — IA de carteira *(Premium para IA narrativa)*

### 10.1 Health Score (gratuito)

**O que faz?** Score de 0 a 100 da saúde da carteira, calculado instantaneamente em 4 dimensões: diversificação, risco de concentração, renda passiva e underperformers. Sem IA — regras determinísticas.

**O que facilita?** Uma nota objetiva da sua carteira em segundos, sem depender de IA.

**Onde acessa?** `/ai/advisor`

---

### 10.2 Inbox de decisões (gratuito)

**O que faz?** Agrega numa só tela os alertas mais relevantes das últimas 24h: saúde da carteira, oportunidades detectadas, insights de portfólio, alertas de watchlist e sinais de swing trade.

**O que facilita?** Uma única tela de "o que fazer hoje" — sem precisar visitar cada módulo separadamente.

**Onde acessa?** `/ai/advisor` (aba Inbox)

---

### 10.3 Narrativa de IA *(Premium)*

**O que faz?** Análise narrativa completa da carteira gerada por IA: pontos fortes, riscos, sugestões de rebalanceamento, contexto macroeconômico. Resultado em minutos.

**O que facilita?** Um relatório de carteira que normalmente exigiria assessor de investimentos — disponível on-demand.

**Onde acessa?** `/ai/advisor` → botão "Analisar com IA".

**Nota**: Sempre acompanha disclaimers CVM obrigatórios.

---

## 11. Swing Trade

**O que faz?** Dois recursos:
1. **Sinais automáticos**: lista de sinais de compra/venda/neutro para ativos da sua carteira e do radar, calculados a partir de preços em tempo real.
2. **Log de operações**: registro manual de operações de swing trade (entrada, saída, stop), com acompanhamento de resultado aberto/fechado.

**O que facilita?** Centralizar a gestão de operações táticas separado da carteira de longo prazo.

**Onde acessa?** `/swing-trade`

---

## 12. Perfil do investidor

**O que faz?** Cadastro do seu perfil: idade, renda, tolerância a risco, objetivo de investimento e horizonte. Usado pelo Wizard e pelo Simulador para personalizar recomendações.

**O que facilita?** As ferramentas de planejamento funcionam com contexto real seu — não com defaults genéricos.

**Onde acessa?** `/profile`

---

## 13. Assinatura

**O que faz?** Gestão do plano: upgrade para Premium via Stripe Checkout, portal para cancelar ou atualizar dados de pagamento, visualização de limites e uso atual.

**Onde acessa?** `/planos`

---

## 14. Admin (Alexandre only)

| Tela | O que faz |
|---|---|
| `/admin/subscribers` | Lista todos os assinantes pagantes com status de pagamento |
| `/admin/ai-usage` | Consumo de IA por provedor, por dia, e taxa de sucesso |
| `/admin/logs` | Erros de aplicação — para diagnóstico rápido sem SSH |

---

## Resumo por área

| Área | Funcionalidades | Free | Premium |
|---|---|---|---|
| Carteira | Registro, posições, dividendos, histórico | Até 50 transações | Ilimitado |
| Importação | PDF / CSV / XLSX de corretoras | 3/mês | Ilimitado |
| Dashboard | Patrimônio consolidado, macro, gráfico | ✅ | ✅ |
| Monitoramento | Alertas de preço, insights diários, digest semanal | ✅ | ✅ |
| Watchlist | Acompanhar ativos, alertas de preço | ✅ | ✅ |
| Screener ações | Snapshot B3, filtros básicos e universo completo | ✅ | ✅ |
| Screener FIIs | Snapshot + ranking por score | ✅ | ✅ |
| Screener Goldman AI | IA de seleção estilo institucional | ❌ | ✅ |
| Renda fixa | Catálogo IR-ajustado, Tesouro, Comparador | ✅ | ✅ |
| Simulador | 3 cenários por perfil/prazo | ✅ | ✅ |
| Wizard "Onde Investir" | Recomendação IA de alocação | ❌ | ✅ |
| IR Helper | DARF, histórico, DIRPF | ✅ | ✅ |
| Análises IA (DCF, valuation, setor) | Por ativo, on-demand | ❌ | ✅ |
| Advisor Health Score + Inbox | Score imediato + painel de alertas | ✅ | ✅ |
| Advisor Narrativa IA | Relatório completo de carteira por IA | ❌ | ✅ |
| Swing Trade | Sinais + log de operações | ✅ | ✅ |
| Oportunidades | Detector automático de oportunidades | ✅ | ✅ |

---

*Gerado a partir do código em produção em 2026-04-19.*
