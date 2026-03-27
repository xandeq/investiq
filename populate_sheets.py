"""
Popula o Google Sheet de Alexandre com dashboard completo de investimentos.
Usa Service Account do projeto alexandre-queiroz (Google Cloud).
"""

import json
import subprocess
import gspread
from google.oauth2.service_account import Credentials

# ── 1. Busca credenciais do AWS Secrets Manager ─────────────────────────────
secret_raw = subprocess.check_output([
    'python', '-m', 'awscli', 'secretsmanager', 'get-secret-value',
    '--secret-id', 'tools/google-sheets',
    '--query', 'SecretString',
    '--output', 'text',
    '--region', 'us-east-1'
]).decode().strip()

secret = json.loads(secret_raw)
sa_info = json.loads(secret['SERVICE_ACCOUNT_JSON'])

# ── 2. Autentica via Service Account ────────────────────────────────────────
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
gc = gspread.authorize(creds)

SHEET_ID = '1TfwR-aJpl55LBU0OoxJf1ui-pK1QP3PluppimHrN4qw'
SA_EMAIL = sa_info['client_email']

# ── 3. Compartilha a planilha com a Service Account ─────────────────────────
# Usamos a API Drive para compartilhar
from googleapiclient.discovery import build
drive_service = build('drive', 'v3', credentials=creds)

try:
    drive_service.permissions().create(
        fileId=SHEET_ID,
        body={'type': 'user', 'role': 'writer', 'emailAddress': SA_EMAIL},
        fields='id'
    ).execute()
    print(f"✓ Planilha compartilhada com {SA_EMAIL}")
except Exception as e:
    print(f"  Share: {e} (pode já estar compartilhada)")

# ── 4. Abre a planilha ───────────────────────────────────────────────────────
sh = gc.open_by_key(SHEET_ID)
print(f"✓ Planilha aberta: {sh.title}")

# ── Helper ───────────────────────────────────────────────────────────────────
def get_or_create_sheet(sh, name, rows=100, cols=20):
    try:
        ws = sh.worksheet(name)
        ws.clear()
        return ws
    except gspread.exceptions.WorksheetNotFound:
        return sh.add_worksheet(title=name, rows=rows, cols=cols)

def fmt(val):
    return str(val) if val is not None else ''

def batch_update(ws, data):
    """data = list of (row, col, value) tuples (1-indexed)"""
    body = {'valueInputOption': 'USER_ENTERED', 'data': []}
    for row, col, val in data:
        cell = gspread.utils.rowcol_to_a1(row, col)
        body['data'].append({'range': f"'{ws.title}'!{cell}", 'values': [[val]]})
    if body['data']:
        ws.spreadsheet.values_batch_update(body)

# ── CORES ────────────────────────────────────────────────────────────────────
VERDE_ESCURO  = {"red": 0.063, "green": 0.361, "blue": 0.141}
VERDE_MEDIO   = {"red": 0.204, "green": 0.659, "blue": 0.325}
VERDE_CLARO   = {"red": 0.851, "green": 0.953, "blue": 0.878}
AZUL_ESCURO   = {"red": 0.051, "green": 0.278, "blue": 0.631}
AZUL_CLARO    = {"red": 0.812, "green": 0.886, "blue": 0.953}
AMARELO       = {"red": 1.0,   "green": 0.949, "blue": 0.8}
CINZA_CLARO   = {"red": 0.957, "green": 0.957, "blue": 0.957}
BRANCO        = {"red": 1.0,   "green": 1.0,   "blue": 1.0}
LARANJA       = {"red": 1.0,   "green": 0.596, "blue": 0.0}
VERMELHO      = {"red": 0.8,   "green": 0.1,   "blue": 0.1}

def cell_format(bg=None, bold=False, size=10, color=None, halign=None):
    fmt = {"textFormat": {"bold": bold, "fontSize": size}}
    if bg:
        fmt["backgroundColor"] = bg
    if color:
        fmt["textFormat"]["foregroundColor"] = color
    if halign:
        fmt["horizontalAlignment"] = halign
    return fmt

def apply_formats(ws, formats):
    """formats = list of (range_a1, format_dict)"""
    requests = []
    for rng, fmt_dict in formats:
        requests.append({
            "repeatCell": {
                "range": gridrange(ws, rng),
                "cell": {"userEnteredFormat": fmt_dict},
                "fields": "userEnteredFormat"
            }
        })
    if requests:
        ws.spreadsheet.batch_update({"requests": requests})

def gridrange(ws, a1_range):
    """Converte 'A1:Z50' em gridRange dict"""
    parts = a1_range.split(':')
    r1, c1 = gspread.utils.a1_to_rowcol(parts[0])
    if len(parts) > 1:
        r2, c2 = gspread.utils.a1_to_rowcol(parts[1])
    else:
        r2, c2 = r1, c1
    return {
        "sheetId": ws.id,
        "startRowIndex": r1 - 1,
        "endRowIndex": r2,
        "startColumnIndex": c1 - 1,
        "endColumnIndex": c2
    }

def merge_cells(ws, a1_range):
    r1c1 = a1_range.split(':')
    return {
        "mergeCells": {
            "range": gridrange(ws, a1_range),
            "mergeType": "MERGE_ALL"
        }
    }

def set_col_width(ws, col_index, width_px):
    return {
        "updateDimensionProperties": {
            "range": {"sheetId": ws.id, "dimension": "COLUMNS",
                      "startIndex": col_index, "endIndex": col_index + 1},
            "properties": {"pixelSize": width_px},
            "fields": "pixelSize"
        }
    }

def set_row_height(ws, row_index, height_px):
    return {
        "updateDimensionProperties": {
            "range": {"sheetId": ws.id, "dimension": "ROWS",
                      "startIndex": row_index, "endIndex": row_index + 1},
            "properties": {"pixelSize": height_px},
            "fields": "pixelSize"
        }
    }

# ═══════════════════════════════════════════════════════════════════════════
# ABA 1 — DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════
print("\n📊 Criando aba Dashboard...")
ws1 = get_or_create_sheet(sh, "📊 Dashboard", rows=60, cols=12)

rows = [
    ["CARTEIRA ALEXANDRE QUEIROZ", "", "", "", "", "", "", "", "", "", "", ""],
    ["Dashboard de Investimentos", "", "", "", "", "", "", "", "", "", "", ""],
    ["Atualizado: Março 2026", "", "", "", "", "", "", "", "", "", "", ""],
    [""],
    ["RESUMO PATRIMÔNIAL", "", "", "", "RENDA PASSIVA MENSAL", "", "", "", "RESERVA DE EMERGÊNCIA", "", "", ""],
    ["Categoria", "Valor", "% Carteira", "", "Fonte", "Valor/mês", "", "", "Indicador", "Valor", "", ""],
    ["Ações (Clear)",   "R$ 13.000",  "11,7%", "", "FIIs",        "R$ 70,98",  "", "", "Gastos mensais",   "R$ 20.000", "", ""],
    ["FIIs (Clear)",    "R$ 0",       "0,0%",  "", "Ações (DY)",  "R$ 271,76", "", "", "Reserva atual",    "R$ 65.000", "", ""],
    ["Reserva XP",      "R$ 65.000",  "58,6%", "", "Renda Fixa",  "R$ 0",      "", "", "Cobertura atual",  "3,3 meses", "", ""],
    ["Herança (XP)",    "R$ 91.000",  "81,9%", "", "TOTAL",       "R$ 342,74", "", "", "Meta (6 meses)",   "R$ 120.000", "", ""],
    ["TOTAL GERAL",     "R$ 111.100", "100%",  "", "", "", "", "", "Gap para meta",    "R$ 55.000", "", ""],
    [""],
    ["PLANO DE ALOCAÇÃO - R$ 91.000 (HERANÇA)", "", "", "", "", "", "", "", "", "", "", ""],
    ["Destinação", "Valor", "% do Total", "Objetivo", "", "", "", "", "", "", "", ""],
    ["Reserva de Emergência", "R$ 55.000", "60,4%", "Completar 6 meses de gastos → Tesouro Selic/CDB liquidez diária", "", "", "", "", "", "", "", ""],
    ["Renda Fixa",            "R$ 14.400", "15,8%", "Tesouro IPCA+ / CDB banco médio (40% dos R$36k)", "", "", "", "", "", "", "", ""],
    ["FIIs",                  "R$ 12.600", "13,8%", "KNCR11, HGLG11, VRTA11, BTLG11 (35% dos R$36k)", "", "", "", "", "", "", "", ""],
    ["Ações",                 "R$ 9.000",  "9,9%",  "BBAS3, WEGE3, SUZB3, ITUB4 (25% dos R$36k)", "", "", "", "", "", "", "", ""],
    ["TOTAL",                 "R$ 91.000", "100%",  "", "", "", "", "", "", "", "", ""],
    [""],
    ["PROJEÇÃO RENDA PASSIVA PÓS-ALOCAÇÃO", "", "", "", "", "", "", "", "", "", "", ""],
    ["Fonte", "Atual/mês", "Adicional/mês", "Total/mês", "", "", "", "", "", "", "", ""],
    ["FIIs",               "R$ 70,98",  "R$ 150,00", "R$ 220,98",  "", "", "", "", "", "", "", ""],
    ["Ações (dividendos)", "R$ 271,76", "R$ 135,00", "R$ 406,76",  "", "", "", "", "", "", "", ""],
    ["Renda Fixa (juros)", "R$ 0",      "R$ 162,00", "R$ 162,00",  "", "", "", "", "", "", "", ""],
    ["Reserva (Selic)",    "R$ 0",      "R$ 1.424,00","R$ 1.424,00","", "", "", "", "", "", "", ""],
    ["TOTAL",              "R$ 342,74", "R$ 1.871,00","R$ 2.213,74","", "", "", "", "", "", "", ""],
    [""],
    ["% das despesas mensais cobertas:", "11,1%", "", "→ Meta futura: 100% = R$ 20.000/mês", "", "", "", "", "", "", "", ""],
]

ws1.update('A1', rows)

# Formatações
fmt_reqs = []
dim_reqs = []

# Título
fmt_reqs.append(('A1:L1', cell_format(bg=VERDE_ESCURO, bold=True, size=16,
                                       color=BRANCO, halign='CENTER')))
fmt_reqs.append(('A2:L2', cell_format(bg=AZUL_ESCURO, bold=True, size=12,
                                       color=BRANCO, halign='CENTER')))
fmt_reqs.append(('A3:L3', cell_format(bg=CINZA_CLARO, bold=False, size=10,
                                       halign='CENTER')))

# Headers das seções
for row in [5, 13, 21]:
    fmt_reqs.append((f'A{row}:L{row}', cell_format(bg=VERDE_MEDIO, bold=True,
                                                     color=BRANCO, size=11)))

# Sub-headers
for row in [6, 14, 22]:
    fmt_reqs.append((f'A{row}:L{row}', cell_format(bg=AZUL_CLARO, bold=True, size=10)))

# Totais
for row in [10, 19, 27]:
    fmt_reqs.append((f'A{row}:L{row}', cell_format(bg=VERDE_CLARO, bold=True, size=10)))

# Linhas alternadas tabelas
for row in [7, 9, 15, 17, 23, 25]:
    fmt_reqs.append((f'A{row}:D{row}', cell_format(bg=CINZA_CLARO)))
    fmt_reqs.append((f'E{row}:H{row}', cell_format(bg=CINZA_CLARO)))
    fmt_reqs.append((f'I{row}:L{row}', cell_format(bg=CINZA_CLARO)))

# Linha de projeção
fmt_reqs.append(('A28:L28', cell_format(bg=AMARELO, bold=True, size=10)))

apply_formats(ws1, fmt_reqs)

# Merge título
merge_reqs = [
    merge_cells(ws1, 'A1:L1'),
    merge_cells(ws1, 'A2:L2'),
    merge_cells(ws1, 'A3:L3'),
    merge_cells(ws1, 'A13:L13'),
    merge_cells(ws1, 'A21:L21'),
]
# Col widths
dim_reqs = [
    set_col_width(ws1, 0, 200),
    set_col_width(ws1, 1, 130),
    set_col_width(ws1, 2, 100),
    set_col_width(ws1, 3, 20),
    set_col_width(ws1, 4, 180),
    set_col_width(ws1, 5, 120),
    set_col_width(ws1, 6, 20),
    set_col_width(ws1, 7, 20),
    set_col_width(ws1, 8, 170),
    set_col_width(ws1, 9, 120),
    set_row_height(ws1, 0, 50),
    set_row_height(ws1, 1, 35),
]

ws1.spreadsheet.batch_update({"requests": merge_reqs + dim_reqs})
print("  ✓ Dashboard criado")

# ═══════════════════════════════════════════════════════════════════════════
# ABA 2 — AÇÕES
# ═══════════════════════════════════════════════════════════════════════════
print("📈 Criando aba Ações...")
ws2 = get_or_create_sheet(sh, "📈 Ações", rows=50, cols=10)

acoes_data = [
    ["CARTEIRA DE AÇÕES — CLEAR CORRETORA", "", "", "", "", "", "", "", "", ""],
    [""],
    ["Ticker", "Qtd", "Preço Atual", "Valor Total", "DY Anual", "Div. Anual", "Div. Mensal", "P/L", "P/VP", "Setor"],
    ["ITUB4",  46,  "R$ 43,00", "R$ 1.978,00", "7%",  "R$ 138,46", "R$ 11,54", "7,5", "1,5",  "Bancos"],
    ["PETR4",  37,  "R$ 44,90", "R$ 1.661,30", "13%", "R$ 215,97", "R$ 17,99", "5,0", "1,1",  "Energia"],
    ["TAEE11", 14,  "R$ 42,90", "R$ 600,60",   "10%", "R$ 60,06",  "R$ 5,01",  "9,0", "1,8",  "Energia"],
    ["BBAS3",  18,  "R$ 24,60", "R$ 442,80",   "10%", "R$ 44,28",  "R$ 3,69",  "4,5", "0,73", "Bancos"],
    ["BBSE3",  11,  "R$ 34,90", "R$ 383,90",   "7%",  "R$ 26,87",  "R$ 2,24",  "15,0","2,5",  "Seguros"],
    ["ITSA4",  28,  "R$ 13,50", "R$ 378,00",   "6%",  "R$ 22,68",  "R$ 1,89",  "8,0", "1,4",  "Holdings"],
    ["EGIE3",  11,  "R$ 32,00", "R$ 352,00",   "8%",  "R$ 28,16",  "R$ 2,35",  "12,0","1,9",  "Energia"],
    ["ISAE3",  9,   "R$ 32,90", "R$ 296,10",   "8%",  "R$ 23,69",  "R$ 1,97",  "10,0","1,5",  "Energia"],
    ["VIVT3",  7,   "R$ 41,20", "R$ 288,40",   "7%",  "R$ 20,19",  "R$ 1,68",  "14,0","2,0",  "Telecom"],
    ["CPLE3",  18,  "R$ 14,40", "R$ 259,20",   "8%",  "R$ 20,74",  "R$ 1,73",  "8,0", "1,2",  "Energia"],
    ["VALE3",  2,   "R$ 79,30", "R$ 158,60",   "8%",  "R$ 12,69",  "R$ 1,06",  "7,0", "1,0",  "Mineração"],
    ["MDIA3",  7,   "R$ 22,40", "R$ 156,80",   "5%",  "R$ 7,84",   "R$ 0,65",  "12,0","1,8",  "Consumo"],
    ["TAEE4",  5,   "R$ 14,40", "R$ 72,00",    "10%", "R$ 7,20",   "R$ 0,60",  "9,0", "1,8",  "Energia"],
    ["CMIG4",  9,   "R$ 11,90", "R$ 107,10",   "10%", "R$ 10,71",  "R$ 0,89",  "6,0", "1,1",  "Energia"],
    ["TOTAL",  "",  "",         "=SUM(D4:D19)","",   "=SUM(F4:F19)","=SUM(G4:G19)","","",""],
    [""],
    ["ANÁLISE — OPORTUNIDADES DESTACADAS", "", "", "", "", "", "", "", "", ""],
    ["", "BBAS3: P/VP 0,73 — abaixo do patrimônio, excelente DY 10%", "", "", "", "", "", "", "", ""],
    ["", "ITUB4: RSI ~21 (sobrevendido), fundamentos sólidos", "", "", "", "", "", "", "", ""],
    ["", "WEGE3: RSI ~12 (extremo sobrevendido) — considerar para aporte", "", "", "", "", "", "", "", ""],
]

ws2.update('A1', acoes_data)

fmt2 = []
fmt2.append(('A1:J1', cell_format(bg=AZUL_ESCURO, bold=True, size=14, color=BRANCO, halign='CENTER')))
fmt2.append(('A3:J3', cell_format(bg=AZUL_ESCURO, bold=True, color=BRANCO, size=10, halign='CENTER')))
fmt2.append(('A20:J20', cell_format(bg=VERDE_MEDIO, bold=True, color=BRANCO)))
for i, row in enumerate(range(4, 19)):
    bg = CINZA_CLARO if i % 2 == 0 else BRANCO
    fmt2.append((f'A{row}:J{row}', cell_format(bg=bg)))
fmt2.append(('A19:J19', cell_format(bg=VERDE_CLARO, bold=True)))

apply_formats(ws2, fmt2)

dim2 = [
    merge_cells(ws2, 'A1:J1'),
    set_col_width(ws2, 0, 80),
    set_col_width(ws2, 1, 50),
    set_col_width(ws2, 2, 110),
    set_col_width(ws2, 3, 110),
    set_col_width(ws2, 4, 80),
    set_col_width(ws2, 5, 110),
    set_col_width(ws2, 6, 110),
    set_col_width(ws2, 7, 60),
    set_col_width(ws2, 8, 60),
    set_col_width(ws2, 9, 110),
    set_row_height(ws2, 0, 45),
]
ws2.spreadsheet.batch_update({"requests": dim2})
print("  ✓ Ações criado")

# ═══════════════════════════════════════════════════════════════════════════
# ABA 3 — FIIs
# ═══════════════════════════════════════════════════════════════════════════
print("🏢 Criando aba FIIs...")
ws3 = get_or_create_sheet(sh, "🏢 FIIs", rows=50, cols=9)

fiis_data = [
    ["CARTEIRA DE FIIs — CLEAR CORRETORA", "", "", "", "", "", "", "", ""],
    [""],
    ["Ticker", "Qtd", "Provento/cota", "Renda/mês", "P/VP", "DY Anual", "Tipo", "Gestor", "Qualidade"],
    ["KNCR11", 21,  "R$ 1,020", "R$ 21,42",  "0,98",  "12,2%", "CRI/CDI",   "Kinea",  "⭐⭐⭐⭐⭐"],
    ["MXRF11", 80,  "R$ 0,075", "R$ 6,00",   "0,97",  "9,0%",  "Híbrido",   "MaxCap", "⭐⭐⭐⭐"],
    ["BTLG11", 10,  "R$ 0,880", "R$ 8,80",   "1,02",  "10,6%", "Logística", "BTG",    "⭐⭐⭐⭐⭐"],
    ["CPTS11", 44,  "R$ 0,090", "R$ 3,96",   "0,94",  "10,8%", "CRI",       "Capitânia","⭐⭐⭐⭐"],
    ["HGLG11", 4,   "R$ 1,450", "R$ 5,80",   "0,99",  "17,4%", "Logística", "CSHG",   "⭐⭐⭐⭐⭐"],
    ["HGBS11", 14,  "R$ 0,180", "R$ 2,52",   "0,87",  "2,2%",  "Shopping",  "CSHG",   "⭐⭐⭐"],
    ["HGRE11", 3,   "R$ 0,550", "R$ 1,65",   "0,81",  "6,6%",  "Lajes Corp","CSHG",   "⭐⭐⭐"],
    ["KNRI11", 2,   "R$ 1,150", "R$ 2,30",   "0,92",  "13,8%", "Híbrido",   "Kinea",  "⭐⭐⭐⭐⭐"],
    ["RBRR11", 3,   "R$ 0,850", "R$ 2,55",   "0,93",  "10,2%", "CRI",       "RBR",    "⭐⭐⭐⭐"],
    ["VISC11", 2,   "R$ 0,850", "R$ 1,70",   "0,88",  "10,2%", "Shopping",  "Vinci",  "⭐⭐⭐⭐"],
    ["VILG11", 1,   "R$ 0,800", "R$ 0,80",   "0,90",  "9,6%",  "Logística", "Vinci",  "⭐⭐⭐⭐"],
    ["PSEC11", 1,   "R$ 0,550", "R$ 0,55",   "0,95",  "6,6%",  "CRI",       "Plural", "⭐⭐⭐"],
    ["VGHF11", 6,   "R$ 0,070", "R$ 0,42",   "0,96",  "8,4%",  "Hedge",     "Valora", "⭐⭐⭐"],
    ["VGIR11", 2,   "R$ 0,080", "R$ 0,16",   "0,97",  "9,6%",  "CRI/CDI",   "Valora", "⭐⭐⭐⭐"],
    ["TOTAL",  "",  "",         "=SUM(D4:D19)","",    "",      "",          "",       ""],
    [""],
    ["FIIs RECOMENDADOS PARA APORTE (R$ 12.600)", "", "", "", "", "", "", "", ""],
    ["Ticker",  "Valor sugerido", "Motivo", "", "", "", "", "", ""],
    ["VRTA11",  "R$ 4.000", "P/VP 0,85 — desconto raro para FII de qualidade", "", "", "", "", "", ""],
    ["HGLG11",  "R$ 3.500", "P/VP 0,99 — quase no par, DY 17% excepcional",   "", "", "", "", "", ""],
    ["MXRF11",  "R$ 3.000", "P/VP 0,97 — líquido, pagamento mensal",          "", "", "", "", "", ""],
    ["KNCR11",  "R$ 2.100", "CRI CDI — proteção inflação, alta qualidade",     "", "", "", "", "", ""],
]

ws3.update('A1', fiis_data)

fmt3 = []
fmt3.append(('A1:I1', cell_format(bg=VERDE_ESCURO, bold=True, size=14, color=BRANCO, halign='CENTER')))
fmt3.append(('A3:I3', cell_format(bg=VERDE_ESCURO, bold=True, color=BRANCO, size=10, halign='CENTER')))
fmt3.append(('A20:I20', cell_format(bg=VERDE_MEDIO, bold=True, color=BRANCO)))
fmt3.append(('A21:I21', cell_format(bg=AZUL_CLARO, bold=True, size=10)))
for i, row in enumerate(range(4, 19)):
    bg = VERDE_CLARO if i % 2 == 0 else BRANCO
    fmt3.append((f'A{row}:I{row}', cell_format(bg=bg)))
fmt3.append(('A19:I19', cell_format(bg=VERDE_CLARO, bold=True)))
for row in [22, 24]:
    fmt3.append((f'A{row}:I{row}', cell_format(bg=CINZA_CLARO)))

apply_formats(ws3, fmt3)

dim3 = [
    merge_cells(ws3, 'A1:I1'),
    set_col_width(ws3, 0, 80),
    set_col_width(ws3, 1, 50),
    set_col_width(ws3, 2, 120),
    set_col_width(ws3, 3, 110),
    set_col_width(ws3, 4, 70),
    set_col_width(ws3, 5, 90),
    set_col_width(ws3, 6, 100),
    set_col_width(ws3, 7, 100),
    set_col_width(ws3, 8, 120),
    set_row_height(ws3, 0, 45),
]
ws3.spreadsheet.batch_update({"requests": dim3})
print("  ✓ FIIs criado")

# ═══════════════════════════════════════════════════════════════════════════
# ABA 4 — RENDA FIXA
# ═══════════════════════════════════════════════════════════════════════════
print("💰 Criando aba Renda Fixa...")
ws4 = get_or_create_sheet(sh, "💰 Renda Fixa", rows=40, cols=8)

rf_data = [
    ["RENDA FIXA & RESERVA DE EMERGÊNCIA", "", "", "", "", "", "", ""],
    [""],
    ["Aplicação", "Corretora", "Valor", "Taxa", "Rendimento/mês", "Liquidez", "Vencimento", "Objetivo"],
    ["Reserva Emergência",      "XP",    "R$ 65.000",  "CDI 100%",     "R$ 769/mês",   "Diária", "Sem vencimento", "Reserva"],
    ["Herança (a alocar)",      "XP",    "R$ 91.000",  "CDI ~100%",    "R$ 1.077/mês", "Diária", "Sem vencimento", "Aguardando alocação"],
    [""],
    ["PLANO DE ALOCAÇÃO DA RESERVA (R$ 55.000)", "", "", "", "", "", "", ""],
    ["Destino",               "Valor",      "Taxa",          "Rendimento/mês", "Liquidez", "Prazo", "", ""],
    ["Tesouro Selic 2027",    "R$ 30.000",  "Selic 14,25%",  "R$ 356/mês",     "D+1",      "2027",  "", ""],
    ["CDB Banco Médio",       "R$ 25.000",  "CDI 105%",      "R$ 312/mês",     "Diária",   "2027",  "", ""],
    ["TOTAL RESERVA",         "R$ 55.000",  "",              "R$ 668/mês",     "",         "",      "", ""],
    [""],
    ["PLANO DE ALOCAÇÃO RENDA FIXA LONGA (R$ 14.400)", "", "", "", "", "", "", ""],
    ["Destino",               "Valor",      "Taxa",          "Rendimento/mês", "Liquidez", "Prazo", "", ""],
    ["Tesouro IPCA+ 2030",    "R$ 8.000",   "IPCA+6,0%",     "R$ 90/mês",      "Mercado",  "2030",  "", ""],
    ["CDB IPCA+ Médio",       "R$ 6.400",   "IPCA+5,5%",     "R$ 72/mês",      "No venc.", "3 anos","", ""],
    ["TOTAL RF LONGA",        "R$ 14.400",  "",              "R$ 162/mês",     "",         "",      "", ""],
    [""],
    ["SIMULAÇÃO RESERVA COMPLETA (R$ 120.000)", "", "", "", "", "", "", ""],
    ["Selic atual: 14,25% a.a.", "", "", "", "", "", "", ""],
    ["Rendimento mensal:",     "R$ 1.424",   "", "", "", "", "", ""],
    ["Rendimento anual:",      "R$ 17.100",  "", "", "", "", "", ""],
    ["Imposto IR (22,5%):",    "R$ 3.848",   "", "", "", "", "", ""],
    ["Rendimento líquido/ano:","R$ 13.252",  "", "", "", "", "", ""],
]

ws4.update('A1', rf_data)

fmt4 = []
fmt4.append(('A1:H1', cell_format(bg=LARANJA, bold=True, size=14, color=BRANCO, halign='CENTER')))
fmt4.append(('A3:H3', cell_format(bg=LARANJA, bold=True, color=BRANCO, size=10, halign='CENTER')))
for row in [7, 13, 19]:
    fmt4.append((f'A{row}:H{row}', cell_format(bg=LARANJA, bold=True, color=BRANCO)))
for row in [8, 14]:
    fmt4.append((f'A{row}:H{row}', cell_format(bg=AMARELO, bold=True)))
for row in [11, 17]:
    fmt4.append((f'A{row}:H{row}', cell_format(bg=VERDE_CLARO, bold=True)))
for row in [4, 9, 15, 21, 23]:
    fmt4.append((f'A{row}:H{row}', cell_format(bg=CINZA_CLARO)))

apply_formats(ws4, fmt4)
dim4 = [
    merge_cells(ws4, 'A1:H1'),
    set_col_width(ws4, 0, 220),
    set_col_width(ws4, 1, 120),
    set_col_width(ws4, 2, 130),
    set_col_width(ws4, 3, 150),
    set_col_width(ws4, 4, 100),
    set_col_width(ws4, 5, 80),
    set_col_width(ws4, 6, 120),
    set_col_width(ws4, 7, 170),
    set_row_height(ws4, 0, 45),
]
ws4.spreadsheet.batch_update({"requests": dim4})
print("  ✓ Renda Fixa criado")

# ═══════════════════════════════════════════════════════════════════════════
# ABA 5 — PLANO DE ALOCAÇÃO
# ═══════════════════════════════════════════════════════════════════════════
print("🎯 Criando aba Plano de Alocação...")
ws5 = get_or_create_sheet(sh, "🎯 Plano Alocação", rows=50, cols=8)

plano_data = [
    ["PLANO DE ALOCAÇÃO INTELIGENTE — ALEXANDRE QUEIROZ", "", "", "", "", "", "", ""],
    ["Março 2026 | Herança R$ 91.000 | Perfil: Conservador/Renda", "", "", "", "", "", "", ""],
    [""],
    ["CONTEXTO PESSOAL", "", "", "", "", "", "", ""],
    ["Situação",          "Detalhe", "", "", "", "", "", ""],
    ["Idade",             "43 anos", "", "", "", "", "", ""],
    ["Estado civil",      "Casado", "", "", "", "", "", ""],
    ["Filha",             "Nascendo em ~20 dias (março 2026)", "", "", "", "", "", ""],
    ["Moradia",           "Aluguel", "", "", "", "", "", ""],
    ["Gastos mensais",    "R$ 20.000/mês", "", "", "", "", "", ""],
    ["Renda passiva atual","R$ 342,74/mês (1,7% das despesas)", "", "", "", "", "", ""],
    ["Meta de longo prazo","Renda passiva ≥ R$ 20.000/mês (FIRE)", "", "", "", "", "", ""],
    [""],
    ["PASSO A PASSO — PRÓXIMAS AÇÕES", "", "", "", "", "", "", ""],
    ["Prioridade", "Ação", "Valor", "Prazo", "Onde", "Por quê", "", ""],
    ["🔴 URGENTE", "Completar reserva emergência",  "R$ 55.000", "Imediato",    "XP — Tesouro Selic ou CDB",       "Filha nascendo, segurança máxima", "", ""],
    ["🟡 CURTO",   "Alocar Renda Fixa longa",       "R$ 14.400", "1-2 semanas", "XP — Tesouro IPCA+ 2030",        "Proteção inflação, liquidez em emergência", "", ""],
    ["🟡 CURTO",   "Aportar em FIIs selecionados",  "R$ 12.600", "2-4 semanas", "Clear — VRTA11, HGLG11, MXRF11", "DY alto, P/VP abaixo do par", "", ""],
    ["🟢 MÉDIO",   "Aportar em Ações selecionadas", "R$ 9.000",  "1-2 meses",   "Clear — BBAS3, WEGE3, SUZB3",    "RSI sobrevendido, fundamentos sólidos", "", ""],
    ["🔵 LONGO",   "Reinvestir dividendos",         "Mensal",    "Sempre",      "Clear/XP",                       "Juros compostos = aceleração do patrimônio", "", ""],
    [""],
    ["ESTRATÉGIA DE INVESTIMENTO POR PERFIL", "", "", "", "", "", "", ""],
    ["Ativo",        "% Ideal", "% Atual", "Status", "Comentário", "", "", ""],
    ["Reserva Emerg.","54,1%",  "58,6%",   "✅ OK",   "Após alocação estará em 54,1% (R$120k/R$222k)", "", "", ""],
    ["Renda Fixa",    "6,5%",   "0%",      "⚠️ Falta","Tesouro IPCA+ protege contra inflação", "", "", ""],
    ["FIIs",          "5,7%",   "0%",      "⚠️ Falta","KNCR11, HGLG11, VRTA11 — pagam mensalmente", "", "", ""],
    ["Ações",         "9,9%",   "11,7%",   "✅ OK",   "Manter carteira diversificada, focar DY", "", "", ""],
    [""],
    ["CAMINHO PARA A INDEPENDÊNCIA FINANCEIRA", "", "", "", "", "", "", ""],
    ["Renda necessária:",    "R$ 20.000/mês", "", "", "", "", "", ""],
    ["Capital necessário:",  "R$ 3.000.000 (Regra dos 4%)", "", "", "", "", "", ""],
    ["Capital atual:",       "R$ 111.100", "", "", "", "", "", ""],
    ["Gap:",                 "R$ 2.888.900", "", "", "", "", "", ""],
    ["Com aporte mensal R$ 2.000 + reinvestimento → ~25-30 anos", "", "", "", "", "", "", ""],
    ["Com aporte mensal R$ 5.000 + reinvestimento → ~18-22 anos", "", "", "", "", "", "", ""],
    ["💡 Foque em aumentar renda e reduzir gastos para acelerar!", "", "", "", "", "", "", ""],
]

ws5.update('A1', plano_data)

fmt5 = []
fmt5.append(('A1:H1', cell_format(bg=VERDE_ESCURO, bold=True, size=14, color=BRANCO, halign='CENTER')))
fmt5.append(('A2:H2', cell_format(bg=AZUL_ESCURO, bold=False, size=10, color=BRANCO, halign='CENTER')))
for row in [4, 14, 22, 29]:
    fmt5.append((f'A{row}:H{row}', cell_format(bg=VERDE_MEDIO, bold=True, color=BRANCO)))
for row in [5, 15, 23]:
    fmt5.append((f'A{row}:H{row}', cell_format(bg=AZUL_CLARO, bold=True)))
for i, row in enumerate(range(6, 13)):
    bg = CINZA_CLARO if i % 2 == 0 else BRANCO
    fmt5.append((f'A{row}:H{row}', cell_format(bg=bg)))
for row in [16, 18, 20]:
    fmt5.append((f'A{row}:H{row}', cell_format(bg=CINZA_CLARO)))
for row in [24, 26]:
    fmt5.append((f'A{row}:H{row}', cell_format(bg=CINZA_CLARO)))
fmt5.append(('A35:H35', cell_format(bg=AMARELO, bold=True)))

apply_formats(ws5, fmt5)
dim5 = [
    merge_cells(ws5, 'A1:H1'),
    merge_cells(ws5, 'A2:H2'),
    set_col_width(ws5, 0, 160),
    set_col_width(ws5, 1, 200),
    set_col_width(ws5, 2, 120),
    set_col_width(ws5, 3, 120),
    set_col_width(ws5, 4, 200),
    set_col_width(ws5, 5, 200),
    set_row_height(ws5, 0, 50),
    set_row_height(ws5, 1, 30),
]
ws5.spreadsheet.batch_update({"requests": dim5})
print("  ✓ Plano de Alocação criado")

# ═══════════════════════════════════════════════════════════════════════════
# ABA 6 — HISTÓRICO
# ═══════════════════════════════════════════════════════════════════════════
print("📅 Criando aba Histórico...")
ws6 = get_or_create_sheet(sh, "📅 Histórico", rows=100, cols=8)

hist_data = [
    ["HISTÓRICO DE APORTES & EVOLUÇÃO PATRIMONIAL", "", "", "", "", "", "", ""],
    [""],
    ["Data", "Evento", "Valor", "Patrimônio Total", "Renda Passiva/mês", "Observação", "", ""],
    ["Jan/2026", "Carteira inicial (Clear)",    "R$ 13.000",  "R$ 13.000",   "R$ 342,74", "14 ações + 14 FIIs", "", ""],
    ["Jan/2026", "Reserva emergência (XP)",     "R$ 65.000",  "R$ 78.000",   "R$ 342,74", "3,25 meses de cobertura", "", ""],
    ["Mar/2026", "Herança recebida (1ª parte)", "R$ 45.000",  "R$ 123.000",  "R$ 342,74", "Depositado na XP", "", ""],
    ["Mar/2026", "Herança recebida (2ª parte)", "R$ 46.000",  "R$ 169.000",  "R$ 342,74", "Depositado na XP", "", ""],
    ["Mar/2026", "Total atual (pré-alocação)",  "R$ 0",       "R$ 111.100",  "R$ 342,74", "Patrimônio investido real", "", ""],
    [""],
    ["PRÓXIMOS LANÇAMENTOS (preencher após executar)", "", "", "", "", "", "", ""],
    ["Data", "Evento", "Valor", "Patrimônio Total", "Renda Passiva/mês", "Observação", "", ""],
    ["___/2026", "Reserva → Tesouro Selic",     "R$ 55.000",  "",  "", "Completar 6 meses", "", ""],
    ["___/2026", "RF → Tesouro IPCA+ 2030",     "R$ 14.400",  "",  "", "Proteção inflação", "", ""],
    ["___/2026", "FIIs → VRTA11/HGLG11/MXRF11","R$ 12.600",  "",  "", "Renda mensal extra", "", ""],
    ["___/2026", "Ações → BBAS3/WEGE3/SUZB3",  "R$ 9.000",   "",  "", "RSI sobrevendido", "", ""],
    [""],
    ["METAS DE ACOMPANHAMENTO", "", "", "", "", "", "", ""],
    ["Meta", "Valor alvo", "Status", "", "", "", "", ""],
    ["Reserva 6 meses",     "R$ 120.000",   "🔴 Em progresso (R$65k atual)", "", "", "", "", ""],
    ["Renda passiva R$1.000/mês", "R$ 1.000/mês", "⚠️ R$ 342 atual — 34,3%", "", "", "", "", ""],
    ["Renda passiva R$5.000/mês", "R$ 5.000/mês", "⚠️ R$ 342 atual — 6,8%", "", "", "", "", ""],
    ["Renda passiva R$20.000/mês","R$ 20.000/mês","⚠️ R$ 342 atual — 1,7%", "", "", "", "", ""],
    ["Patrimônio R$500.000",      "R$ 500.000",   "⚠️ R$111k atual — 22,2%",  "", "", "", "", ""],
    ["FIRE completo (R$3M)",      "R$ 3.000.000", "⚠️ R$111k atual — 3,7%",   "", "", "", "", ""],
]

ws6.update('A1', hist_data)

fmt6 = []
fmt6.append(('A1:H1', cell_format(bg=AZUL_ESCURO, bold=True, size=14, color=BRANCO, halign='CENTER')))
for row in [3, 11]:
    fmt6.append((f'A{row}:H{row}', cell_format(bg=AZUL_ESCURO, bold=True, color=BRANCO, size=10)))
for row in [10, 17]:
    fmt6.append((f'A{row}:H{row}', cell_format(bg=VERDE_MEDIO, bold=True, color=BRANCO)))
fmt6.append(('A18:H18', cell_format(bg=AZUL_CLARO, bold=True)))
for i, row in enumerate(range(4, 9)):
    bg = CINZA_CLARO if i % 2 == 0 else BRANCO
    fmt6.append((f'A{row}:H{row}', cell_format(bg=bg)))
for i, row in enumerate(range(12, 16)):
    bg = CINZA_CLARO if i % 2 == 0 else BRANCO
    fmt6.append((f'A{row}:H{row}', cell_format(bg=bg)))
for row in [19, 21, 23]:
    fmt6.append((f'A{row}:H{row}', cell_format(bg=CINZA_CLARO)))

apply_formats(ws6, fmt6)
dim6 = [
    merge_cells(ws6, 'A1:H1'),
    set_col_width(ws6, 0, 100),
    set_col_width(ws6, 1, 230),
    set_col_width(ws6, 2, 120),
    set_col_width(ws6, 3, 140),
    set_col_width(ws6, 4, 160),
    set_col_width(ws6, 5, 200),
    set_row_height(ws6, 0, 45),
]
ws6.spreadsheet.batch_update({"requests": dim6})
print("  ✓ Histórico criado")

# ── Reordena abas ─────────────────────────────────────────────────────────
print("\n🔄 Finalizando...")
sheet_order = ["📊 Dashboard", "📈 Ações", "🏢 FIIs", "💰 Renda Fixa", "🎯 Plano Alocação", "📅 Histórico"]
worksheets = {ws.title: ws for ws in sh.worksheets()}

# Remove a aba padrão "Página1" ou "Sheet1" se existir
for default_name in ["Página1", "Sheet1", "Plan1"]:
    if default_name in worksheets:
        try:
            sh.del_worksheet(worksheets[default_name])
            print(f"  ✓ Aba '{default_name}' removida")
        except:
            pass

print(f"\n✅ CONCLUÍDO!")
print(f"   Planilha: https://docs.google.com/spreadsheets/d/{SHEET_ID}")
print(f"   6 abas criadas com dashboard completo de investimentos")
print(f"\n⚠️  IMPORTANTE: Compartilhe a planilha com: {SA_EMAIL}")
print(f"   Ou acesse o link acima — se não tiver permissão, use o botão 'Compartilhar'")
