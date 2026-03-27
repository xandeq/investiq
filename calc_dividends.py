
fiis_proventos = {
    'KNCR11': (21, 1.02),
    'BTLG11': (10, 0.88),
    'MXRF11': (80, 0.075),
    'HGLG11': (4, 1.45),
    'HGRE11': (3, 0.55),
    'CPTS11': (44, 0.09),
    'KNRI11': (2, 1.15),
    'HGBS11': (14, 0.18),
    'RBRR11': (3, 0.85),
    'VISC11': (2, 0.85),
    'VILG11': (1, 0.80),
    'PSEC11': (1, 0.55),
    'VGHF11': (6, 0.07),
    'VGIR11': (2, 0.08),
}

acoes_dy_anual = {
    'ITUB4':  (46, 43.0, 0.07),
    'PETR4':  (37, 44.9, 0.13),
    'TAEE11': (14, 42.9, 0.10),
    'BBAS3':  (18, 24.6, 0.10),
    'BBSE3':  (11, 34.9, 0.07),
    'ITSA4':  (28, 13.5, 0.06),
    'EGIE3':  (11, 32.0, 0.08),
    'ISAE3':  (9, 32.9, 0.08),
    'VIVT3':  (7, 41.2, 0.07),
    'CPLE3':  (18, 14.4, 0.08),
    'VALE3':  (2, 79.3, 0.08),
    'MDIA3':  (7, 22.4, 0.05),
    'TAEE4':  (5, 14.4, 0.10),
    'CMIG4':  (9, 11.9, 0.10),
}

print('=== RENDA MENSAL ESTIMADA - FIIs ===')
total_fii = 0
for t, (qtd, prov) in fiis_proventos.items():
    mensal = qtd * prov
    total_fii += mensal
    print(f'{t:<12} {qtd:>3} cotas x R${prov:.3f} = R${mensal:>6.2f}/mes')
print(f'\nTOTAL FIIs: R${total_fii:.2f}/mes | R${total_fii*12:.0f}/ano')

print('\n=== RENDA MENSAL ESTIMADA - ACOES (dividendos) ===')
total_acoes_anual = 0
for t, (qtd, preco, dy) in acoes_dy_anual.items():
    anual = qtd * preco * dy
    total_acoes_anual += anual
    print(f'{t:<12} DY {dy*100:.0f}% -> R${anual/12:.2f}/mes | R${anual:.0f}/ano')

total_mensal_atual = total_fii + total_acoes_anual/12
print(f'\nTOTAL Acoes: R${total_acoes_anual/12:.2f}/mes | R${total_acoes_anual:.0f}/ano')
print(f'\nTOTAL GERAL CARTEIRA CLEAR: R${total_mensal_atual:.2f}/mes | R${total_mensal_atual*12:.0f}/ano')

print('\n=== ANALISE RESERVA DE EMERGENCIA ===')
gastos_mensais = 20000
reserva_atual = 65000
meses_cobertura = reserva_atual / gastos_mensais
print(f'Gastos mensais:       R${gastos_mensais:,.0f}/mes')
print(f'Reserva atual:        R${reserva_atual:,.0f} ({meses_cobertura:.1f} meses)')
print(f'Cobertura ideal 6m:   R${gastos_mensais*6:,.0f}')
print(f'Cobertura ideal 9m:   R${gastos_mensais*9:,.0f}')
print(f'GAP para 6 meses:     R${(gastos_mensais*6 - reserva_atual):,.0f} faltando')
print(f'GAP para 9 meses:     R${(gastos_mensais*9 - reserva_atual):,.0f} faltando')

print('\n=== PLANO DE ALOCACAO DOS R$91.000 ===')
heranca = 91000
reserva_adicional = 55000  # Completar reserva para 6 meses
para_investir = heranca - reserva_adicional
print(f'Heranca total:        R${heranca:,.0f}')
print(f'Para reserva (6m):    R${reserva_adicional:,.0f} -> Tesouro Selic/CDB liquidez diaria')
print(f'Para investimentos:   R${para_investir:,.0f}')

print(f'\nAlocacao dos R${para_investir:,.0f}:')
rf = para_investir * 0.40
fiis_aporte = para_investir * 0.35
acoes_aporte = para_investir * 0.25
print(f'  Renda Fixa (40%):   R${rf:,.0f}  -> Tesouro IPCA+ + CDB banco medio')
print(f'  FIIs (35%):         R${fiis_aporte:,.0f}  -> KNCR11, HGLG11, VRTA11, BTLG11')
print(f'  Acoes (25%):        R${acoes_aporte:,.0f}  -> BBAS3, WEGE3, SUZB3, ITUB4')

selic = 0.1425
print(f'\nRendimento reserva R$120k (Tesouro Selic {selic*100:.2f}%):')
print(f'  Mensal:  R${120000*selic/12:,.0f}')
print(f'  Anual:   R${120000*selic:,.0f}')

print('\n=== PROJECAO RENDA PASSIVA APOS ALOCACAO ===')
renda_fii_adicional = fiis_aporte * 0.10 / 12
renda_acoes_adicional = acoes_aporte * 0.09 / 12
renda_rf = rf * 0.135 / 12
total_projetado = total_mensal_atual + renda_fii_adicional + renda_acoes_adicional + renda_rf
print(f'Renda atual (Clear):         R${total_mensal_atual:.2f}/mes')
print(f'FIIs novos aporte:           R${renda_fii_adicional:.2f}/mes')
print(f'Acoes novos aporte:          R${renda_acoes_adicional:.2f}/mes')
print(f'Renda fixa (juros mensais):  R${renda_rf:.2f}/mes')
print(f'TOTAL RENDA PASSIVA:         R${total_projetado:.2f}/mes')
print(f'% da despesa mensal coberta: {total_projetado/gastos_mensais*100:.1f}%')
