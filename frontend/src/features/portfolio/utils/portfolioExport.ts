/**
 * Portfolio export utilities — no external libraries required.
 *
 * Formats:
 *  - CSV  → standard comma-separated, UTF-8 BOM for Excel
 *  - XLS  → XML Spreadsheet 2003 (opens in Excel / LibreOffice as .xls)
 *  - PDF  → opens a print window with formatted HTML
 *  - Clipboard → tab-separated (paste into Excel / Google Sheets)
 */
import { PnLResponse, PositionResponse } from "@/features/portfolio/types";

// ── helpers ─────────────────────────────────────────────────────────────────

function fmtNum(v: string | null | undefined, decimals = 2): string {
  if (v == null) return "";
  const n = parseFloat(v);
  return isNaN(n) ? "" : n.toFixed(decimals);
}

function fmtBRL(v: string | null | undefined): string {
  if (v == null) return "";
  const n = parseFloat(v);
  return isNaN(n) ? "" : `R$ ${n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const ASSET_LABELS: Record<string, string> = {
  acao: "Ação", fii: "FII", renda_fixa: "Renda Fixa", bdr: "BDR", etf: "ETF",
};

function assetLabel(cls: string) {
  return ASSET_LABELS[cls] ?? cls;
}

const HEADERS = [
  "Ticker", "Classe", "Qtd", "Preço Médio (R$)", "Custo Total (R$)",
  "Preço Atual (R$)", "P&L Não Realiz. (R$)", "P&L %",
];

function positionRow(pos: PositionResponse): string[] {
  return [
    pos.ticker,
    assetLabel(pos.asset_class),
    fmtNum(pos.quantity, 4),
    fmtNum(pos.cmp),
    fmtNum(pos.total_cost),
    pos.current_price_stale ? "" : fmtNum(pos.current_price),
    fmtNum(pos.unrealized_pnl),
    fmtNum(pos.unrealized_pnl_pct, 4),
  ];
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ── CSV ─────────────────────────────────────────────────────────────────────

function escapeCsv(v: string): string {
  if (v.includes(",") || v.includes('"') || v.includes("\n")) {
    return `"${v.replace(/"/g, '""')}"`;
  }
  return v;
}

export function exportPortfolioCsv(pnl: PnLResponse) {
  const rows: string[][] = [HEADERS, ...pnl.positions.map(positionRow)];
  // Summary footer
  rows.push([]);
  rows.push(["Total investido", fmtBRL(pnl.total_invested)]);
  rows.push(["Valor atual", fmtBRL(pnl.total_portfolio_value)]);
  rows.push(["P&L realizado", fmtBRL(pnl.realized_pnl_total)]);
  rows.push(["P&L não realizado", fmtBRL(pnl.unrealized_pnl_total)]);
  if (pnl.total_return_pct) rows.push(["Retorno total %", fmtNum(pnl.total_return_pct, 2) + "%"]);

  const csv =
    "\uFEFF" + // UTF-8 BOM → Excel opens with correct encoding
    rows.map((r) => r.map(escapeCsv).join(",")).join("\r\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const date = new Date().toISOString().slice(0, 10);
  triggerDownload(blob, `portfolio_${date}.csv`);
}

// ── XLS (XML Spreadsheet 2003) ───────────────────────────────────────────────

function xmlCell(value: string, type: "String" | "Number" = "String"): string {
  const safe = value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return `<Cell><Data ss:Type="${type}">${safe}</Data></Cell>`;
}

function xlsRow(cells: string[]): string {
  const mapped = cells.map((v) => {
    const n = parseFloat(v.replace(/[^\d.,-]/g, "").replace(",", "."));
    return !isNaN(n) && v.replace(/[^\d.,-]/g, "").length > 0 && !/[a-zA-Z%]/.test(v)
      ? xmlCell(String(n), "Number")
      : xmlCell(v);
  });
  return `<Row>${mapped.join("")}</Row>`;
}

export function exportPortfolioXls(pnl: PnLResponse) {
  const dataRows = [HEADERS, ...pnl.positions.map(positionRow)];

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
  xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"
  xmlns:x="urn:schemas-microsoft-com:office:excel">
  <Styles>
    <Style ss:ID="header">
      <Font ss:Bold="1"/>
      <Interior ss:Color="#E8F0FE" ss:Pattern="Solid"/>
    </Style>
    <Style ss:ID="pos">
      <Font ss:Color="#16A34A"/>
    </Style>
    <Style ss:ID="neg">
      <Font ss:Color="#DC2626"/>
    </Style>
  </Styles>
  <Worksheet ss:Name="Portfolio">
    <Table>
      <Column ss:Width="80"/>
      <Column ss:Width="90"/>
      <Column ss:Width="70"/>
      <Column ss:Width="110"/>
      <Column ss:Width="110"/>
      <Column ss:Width="110"/>
      <Column ss:Width="130"/>
      <Column ss:Width="60"/>
      <Row ss:StyleID="header">${HEADERS.map((h) => xmlCell(h)).join("")}</Row>
      ${dataRows.slice(1).map((r) => xlsRow(r)).join("\n      ")}
      <Row/>
      <Row><Cell ss:StyleID="header"><Data ss:Type="String">Resumo</Data></Cell></Row>
      ${xlsRow(["Total investido", fmtNum(pnl.total_invested)])}
      ${xlsRow(["Valor atual", fmtNum(pnl.total_portfolio_value)])}
      ${xlsRow(["P&L realizado", fmtNum(pnl.realized_pnl_total)])}
      ${xlsRow(["P&L não realizado", fmtNum(pnl.unrealized_pnl_total)])}
      ${pnl.total_return_pct ? xlsRow(["Retorno total %", fmtNum(pnl.total_return_pct, 2)]) : ""}
    </Table>
  </Worksheet>
</Workbook>`;

  const blob = new Blob([xml], { type: "application/vnd.ms-excel;charset=utf-8" });
  const date = new Date().toISOString().slice(0, 10);
  triggerDownload(blob, `portfolio_${date}.xls`);
}

// ── PDF (print window) ───────────────────────────────────────────────────────

export function exportPortfolioPdf(pnl: PnLResponse) {
  const date = new Date().toLocaleDateString("pt-BR");
  const rows = pnl.positions.map(positionRow);

  const tableRows = rows
    .map((r) => {
      const pnlVal = parseFloat(r[6] ?? "0");
      const color = pnlVal >= 0 ? "#16a34a" : "#dc2626";
      return `<tr>
        <td>${r[0]}</td>
        <td>${r[1]}</td>
        <td style="text-align:right">${r[2]}</td>
        <td style="text-align:right">${r[3]}</td>
        <td style="text-align:right">${r[4]}</td>
        <td style="text-align:right">${r[5] || "—"}</td>
        <td style="text-align:right;color:${color}">${r[6]}</td>
        <td style="text-align:right;color:${color}">${r[7]}%</td>
      </tr>`;
    })
    .join("");

  const html = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>InvestIQ — Portfolio ${date}</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, Arial, sans-serif; font-size: 11px; color: #111; padding: 20px; }
  h1 { font-size: 16px; margin-bottom: 4px; }
  .subtitle { color: #666; margin-bottom: 16px; font-size: 10px; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 16px; }
  th { background: #e8f0fe; font-weight: 700; padding: 6px 8px; text-align: left; border: 1px solid #c5d3f0; font-size: 10px; }
  td { padding: 5px 8px; border: 1px solid #e5e7eb; }
  tr:nth-child(even) td { background: #f9fafb; }
  .summary { margin-top: 12px; display: flex; gap: 24px; flex-wrap: wrap; }
  .summary-item { background: #f3f4f6; border-radius: 6px; padding: 8px 14px; }
  .summary-item .label { font-size: 9px; color: #666; text-transform: uppercase; letter-spacing: .5px; }
  .summary-item .value { font-size: 13px; font-weight: 700; margin-top: 2px; }
  .pos { color: #16a34a; }
  .neg { color: #dc2626; }
  @media print { body { padding: 0; } }
</style>
</head>
<body>
<h1>InvestIQ — Carteira de Investimentos</h1>
<div class="subtitle">Gerado em ${date} · ${pnl.positions.length} posições</div>
<table>
  <thead><tr>${HEADERS.map((h) => `<th>${h}</th>`).join("")}</tr></thead>
  <tbody>${tableRows}</tbody>
</table>
<div class="summary">
  <div class="summary-item"><div class="label">Total investido</div><div class="value">${fmtBRL(pnl.total_invested)}</div></div>
  <div class="summary-item"><div class="label">Valor atual</div><div class="value">${fmtBRL(pnl.total_portfolio_value)}</div></div>
  <div class="summary-item"><div class="label">P&amp;L realizado</div><div class="value ${parseFloat(pnl.realized_pnl_total ?? "0") >= 0 ? "pos" : "neg"}">${fmtBRL(pnl.realized_pnl_total)}</div></div>
  <div class="summary-item"><div class="label">P&amp;L não realizado</div><div class="value ${parseFloat(pnl.unrealized_pnl_total ?? "0") >= 0 ? "pos" : "neg"}">${fmtBRL(pnl.unrealized_pnl_total)}</div></div>
  ${pnl.total_return_pct ? `<div class="summary-item"><div class="label">Retorno total</div><div class="value ${parseFloat(pnl.total_return_pct) >= 0 ? "pos" : "neg"}">${fmtNum(pnl.total_return_pct, 2)}%</div></div>` : ""}
</div>
</body>
</html>`;

  const win = window.open("", "_blank", "width=1000,height=700");
  if (!win) {
    alert("Popups bloqueados — libere popups para exportar PDF.");
    return;
  }
  win.document.write(html);
  win.document.close();
  win.focus();
  setTimeout(() => win.print(), 500);
}

// ── Clipboard (tab-separated) ────────────────────────────────────────────────

export async function copyPortfolioToClipboard(pnl: PnLResponse): Promise<number> {
  const rows = [HEADERS, ...pnl.positions.map(positionRow)];
  const tsv = rows.map((r) => r.join("\t")).join("\n");
  await navigator.clipboard.writeText(tsv);
  return pnl.positions.length;
}
