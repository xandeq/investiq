// ============================================================
// CARTEIRA ALEXANDRE — Dashboard Financeiro Completo
// Gerado por Claude Code | Versão 1.0 | Março 2026
// ============================================================
// INSTRUCOES:
// 1. Abra qualquer Google Sheet
// 2. Extensoes > Apps Script
// 3. Cole este codigo (substitua tudo que estiver la)
// 4. Clique em Executar > criarDashboard
// ============================================================

function criarDashboard() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  // Remove abas antigas se existirem
  const abasParaCriar = ['📊 Dashboard', '📈 Ações', '🏢 FIIs', '💰 Renda Fixa', '🎯 Plano Alocação', '📅 Histórico'];
  abasParaCriar.forEach(nome => {
    const aba = ss.getSheetByName(nome);
    if (aba) ss.deleteSheet(aba);
  });

  // Cores do tema
  const COR = {
    azulEscuro:   '#1a237e',
    azulMedio:    '#283593',
    azulClaro:    '#3949ab',
    azulSuave:    '#e8eaf6',
    azulBorda:    '#7986cb',
    verdeEscuro:  '#1b5e20',
    verdeMedio:   '#2e7d32',
    verdeClaro:   '#e8f5e9',
    verdeBorda:   '#66bb6a',
    vermelho:     '#c62828',
    vermelhoClaro:'#ffebee',
    amarelo:      '#f57f17',
    amareloClaro: '#fff9c4',
    cinzaEscuro:  '#37474f',
    cinzaMedio:   '#607d8b',
    cinzaClaro:   '#eceff1',
    branco:       '#ffffff',
    dourado:      '#f9a825',
    grafite:      '#263238',
  };

  // ============================================================
  // ABA 1: DASHBOARD
  // ============================================================
  const dash = ss.insertSheet('📊 Dashboard', 0);
  dash.setTabColor(COR.azulEscuro);

  // Dimensoes
  dash.setColumnWidth(1, 25);
  [2,3,4,5,6,7,8,9,10,11].forEach(c => dash.setColumnWidth(c, 140));
  dash.setColumnWidth(12, 25);

  // ---- CABECALHO ----
  dash.setRowHeight(1, 10);
  dash.setRowHeight(2, 60);
  dash.setRowHeight(3, 35);
  dash.setRowHeight(4, 10);

  const cabecalho = dash.getRange('B2:K2');
  cabecalho.merge();
  cabecalho.setValue('💼  CARTEIRA ALEXANDRE  —  Dashboard Financeiro');
  cabecalho.setBackground(COR.azulEscuro);
  cabecalho.setFontColor(COR.branco);
  cabecalho.setFontSize(22);
  cabecalho.setFontWeight('bold');
  cabecalho.setVerticalAlignment('middle');
  cabecalho.setHorizontalAlignment('center');

  const subtitulo = dash.getRange('B3:K3');
  subtitulo.merge();
  subtitulo.setValue('Atualizado em: ' + Utilities.formatDate(new Date(), 'America/Sao_Paulo', 'dd/MM/yyyy HH:mm') + '   |   Perfil: Conservador   |   Objetivo: Renda Passiva + Preservação de Capital');
  subtitulo.setBackground(COR.azulMedio);
  subtitulo.setFontColor('#c5cae9');
  subtitulo.setFontSize(10);
  subtitulo.setHorizontalAlignment('center');
  subtitulo.setVerticalAlignment('middle');

  // ---- CARDS PATRIMONIO ----
  dash.setRowHeight(5, 15);
  dash.setRowHeight(6, 30);
  dash.setRowHeight(7, 50);
  dash.setRowHeight(8, 30);
  dash.setRowHeight(9, 15);

  const cards = [
    { range: 'B6:C8', titulo: '💼 PATRIMÔNIO TOTAL', valor: 'R$ 169.993', cor: COR.azulEscuro, corFonte: COR.branco },
    { range: 'D6:E8', titulo: '📈 RENDA VARIÁVEL', valor: 'R$ 13.992', cor: COR.verdeMedio, corFonte: COR.branco },
    { range: 'F6:G8', titulo: '🏦 RESERVA EMERG.', valor: 'R$ 65.000', cor: COR.amarelo, corFonte: COR.grafite },
    { range: 'H6:I8', titulo: '💰 HERANÇA (XP)', valor: 'R$ 91.000', cor: COR.azulClaro, corFonte: COR.branco },
    { range: 'J6:K8', titulo: '📅 RENDA/MÊS', valor: 'R$ 112', cor: COR.verdeMedio, corFonte: COR.branco },
  ];

  cards.forEach(c => {
    const r = dash.getRange(c.range);
    r.merge();
    r.setBackground(c.cor);
    r.setFontColor(c.corFonte);
    r.setFontWeight('bold');
    r.setHorizontalAlignment('center');
    r.setVerticalAlignment('middle');
    r.setBorder(true, true, true, true, false, false, COR.branco, SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
    // Titulo + valor em duas linhas
    r.setValue(c.titulo + '\n' + c.valor);
    r.setFontSize(11);
    r.setWrap(true);
  });

  // ---- ALERTA RESERVA ----
  dash.setRowHeight(10, 50);
  const alerta = dash.getRange('B10:K10');
  alerta.merge();
  alerta.setValue('⚠️  ALERTA: Reserva de emergência cobre apenas 3,2 meses. Com gastos de R$ 20.000/mês e bebê nascendo em 20 dias, o ideal é 6 meses (R$ 120.000). Alocar R$ 55.000 da herança imediatamente no Tesouro Selic.');
  alerta.setBackground('#fff3e0');
  alerta.setFontColor('#e65100');
  alerta.setFontSize(10);
  alerta.setFontWeight('bold');
  alerta.setVerticalAlignment('middle');
  alerta.setHorizontalAlignment('left');
  alerta.setBorder(true, true, true, true, false, false, '#e65100', SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
  alerta.setWrap(true);

  // ---- ALOCACAO ATUAL vs IDEAL ----
  dash.setRowHeight(11, 15);
  dash.setRowHeight(12, 30);
  dash.setRowHeight(13, 25);
  dash.setRowHeight(14, 25);
  dash.setRowHeight(15, 25);
  dash.setRowHeight(16, 25);
  dash.setRowHeight(17, 25);
  dash.setRowHeight(18, 25);

  // Titulo secao
  const tituloAloc = dash.getRange('B12:F12');
  tituloAloc.merge();
  setTituloSecao(tituloAloc, '📊 ALOCAÇÃO ATUAL vs IDEAL', COR);

  const tituloPlano = dash.getRange('G12:K12');
  tituloPlano.merge();
  setTituloSecao(tituloPlano, '🎯 PLANO DE ALOCAÇÃO DOS R$ 91.000', COR);

  // Tabela alocacao atual
  const headersAloc = [['CLASSE', 'VALOR', '% ATUAL', '% IDEAL', 'STATUS']];
  const dadosAloc = [
    ['Renda Variável (Ações)', 'R$ 7.292', '4,3%', '15-25%', '⬇️ Baixo'],
    ['FIIs', 'R$ 6.701', '3,9%', '15-20%', '⬇️ Baixo'],
    ['Renda Fixa', 'R$ 0', '0,0%', '40-50%', '⚠️ Zero'],
    ['Reserva Emergência', 'R$ 65.000', '38,2%', '35-50%', '⚠️ Insuf.'],
    ['Internacional', 'R$ 0', '0,0%', '5-10%', '⬇️ Baixo'],
  ];

  setTabelaComCabecalho(dash, 13, 2, headersAloc, dadosAloc, COR);

  // Tabela plano
  const headersPlano = [['DESTINO', 'VALOR', 'PRIORIDADE', 'ONDE', 'STATUS']];
  const dadosPlano = [
    ['Completar Reserva (6m)', 'R$ 55.000', '🔴 URGENTE', 'Tesouro Selic XP', 'Pendente'],
    ['Tesouro IPCA+ 2035', 'R$ 10.000', '🟡 Alta', 'XP', 'Pendente'],
    ['LCI/LCA isento IR', 'R$ 4.400', '🟡 Alta', 'XP', 'Pendente'],
    ['FIIs (KNCR11+HGLG11+VRTA11)', 'R$ 12.600', '🟢 Média', 'Clear', 'Pendente'],
    ['Ações (BBAS3+WEGE3+ITUB4)', 'R$ 9.000', '🟢 Média', 'Clear', 'Pendente'],
  ];

  setTabelaComCabecalho(dash, 13, 7, headersPlano, dadosPlano, COR);

  // ---- CARTEIRA ACOES RESUMO ----
  dash.setRowHeight(19, 15);
  dash.setRowHeight(20, 30);

  const tituloAcoes = dash.getRange('B20:F20');
  tituloAcoes.merge();
  setTituloSecao(tituloAcoes, '📈 AÇÕES — Top Posições', COR);

  const tituloFIIs2 = dash.getRange('G20:K20');
  tituloFIIs2.merge();
  setTituloSecao(tituloFIIs2, '🏢 FIIs — Top Posições', COR);

  const acoesDash = [
    ['TICKER', 'EMPRESA', 'POSIÇÃO', 'PREÇO', 'AVALIAÇÃO'],
    ['ITUB4', 'Itaú Unibanco', 'R$ 1.988', 'R$ 42,95', '✅ Manter'],
    ['PETR4', 'Petrobras', 'R$ 1.663', 'R$ 45,14', '⚠️ Não aportar'],
    ['TAEE11', 'Taesa', 'R$ 600', 'R$ 42,74', '✅ Manter'],
    ['BBAS3', 'Banco do Brasil', 'R$ 444', 'R$ 24,56', '🟢 Comprar mais'],
    ['BBSE3', 'BB Seguridade', 'R$ 383', 'R$ 34,77', '✅ Manter'],
    ['ITSA4', 'Itaúsa', 'R$ 378', 'R$ 13,43', '✅ Manter'],
    ['EGIE3', 'Engie Brasil', 'R$ 352', 'R$ 31,91', '✅ Manter'],
    ['Outros (9)', '—', 'R$ 1.441', '—', '—'],
  ];

  setTabelaComCabecalho(dash, 21, 2, [acoesDash[0]], acoesDash.slice(1), COR);

  const fiisTop = [
    ['FII', 'TIPO', 'POSIÇÃO', 'P/VP', 'AVALIAÇÃO'],
    ['KNCR11', 'CRI CDI', 'R$ 2.200', '~1,00', '✅ Adicionar'],
    ['BTLG11', 'Logística', 'R$ 1.040', '1,01', '✅ Manter'],
    ['MXRF11', 'CRI Diversif.', 'R$ 774', '0,97', '✅ Manter'],
    ['HGLG11', 'Logística', 'R$ 628', '0,99', '🟢 Adicionar'],
    ['HGRE11', 'Lajes Corp.', 'R$ 385', '~1,00', '✅ Manter'],
    ['CPTS11', 'CRI CDI', 'R$ 356', '~1,00', '✅ Manter'],
    ['KNRI11', 'Híbrido', 'R$ 331', '1,03', '✅ Manter'],
    ['Outros (8)', '—', 'R$ 978', '—', '—'],
  ];

  setTabelaComCabecalho(dash, 21, 7, [fiisTop[0]], fiisTop.slice(1), COR);

  // ---- RENDA PASSIVA PROJECAO ----
  dash.setRowHeight(30, 15);
  dash.setRowHeight(31, 30);

  const tituloRenda = dash.getRange('B31:K31');
  tituloRenda.merge();
  setTituloSecao(tituloRenda, '💵 PROJEÇÃO DE RENDA PASSIVA', COR);

  const rendaData = [
    ['CENÁRIO', 'RENDA/MÊS', 'RENDA/ANO', '% DAS DESPESAS', 'PATRIMÔNIO NECESSÁRIO'],
    ['Atual (carteira Clear)', 'R$ 112', 'R$ 1.344', '0,6%', '—'],
    ['Após alocar herança', 'R$ 447', 'R$ 5.364', '2,2%', '—'],
    ['Meta 1 ano (aportes)', 'R$ 800', 'R$ 9.600', '4,0%', '~R$ 100.000'],
    ['Meta 5 anos', 'R$ 2.500', 'R$ 30.000', '12,5%', '~R$ 300.000'],
    ['Meta 10 anos (semi-IF)', 'R$ 8.000', 'R$ 96.000', '40%', '~R$ 900.000'],
    ['Independência Financeira', 'R$ 20.000', 'R$ 240.000', '100%', '~R$ 2.400.000'],
  ];

  setTabelaComCabecalho(dash, 32, 2, [rendaData[0]], rendaData.slice(1), COR);

  // Colorir linhas especiais
  dash.getRange(33, 2, 1, 10).setBackground('#f3e5f5');  // linha atual
  dash.getRange(34, 2, 1, 10).setBackground('#e8f5e9');  // linha após herança

  // ---- GRAFICO PIZZA ALOCACAO ----
  // Dados para o grafico (coluna oculta)
  dash.getRange('M2').setValue('Classe');
  dash.getRange('N2').setValue('Valor');
  const graficoDados = [
    ['Ações', 7292],
    ['FIIs', 6701],
    ['Reserva Emerg.', 65000],
    ['Herança (XP)', 91000],
  ];
  graficoDados.forEach((row, i) => {
    dash.getRange(3 + i, 13).setValue(row[0]);
    dash.getRange(3 + i, 14).setValue(row[1]);
  });

  const chart1 = dash.newChart()
    .setChartType(Charts.ChartType.PIE)
    .addRange(dash.getRange('M2:N6'))
    .setPosition(5, 8, 0, 0)
    .setOption('title', 'Alocação Atual do Patrimônio')
    .setOption('titleTextStyle', { fontSize: 13, bold: true, color: COR.azulEscuro })
    .setOption('pieHole', 0.4)
    .setOption('legend', { position: 'bottom', textStyle: { fontSize: 10 } })
    .setOption('colors', [COR.verdeMedio, '#26a69a', COR.amarelo, COR.azulClaro])
    .setOption('width', 380)
    .setOption('height', 280)
    .build();
  // Remover chart antigo se existir e inserir novo
  try { dash.insertChart(chart1); } catch(e) {}

  // ---- FOOTER ----
  const ultimaLinha = 40;
  dash.setRowHeight(ultimaLinha, 30);
  const footer = dash.getRange(ultimaLinha, 2, 1, 10);
  footer.merge();
  footer.setValue('📌  Análise gerada por Claude Code  |  Dados: Yahoo Finance + cálculos próprios  |  Não é recomendação de investimento. Consulte um assessor CVM.');
  footer.setBackground(COR.cinzaClaro);
  footer.setFontColor(COR.cinzaMedio);
  footer.setFontSize(9);
  footer.setHorizontalAlignment('center');
  footer.setVerticalAlignment('middle');

  // ============================================================
  // ABA 2: AÇÕES DETALHADO
  // ============================================================
  const abaAcoes = ss.insertSheet('📈 Ações', 1);
  abaAcoes.setTabColor(COR.verdeMedio);

  [1,2,3,4,5,6,7,8,9,10,11,12].forEach(c => abaAcoes.setColumnWidth(c, 130));
  abaAcoes.setColumnWidth(1, 20);

  // Cabecalho
  setCabecalhoAba(abaAcoes, '📈 CARTEIRA DE AÇÕES — Análise Detalhada', COR);

  // Tabela de acoes
  const headersAcoesDetail = [['TICKER','EMPRESA','SETOR','QTD','P.MÉDIO','PREÇO ATUAL','POSIÇÃO','VARIAÇÃO','P/L','P/VP','DY EST.','AVALIAÇÃO']];
  const dadosAcoesDetail = [
    ['ITUB4','Itaú Unibanco','Banco','46','R$ 43,21','R$ 42,95','R$ 1.976','-0,6%','10,6','2,30','7%','✅ MANTER'],
    ['PETR4','Petrobras','Petróleo','37','R$ 44,95','R$ 45,14','R$ 1.670','+0,4%','5,6','1,39','13%','⚠️ NÃO APORTAR'],
    ['TAEE11','Taesa','Transmissão','14','R$ 42,85','R$ 42,74','R$ 598','-0,3%','39,4','1,90','10%','✅ MANTER'],
    ['BBAS3','Banco do Brasil','Banco','18','R$ 24,64','R$ 24,56','R$ 442','-0,3%','10,1','0,73','10%','🟢 COMPRAR MAIS'],
    ['BBSE3','BB Seguridade','Seguros','11','R$ 34,85','R$ 34,77','R$ 383','-0,2%','—','—','7%','✅ MANTER'],
    ['ITSA4','Itaúsa','Holding','28','R$ 13,50','R$ 13,43','R$ 376','-0,5%','—','—','6%','✅ MANTER'],
    ['EGIE3','Engie Brasil','Elétrica','11','R$ 32,04','R$ 31,91','R$ 351','-0,4%','14,0','2,83','8%','✅ MANTER'],
    ['ISAE3','Isa Energia','Elétrica','9','R$ 32,85','R$ 32,85','R$ 296','0,0%','—','—','8%','✅ MANTER'],
    ['VIVT3','Vivo/Telefônica','Telecom','7','R$ 41,19','R$ 41,08','R$ 288','-0,3%','21,2','1,88','7%','✅ MANTER'],
    ['CPLE3','Copel','Elétrica','18','R$ 14,40','R$ 14,36','R$ 258','-0,3%','—','—','8%','✅ MANTER'],
    ['VALE3','Vale','Mineração','2','R$ 79,30','R$ 79,14','R$ 158','-0,2%','27,7','1,84','8%','⚠️ VOLÁTIL'],
    ['MDIA3','M.Dias Branco','Consumo','7','R$ 22,41','R$ 22,43','R$ 157','+0,1%','—','—','5%','✅ MANTER'],
    ['DIRR3','Direcional','Construção','9','R$ 14,09','R$ 14,02','R$ 126','-0,5%','—','—','—','⚠️ REVISAR'],
    ['CMIG4','Cemig','Elétrica','9','R$ 11,91','R$ 11,86','R$ 107','-0,4%','5,1','1,16','10%','✅ MANTER'],
    ['TAEE4','Taesa ON','Transmissão','5','R$ 14,40','R$ 14,36','R$ 72','-0,3%','—','—','10%','✅ MANTER'],
    ['CSAN3','Cosan','Holding','6','R$ 5,74','R$ 5,72','R$ 34','-0,3%','—','—','—','⚠️ POSIÇÃO IRREL.'],
  ];

  setTabelaComCabecalho(abaAcoes, 4, 2, headersAcoesDetail, dadosAcoesDetail, COR);

  // Total
  const totalAcoes = abaAcoes.getRange(21, 2, 1, 12);
  totalAcoes.getCell(1,1).setValue('TOTAL').setFontWeight('bold');
  totalAcoes.getCell(1,7).setValue('R$ 7.292').setFontWeight('bold');
  totalAcoes.setBackground(COR.azulSuave);

  // Colorir linhas de avaliacao
  colorirLinhasAvaliacao(abaAcoes, 5, 16, 2, 12);

  // Secao recomendacoes
  abaAcoes.setRowHeight(23, 30);
  setCabecalhoSecao(abaAcoes, 23, 2, 12, '💡 RECOMENDAÇÕES PARA NOVOS APORTES EM AÇÕES', COR);

  const recsAcoes = [
    ['TICKER', 'PREÇO ALVO', 'APORTE SUGERIDO', 'QTD SUGERIDA', 'MOTIVO'],
    ['BBAS3', 'Abaixo R$26', 'R$ 3.000', '~120 cotas', 'P/VP 0,73 (abaixo patrimônio), RSI 29, banco sólido'],
    ['WEGE3', 'Abaixo R$50', 'R$ 3.000', '~60 cotas', 'RSI 11,6 mínimo histórico, melhor industrial BR'],
    ['ITUB4', 'Abaixo R$44', 'R$ 3.000', '~70 cotas', 'RSI 20,7 extremamente oversold, ROE 21%'],
    ['SUZB3', 'Abaixo R$56', 'R$ 0 (novo)', '~50 cotas', 'P/L 4,9, ROE 35%, papel/celulose ciclo favorável'],
  ];
  setTabelaComCabecalho(abaAcoes, 24, 2, [recsAcoes[0]], recsAcoes.slice(1), COR);

  // ============================================================
  // ABA 3: FIIs DETALHADO
  // ============================================================
  const abaFIIs = ss.insertSheet('🏢 FIIs', 2);
  abaFIIs.setTabColor('#26a69a');
  [1,2,3,4,5,6,7,8,9,10,11].forEach(c => abaFIIs.setColumnWidth(c, 135));
  abaFIIs.setColumnWidth(1, 20);

  setCabecalhoAba(abaFIIs, '🏢 CARTEIRA DE FIIs — Análise Detalhada', COR);

  const headersFII = [['FII','NOME','TIPO','COTAS','P.MÉDIO','PREÇO ATUAL','POSIÇÃO','VARIAÇÃO','P/VP','PROV. EST./MÊS','AVALIAÇÃO']];
  const dadosFII = [
    ['KNCR11','Kinea CRI','CRI CDI','21','R$ 104,75','R$ 104,74','R$ 2.200','-0,0%','~1,00','R$ 21,42','✅ ADICIONAR'],
    ['BTLG11','BTG Logística','Logística','10','R$ 104,00','R$ 103,99','R$ 1.040','-0,0%','1,01','R$ 8,80','✅ MANTER'],
    ['MXRF11','Maxi Renda','CRI Diversif.','80','R$ 9,68','R$ 9,68','R$ 774','+0,0%','0,97','R$ 6,00','✅ MANTER'],
    ['HGLG11','CSHG Logística','Logística','4','R$ 157,04','R$ 156,83','R$ 627','-0,1%','0,99','R$ 5,80','🟢 ADICIONAR'],
    ['HGRE11','CSHG Real Est.','Lajes Corp.','3','R$ 128,45','R$ 128,38','R$ 385','-0,1%','~1,00','R$ 1,65','✅ MANTER'],
    ['CPTS11','Capitânia Sec.','CRI CDI','44','R$ 8,08','R$ 8,08','R$ 356','+0,0%','~1,00','R$ 3,96','✅ MANTER'],
    ['KNRI11','Kinea Renda Imob','Híbrido','2','R$ 165,66','R$ 165,66','R$ 331','+0,0%','1,03','R$ 2,30','✅ MANTER'],
    ['HGBS11','CSHG Brasil Shopping','Shopping','14','R$ 20,46','R$ 20,49','R$ 287','+0,1%','~1,00','R$ 2,52','✅ MANTER'],
    ['RBRR11','RBR Rendimento','CRI Premium','3','R$ 85,44','R$ 85,44','R$ 256','+0,0%','~1,00','R$ 2,55','✅ MANTER'],
    ['VISC11','Vinci Shopping','Shopping','2','R$ 110,25','R$ 110,25','R$ 221','+0,0%','—','R$ 1,70','✅ MANTER'],
    ['VILG11','Vinci Logística','Logística','1','R$ 99,56','R$ 99,39','R$ 99','-0,2%','~1,00','R$ 0,80','✅ MANTER'],
    ['PSEC11','Plural Sec. Crédito','CRI','1','R$ 62,35','R$ 62,36','R$ 62','+0,0%','—','R$ 0,55','⚠️ POSIÇÃO IRREL.'],
    ['VGHF11','Valora Hedge Fund','CRI','6','R$ 7,10','R$ 7,10','R$ 43','-0,0%','~1,00','R$ 0,42','⚠️ POSIÇÃO IRREL.'],
    ['VGIR11','Valora Receb. Imob','CRI','2','R$ 9,73','R$ 9,73','R$ 19','+0,0%','~1,00','R$ 0,16','🗑️ VENDER/CONSOLIDAR'],
    ['HGBS12','CSHG Shopping2','Shopping','~3','R$ 0,02','R$ 0,02','R$ 0','-','—','—','🗑️ VENDER (lixo)'],
  ];

  setTabelaComCabecalho(abaFIIs, 4, 2, headersFII, dadosFII, COR);

  // Total
  const totalFIIs = abaFIIs.getRange(20, 2, 1, 11);
  totalFIIs.getCell(1,1).setValue('TOTAL').setFontWeight('bold');
  totalFIIs.getCell(1,7).setValue('R$ 6.701').setFontWeight('bold');
  totalFIIs.getCell(1,10).setValue('R$ 58,63/mês').setFontWeight('bold').setFontColor(COR.verdeMedio);
  totalFIIs.setBackground(COR.azulSuave);

  colorirLinhasAvaliacao(abaFIIs, 5, 19, 2, 11);

  // Recomendacoes FII
  abaFIIs.setRowHeight(22, 30);
  setCabecalhoSecao(abaFIIs, 22, 2, 11, '💡 RECOMENDAÇÕES PARA NOVOS APORTES EM FIIs', COR);

  const recsFIIs = [
    ['FII', 'COTAS ATUAIS', 'APORTE SUGERIDO', 'COTAS NOVAS', 'MOTIVO'],
    ['KNCR11', '21', 'R$ 4.200', '+40 cotas', 'CRI CDI ideal para Selic alta. Melhor FII de papel do mercado'],
    ['HGLG11', '4', 'R$ 3.200', '+20 cotas', 'P/VP 0,99 abaixo do VPA. Logística premium, gestão CSHG'],
    ['VRTA11', '0 (novo)', 'R$ 2.000', '~26 cotas', 'P/VP 0,85 — desconto raro em FII de qualidade'],
    ['BTLG11', '10', 'R$ 3.000', '+29 cotas', 'Logística BTG, portfólio premium, P/VP ~1'],
  ];
  setTabelaComCabecalho(abaFIIs, 23, 2, [recsFIIs[0]], recsFIIs.slice(1), COR);

  // ============================================================
  // ABA 4: RENDA FIXA E PLANO
  // ============================================================
  const abaRF = ss.insertSheet('💰 Renda Fixa', 3);
  abaRF.setTabColor(COR.amarelo);
  [1,2,3,4,5,6,7,8,9,10].forEach(c => abaRF.setColumnWidth(c, 150));
  abaRF.setColumnWidth(1, 20);

  setCabecalhoAba(abaRF, '💰 RENDA FIXA — Situação e Recomendações', COR);

  // Situacao atual
  setCabecalhoSecao(abaRF, 4, 2, 10, '📍 SITUAÇÃO ATUAL NA XP', COR);

  const rfAtual = [
    ['APLICAÇÃO', 'VALOR', 'TIPO', 'RENTABILIDADE', 'LIQUIDEZ', 'STATUS', 'AÇÃO RECOMENDADA'],
    ['Reserva Emergência', 'R$ 65.000', 'CDB/Tesouro?', '~13-14% a.a.', 'Diária', '⚠️ Insuficiente', 'Mover para Tesouro Selic 2027'],
    ['Herança (recebida)', 'R$ 45.000', 'Aguardando', '0%?', 'Imediata', '🔴 Parado', 'Alocar conforme plano urgente'],
    ['Herança (chegando)', 'R$ 46.000', 'Chegando', '0%', '—', '⏳ Em trânsito', 'R$9k→Tesouro Selic | Resto investir'],
  ];
  setTabelaComCabecalho(abaRF, 5, 2, [rfAtual[0]], rfAtual.slice(1), COR);

  // Melhores opcoes RF
  setCabecalhoSecao(abaRF, 10, 2, 10, '🏆 MELHORES OPÇÕES DE RENDA FIXA AGORA (Selic ~14,25%)', COR);

  const rfOpcoes = [
    ['PRODUTO', 'RENTAB. EST.', 'PRAZO', 'IR', 'RISCO', 'LIQUIDEZ', 'INDICADO PARA', 'PRIORIDADE'],
    ['Tesouro Selic 2027', '~14,25% a.a.', 'Curto', 'Sim (15-22%)', 'ZERO', 'D+1', 'Reserva de emergência', '🔴 URGENTE'],
    ['Tesouro IPCA+ 2035', '~IPCA+7%', '9 anos', 'Sim', 'Baixo', 'D+1', 'Proteção inflação LT', '🟡 Alta'],
    ['LCI/LCA 95% CDI', '~13,5% a.a.', '1-2 anos', '❌ ISENTO', 'Baixo', '30-90d', 'Renda fixa médio prazo', '🟡 Alta'],
    ['CDB Sofisa/Daycoval 120% CDI', '~17% a.a.', '2 anos', 'Sim', 'Baixo (FGC)', 'Vencimento', 'Rendimento alto prazo', '🟢 Média'],
    ['Debentures Incentivadas IPCA+', '~IPCA+8%', '5-10 anos', '❌ ISENTO', 'Médio', 'Mercado sec.', 'Renda infra isenção IR', '🟢 Média'],
  ];
  setTabelaComCabecalho(abaRF, 11, 2, [rfOpcoes[0]], rfOpcoes.slice(1), COR);

  // Plano renda fixa
  setCabecalhoSecao(abaRF, 18, 2, 10, '📋 PLANO DETALHADO — Alocação dos R$ 91.000', COR);

  const planoRF = [
    ['FASE', 'VALOR', 'DESTINO', 'PRODUTO', 'RESULTADO'],
    ['FASE 1 — IMEDIATO', 'R$ 55.000', 'Reserva emergência', 'Tesouro Selic 2027 (XP)', 'Reserva vai a R$120k = 6 meses ✅'],
    ['FASE 2 — RENDA FIXA', 'R$ 10.000', 'Proteção inflação', 'Tesouro IPCA+ 2035 (XP)', 'Protege poder de compra 9 anos'],
    ['FASE 2 — RENDA FIXA', 'R$ 4.400', 'Isento IR', 'LCI 95% CDI (XP ou Rico)', 'R$49/mês líquido sem IR'],
    ['FASE 3 — FIIs', 'R$ 12.600', 'Renda imobiliária', 'KNCR11+HGLG11+VRTA11+BTLG11', 'R$105/mês adicionais'],
    ['FASE 3 — AÇÕES', 'R$ 9.000', 'Crescimento+dividendos', 'BBAS3+WEGE3+ITUB4', 'R$68/mês adicionais'],
    ['TOTAL', 'R$ 91.000', '—', '—', 'Renda passiva: R$447/mês'],
  ];
  setTabelaComCabecalho(abaRF, 19, 2, [planoRF[0]], planoRF.slice(1), COR);

  // Destacar total
  abaRF.getRange(25, 2, 1, 10).setBackground(COR.azulSuave).setFontWeight('bold');

  // ============================================================
  // ABA 5: PLANO DE ALOCACAO
  // ============================================================
  const abaPlano = ss.insertSheet('🎯 Plano Alocação', 4);
  abaPlano.setTabColor(COR.vermelho);
  [1,2,3,4,5,6,7,8,9].forEach(c => abaPlano.setColumnWidth(c, 160));
  abaPlano.setColumnWidth(1, 20);

  setCabecalhoAba(abaPlano, '🎯 PLANO COMPLETO DE ALOCAÇÃO + CRONOGRAMA', COR);

  // Perfil do investidor
  setCabecalhoSecao(abaPlano, 4, 2, 9, '👤 PERFIL DO INVESTIDOR — Alexandre', COR);

  const perfilData = [
    ['DADOS', 'INFORMAÇÃO'],
    ['Idade', '43 anos'],
    ['Estado civil', 'Casado'],
    ['Filha', 'Nascendo em ~20 dias (Março 2026)'],
    ['Moradia', 'Aluguel'],
    ['Gastos mensais', 'R$ 20.000/mês'],
    ['Patrimônio total', 'R$ 169.993'],
    ['Perfil de risco', 'Conservador'],
    ['Objetivo principal', 'Renda passiva crescente + segurança familiar'],
    ['Horizonte', '10-20 anos'],
    ['Corretoras', 'XP (renda fixa/reserva) + Clear (ações/FIIs)'],
  ];

  perfilData.forEach((row, i) => {
    if (i === 0) {
      const h = abaPlano.getRange(5, 2, 1, 2);
      h.setValues([row]);
      h.setBackground(COR.azulEscuro);
      h.setFontColor(COR.branco);
      h.setFontWeight('bold');
    } else {
      const r = abaPlano.getRange(5 + i, 2, 1, 2);
      r.setValues([row]);
      r.setBackground(i % 2 === 0 ? COR.azulSuave : COR.branco);
    }
  });

  // Cronograma
  setCabecalhoSecao(abaPlano, 18, 2, 9, '📅 CRONOGRAMA DE AÇÕES — Próximas 4 semanas', COR);

  const cronograma = [
    ['SEMANA', 'AÇÃO', 'VALOR', 'ONDE FAZER', 'RESULTADO ESPERADO', 'STATUS'],
    ['Semana 1 (AGORA)', 'Verificar onde está o $ na XP', '—', 'App XP', 'Confirmar rendimento atual', '☐ Pendente'],
    ['Semana 1 (AGORA)', 'Mover R$55k para Tesouro Selic', 'R$ 55.000', 'XP > Tesouro Direto', 'Reserva = 6 meses', '☐ Urgente'],
    ['Semana 2 (herança chega)', 'Receber R$46k adicional', 'R$ 46.000', 'XP', 'Aguardar compensação', '☐ Pendente'],
    ['Semana 2', 'Tesouro IPCA+ 2035', 'R$ 10.000', 'XP > Tesouro Direto', 'Proteção inflação', '☐ Pendente'],
    ['Semana 2', 'LCI/LCA isento IR', 'R$ 4.400', 'XP > Renda Fixa', 'Rendimento isento', '☐ Pendente'],
    ['Semana 3', 'Comprar FIIs na Clear', 'R$ 12.600', 'Clear > FIIs', 'KNCR11+HGLG11+VRTA11+BTLG11', '☐ Pendente'],
    ['Semana 3', 'Comprar Ações na Clear', 'R$ 9.000', 'Clear > Ações', 'BBAS3+WEGE3+ITUB4', '☐ Pendente'],
    ['Semana 4 (bebê)', 'Revisar plano de saúde família', '—', 'Operadora atual', 'Incluir bebê no plano', '☐ Urgente'],
    ['Mensal', 'Aportar R$ 500-1000 em FIIs', '~R$ 750', 'Clear > FIIs', 'Crescimento carteira', '☐ Recorrente'],
  ];
  setTabelaComCabecalho(abaPlano, 19, 2, [cronograma[0]], cronograma.slice(1), COR);

  // ============================================================
  // ABA 6: HISTORICO (para acompanhamento mensal)
  // ============================================================
  const abaHist = ss.insertSheet('📅 Histórico', 5);
  abaHist.setTabColor(COR.cinzaMedio);
  [1,2,3,4,5,6,7,8,9,10,11].forEach(c => abaHist.setColumnWidth(c, 130));
  abaHist.setColumnWidth(1, 20);

  setCabecalhoAba(abaHist, '📅 HISTÓRICO MENSAL — Evolução Patrimonial', COR);

  const headersHist = [['MÊS','AÇÕES','FIIs','RENDA FIXA','RESERVA','TOTAL','RENDA MÊNSAL','APORTE MÊS','DY AÇÕES','DY FIIs','NOTAS']];
  const dadosHist = [
    ['Mar/2026','R$ 7.292','R$ 6.701','R$ 0','R$ 65.000','R$ 78.993','R$ 112','—','7%','~10%','Herança recebida + bebê nascendo'],
    ['Abr/2026','','','','','','','','','',''],
    ['Mai/2026','','','','','','','','','',''],
    ['Jun/2026','','','','','','','','','',''],
    ['Jul/2026','','','','','','','','','',''],
    ['Ago/2026','','','','','','','','','',''],
    ['Set/2026','','','','','','','','','',''],
    ['Out/2026','','','','','','','','','',''],
    ['Nov/2026','','','','','','','','','',''],
    ['Dez/2026','','','','','','','','','',''],
    ['Jan/2027','','','','','','','','','',''],
    ['Fev/2027','','','','','','','','','',''],
    ['Mar/2027','','','','','','','','','',''],
  ];

  setTabelaComCabecalho(abaHist, 4, 2, headersHist, dadosHist, COR);

  // Grafico evolucao (dados historicos)
  // Instrucoes
  abaHist.setRowHeight(20, 30);
  setCabecalhoSecao(abaHist, 20, 2, 11, '📝 INSTRUÇÕES: Preencha os valores mensais na tabela acima para acompanhar a evolução', COR);
  abaHist.getRange(21, 2, 1, 11).merge()
    .setValue('Dica: Use Ctrl+; para inserir a data atual. Atualize todo mês no último dia útil do mês para ter o histórico completo.')
    .setFontSize(10).setFontColor(COR.cinzaMedio).setBackground(COR.cinzaClaro).setVerticalAlignment('middle').setWrap(true);
  abaHist.setRowHeight(21, 40);

  // ============================================================
  // FINALIZACAO
  // ============================================================

  // Voltar ao Dashboard
  ss.setActiveSheet(dash);

  // Renomear o arquivo
  ss.rename('💼 Carteira Alexandre — Dashboard Financeiro');

  SpreadsheetApp.getUi().alert(
    '✅ Dashboard criado com sucesso!\n\n' +
    '📊 Abas criadas:\n' +
    '• Dashboard — Visão geral e alertas\n' +
    '• Ações — Análise de todas as 16 ações\n' +
    '• FIIs — Análise dos 15 FIIs\n' +
    '• Renda Fixa — Plano de alocação\n' +
    '• Plano Alocação — Cronograma semanal\n' +
    '• Histórico — Acompanhamento mensal\n\n' +
    '⚠️ AÇÃO URGENTE: Mover R$55.000 para Tesouro Selic!\n\n' +
    'Gerado por Claude Code | ' + Utilities.formatDate(new Date(), 'America/Sao_Paulo', 'dd/MM/yyyy HH:mm')
  );
}

// ============================================================
// FUNCOES AUXILIARES
// ============================================================

function setCabecalhoAba(sheet, titulo, COR) {
  sheet.setColumnWidth(1, 20);
  sheet.setRowHeight(1, 10);
  sheet.setRowHeight(2, 55);
  sheet.setRowHeight(3, 15);
  const cab = sheet.getRange('B2:K2');
  cab.merge();
  cab.setValue(titulo);
  cab.setBackground(COR.azulEscuro);
  cab.setFontColor(COR.branco);
  cab.setFontSize(18);
  cab.setFontWeight('bold');
  cab.setHorizontalAlignment('center');
  cab.setVerticalAlignment('middle');
}

function setCabecalhoSecao(sheet, linha, colInicio, colFim, titulo, COR) {
  const r = sheet.getRange(linha, colInicio, 1, colFim - colInicio + 1);
  r.merge();
  r.setValue(titulo);
  r.setBackground(COR.azulMedio);
  r.setFontColor(COR.branco);
  r.setFontSize(12);
  r.setFontWeight('bold');
  r.setHorizontalAlignment('left');
  r.setVerticalAlignment('middle');
  r.setBorder(false, true, false, true, false, false, COR.azulBorda, SpreadsheetApp.BorderStyle.SOLID_THICK);
  sheet.setRowHeight(linha, 32);
}

function setTituloSecao(range, titulo, COR) {
  range.setValue(titulo);
  range.setBackground(COR.azulMedio);
  range.setFontColor(COR.branco);
  range.setFontSize(11);
  range.setFontWeight('bold');
  range.setHorizontalAlignment('left');
  range.setVerticalAlignment('middle');
}

function setTabelaComCabecalho(sheet, linhaInicio, colInicio, headers, dados, COR) {
  const numCols = headers[0].length;

  // Cabecalho
  const hRange = sheet.getRange(linhaInicio, colInicio, 1, numCols);
  hRange.setValues(headers);
  hRange.setBackground(COR.azulClaro);
  hRange.setFontColor(COR.branco);
  hRange.setFontWeight('bold');
  hRange.setFontSize(10);
  hRange.setHorizontalAlignment('center');
  hRange.setVerticalAlignment('middle');
  hRange.setBorder(true, true, true, true, true, false, COR.azulBorda, SpreadsheetApp.BorderStyle.SOLID);
  sheet.setRowHeight(linhaInicio, 28);

  // Dados
  if (dados.length > 0) {
    const dRange = sheet.getRange(linhaInicio + 1, colInicio, dados.length, numCols);
    dRange.setValues(dados);
    dRange.setFontSize(10);
    dRange.setVerticalAlignment('middle');
    dRange.setBorder(true, true, true, true, true, true, '#c5cae9', SpreadsheetApp.BorderStyle.SOLID);

    // Zebra striping
    dados.forEach((row, i) => {
      const rowRange = sheet.getRange(linhaInicio + 1 + i, colInicio, 1, numCols);
      if (i % 2 === 0) {
        rowRange.setBackground(COR.branco);
      } else {
        rowRange.setBackground(COR.azulSuave);
      }
      sheet.setRowHeight(linhaInicio + 1 + i, 24);
    });
  }
}

function colorirLinhasAvaliacao(sheet, linhaInicio, linhaFim, colInicio, numCols) {
  for (let i = linhaInicio; i <= linhaFim; i++) {
    const ultCell = sheet.getRange(i, colInicio + numCols - 1).getValue();
    if (typeof ultCell === 'string') {
      if (ultCell.includes('🟢') || ultCell.includes('COMPRAR') || ultCell.includes('ADICIONAR')) {
        sheet.getRange(i, colInicio + numCols - 1).setBackground('#c8e6c9').setFontColor('#1b5e20');
      } else if (ultCell.includes('⚠️') || ultCell.includes('REVISAR') || ultCell.includes('NÃO APORTAR')) {
        sheet.getRange(i, colInicio + numCols - 1).setBackground('#fff9c4').setFontColor('#f57f17');
      } else if (ultCell.includes('🗑️') || ultCell.includes('VENDER') || ultCell.includes('lixo')) {
        sheet.getRange(i, colInicio + numCols - 1).setBackground('#ffcdd2').setFontColor('#c62828');
      } else if (ultCell.includes('✅') || ultCell.includes('MANTER')) {
        sheet.getRange(i, colInicio + numCols - 1).setBackground('#e8f5e9').setFontColor('#2e7d32');
      }
    }
  }
}
