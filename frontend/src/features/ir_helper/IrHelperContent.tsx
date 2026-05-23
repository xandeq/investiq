"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import {
  Calculator,
  TrendDown,
  TrendUp,
  Receipt,
  Warning,
  CheckCircle,
  FileText,
  Copy,
  Check,
  Scissors,
} from "@phosphor-icons/react";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

// ── Types ─────────────────────────────────────────────────────────────────────

interface IrSummary {
  month: string;
  total_vendas: number;
  lucro_bruto: number;
  prejuizo_acumulado: number;
  lucro_liquido: number;
  isento: boolean;
  aliquota: number;
  ir_devido: number;
  darf_gerado: boolean;
  darf_valor: number;
  transactions_count: number;
  transactions: {
    id: string;
    ticker: string;
    date: string;
    quantity: number;
    unit_price: number;
    total_value: number;
    gross_profit: number | null;
  }[];
}

interface HistoryRow {
  month: string;
  total_vendas: number;
  lucro_bruto: number;
  lucro_liquido: number;
  isento: boolean;
  ir_devido: number;
  darf_gerado: boolean;
}

interface DeclarationItem {
  ticker: string;
  asset_class: string;
  grupo: string;
  codigo: string;
  descricao_codigo: string;
  discriminacao: string;
  situacao_ano_anterior: number;
  situacao_ano_atual: number;
  quantidade_atual: number;
  custo_medio_atual: number;
}

interface Declaration {
  year: number;
  reference_date: string;
  total_declarado_atual: number;
  total_declarado_anterior: number;
  items: DeclarationItem[];
  instrucoes: {
    ficha: string;
    cnpj_b3: string;
    pais: string;
    nota: string;
  };
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(value: number) {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function currentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function currentYear() {
  // DIRPF is filed for the previous year
  return new Date().getFullYear() - 1;
}

// ── Copy button ───────────────────────────────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <button
      onClick={copy}
      className="ml-1 inline-flex items-center text-zinc-400 hover:text-zinc-700 transition-colors"
      title="Copiar"
    >
      {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
}

// ── DARF Tab ──────────────────────────────────────────────────────────────────

function DarfTab() {
  const [month, setMonth] = useState(currentMonth());

  const { data: summary, isLoading, error } = useQuery<IrSummary>({
    queryKey: ["ir-helper", "summary", month],
    queryFn: () => apiClient(`/ir-helper/summary?month=${month}`),
    staleTime: 60_000,
  });

  const { data: history = [] } = useQuery<HistoryRow[]>({
    queryKey: ["ir-helper", "history"],
    queryFn: () => apiClient("/ir-helper/history"),
    staleTime: 60_000,
  });

  return (
    <div className="space-y-6">
      {/* Month selector */}
      <div className="flex items-center gap-2">
        <label className="text-sm font-medium text-zinc-700">Mês</label>
        <input
          type="month"
          value={month}
          onChange={(e) => setMonth(e.target.value)}
          className="bg-zinc-100 border-0 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
        />
      </div>

      {isLoading && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((n) => (
            <ShimmerSkeleton key={n} className="h-24 rounded-xl" />
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-lg bg-red-50 border-l-4 border-red-500 p-4 text-sm text-red-600 flex gap-2">
          <Warning className="h-4 w-4 shrink-0 mt-0.5" weight="fill" />
          Erro ao carregar dados do IR Helper.
        </div>
      )}

      {summary && (
        <>
          {/* Status badge */}
          <div className="flex items-center gap-3">
            {summary.isento ? (
              <div className="flex items-center gap-2 bg-emerald-100 text-emerald-700 px-4 py-2 rounded-full font-semibold text-sm">
                <CheckCircle className="h-4 w-4" weight="fill" />
                ISENTO — vendas abaixo de R$20.000
              </div>
            ) : summary.darf_gerado ? (
              <div className="flex items-center gap-2 bg-red-100 text-red-700 px-4 py-2 rounded-full font-semibold text-sm">
                <Receipt className="h-4 w-4" />
                DARF DEVIDA — {fmt(summary.darf_valor)}
              </div>
            ) : (
              <div className="flex items-center gap-2 bg-amber-100 text-amber-700 px-4 py-2 rounded-full font-semibold text-sm">
                <Warning className="h-4 w-4" weight="fill" />
                IR abaixo de R$10 — sem DARF
              </div>
            )}
          </div>

          {/* Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white border border-zinc-200 rounded-xl p-5">
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Total Vendas</p>
              <p className="text-xl font-bold mt-1">{fmt(summary.total_vendas)}</p>
              <p className="text-xs text-zinc-500 mt-1">{summary.transactions_count} operações</p>
            </div>
            <div className="bg-white border border-zinc-200 rounded-xl p-5">
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Lucro Bruto</p>
              <p className={`text-xl font-bold mt-1 ${summary.lucro_bruto >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                {fmt(summary.lucro_bruto)}
              </p>
              {summary.lucro_bruto >= 0 ? (
                <TrendUp className="h-4 w-4 text-emerald-500 mt-1" />
              ) : (
                <TrendDown className="h-4 w-4 text-red-500 mt-1" />
              )}
            </div>
            <div className="bg-white border border-zinc-200 rounded-xl p-5">
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Prejuízo Acumulado</p>
              <p className={`text-xl font-bold mt-1 ${summary.prejuizo_acumulado > 0 ? "text-red-600" : "text-zinc-400"}`}>
                {summary.prejuizo_acumulado > 0 ? `−${fmt(summary.prejuizo_acumulado)}` : "—"}
              </p>
              <p className="text-xs text-zinc-500 mt-1">meses anteriores</p>
            </div>
            <div className={`rounded-xl p-5 border ${summary.darf_gerado ? "bg-red-50 border-red-200" : "bg-white border-zinc-200"}`}>
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">DARF</p>
              <p className={`text-xl font-bold mt-1 ${summary.darf_gerado ? "text-red-600" : "text-zinc-400"}`}>
                {summary.darf_gerado ? fmt(summary.darf_valor) : "—"}
              </p>
              <p className="text-xs text-zinc-500 mt-1">
                {summary.darf_gerado ? `Vencimento: último dia útil do mês` : "sem DARF"}
              </p>
            </div>
          </div>

          {/* DARF instructions */}
          {summary.darf_gerado && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
              <h3 className="font-semibold text-amber-800 flex items-center gap-2">
                <Receipt className="h-4 w-4" />
                Como pagar o DARF
              </h3>
              <ul className="mt-3 space-y-1.5 text-sm text-amber-700">
                <li>• Código de receita: <strong>6015</strong> (Renda Variável — Operações de Bolsa)</li>
                <li>• Valor: <strong>{fmt(summary.darf_valor)}</strong></li>
                <li>• Período de apuração: <strong>{summary.month}</strong></li>
                <li>• Vencimento: último dia útil do mês seguinte</li>
                <li>• Pagar via Receita Federal (e-CAC) ou internet banking</li>
              </ul>
            </div>
          )}

          {/* Rules */}
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
            <h3 className="font-semibold text-blue-800 flex items-center gap-2">
              <Warning className="h-4 w-4" weight="fill" />
              Regras do IR — Swing Trade
            </h3>
            <ul className="mt-3 space-y-1 text-sm text-blue-700">
              <li>• Isenção: total de vendas abaixo de <strong>R$20.000/mês</strong></li>
              <li>• Alíquota: <strong>15%</strong> sobre lucro líquido</li>
              <li>• Prejuízos de meses anteriores (sem isenção) são deduzidos do lucro</li>
              <li>• DARF emitida apenas se IR ≥ R$10,00</li>
              <li>• Day trade: alíquota diferente (20%) — não calculado aqui</li>
            </ul>
          </div>

          {/* Transactions */}
          {summary.transactions.length > 0 && (
            <div>
              <h3 className="text-base font-semibold mb-3">Vendas em {summary.month}</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-zinc-100 text-zinc-600">
                      <th className="text-left px-4 py-2.5 rounded-tl-lg font-semibold">Ticker</th>
                      <th className="text-left px-4 py-2.5 font-semibold">Data</th>
                      <th className="text-right px-4 py-2.5 font-semibold">Qtd</th>
                      <th className="text-right px-4 py-2.5 font-semibold">Preço Unit.</th>
                      <th className="text-right px-4 py-2.5 font-semibold">Total Venda</th>
                      <th className="text-right px-4 py-2.5 rounded-tr-lg font-semibold">Lucro/Prejuízo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.transactions.map((tx) => (
                      <tr key={tx.id} className="border-b border-zinc-100 hover:bg-zinc-50 transition-colors">
                        <td className="px-4 py-3 font-bold font-mono">{tx.ticker}</td>
                        <td className="px-4 py-3 text-zinc-600">
                          {new Date(tx.date + "T00:00:00").toLocaleDateString("pt-BR")}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums">{tx.quantity.toLocaleString("pt-BR")}</td>
                        <td className="px-4 py-3 text-right tabular-nums">{fmt(tx.unit_price)}</td>
                        <td className="px-4 py-3 text-right tabular-nums font-medium">{fmt(tx.total_value)}</td>
                        <td className="px-4 py-3 text-right tabular-nums font-semibold">
                          {tx.gross_profit !== null ? (
                            <span className={tx.gross_profit >= 0 ? "text-emerald-600" : "text-red-600"}>
                              {tx.gross_profit >= 0 ? "+" : ""}{fmt(tx.gross_profit)}
                            </span>
                          ) : (
                            <span className="text-zinc-400 text-xs">não informado</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* History */}
      {history.length > 0 && (
        <div>
          <h3 className="text-base font-semibold mb-3 flex items-center gap-2">
            <Calculator className="h-4 w-4" />
            Histórico Anual
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-zinc-100 text-zinc-600">
                  <th className="text-left px-4 py-2.5 rounded-tl-lg font-semibold">Mês</th>
                  <th className="text-right px-4 py-2.5 font-semibold">Total Vendas</th>
                  <th className="text-right px-4 py-2.5 font-semibold">Lucro Bruto</th>
                  <th className="text-right px-4 py-2.5 font-semibold">IR Devido</th>
                  <th className="text-right px-4 py-2.5 rounded-tr-lg font-semibold">Status</th>
                </tr>
              </thead>
              <tbody>
                {[...history].reverse().map((row) => (
                  <tr
                    key={row.month}
                    className={`border-b border-zinc-100 hover:bg-zinc-50 transition-colors cursor-pointer ${row.month === month ? "bg-blue-50" : ""}`}
                    onClick={() => setMonth(row.month)}
                  >
                    <td className="px-4 py-3 font-medium">{row.month}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{fmt(row.total_vendas)}</td>
                    <td className={`px-4 py-3 text-right tabular-nums font-medium ${row.lucro_bruto >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                      {fmt(row.lucro_bruto)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">{row.ir_devido > 0 ? fmt(row.ir_devido) : "—"}</td>
                    <td className="px-4 py-3 text-right">
                      {row.isento ? (
                        <span className="bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full text-xs font-medium">Isento</span>
                      ) : row.darf_gerado ? (
                        <span className="bg-red-100 text-red-700 px-2 py-0.5 rounded-full text-xs font-medium">DARF</span>
                      ) : (
                        <span className="bg-zinc-100 text-zinc-600 px-2 py-0.5 rounded-full text-xs font-medium">Sem DARF</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-zinc-400 mt-2">Clique em uma linha para ver os detalhes do mês.</p>
        </div>
      )}

      {!isLoading && summary && summary.transactions_count === 0 && history.length === 0 && (
        <div className="rounded-lg bg-zinc-100 p-12 text-center">
          <Calculator className="h-8 w-8 text-zinc-400 mx-auto mb-3" />
          <p className="font-semibold text-zinc-900">Nenhuma venda registrada</p>
          <p className="text-sm text-muted-foreground mt-1">
            Registre transações de venda na carteira para calcular o IR.
          </p>
        </div>
      )}
    </div>
  );
}

// ── Declaration Tab ────────────────────────────────────────────────────────────

const ASSET_CLASS_LABELS: Record<string, string> = {
  acao: "Ação",
  fii: "FII",
  bdr: "BDR",
  etf: "ETF",
  renda_fixa: "Renda Fixa",
};

function DeclarationTab() {
  const [year, setYear] = useState(currentYear());

  const { data, isLoading, error } = useQuery<Declaration>({
    queryKey: ["ir-helper", "declaration", year],
    queryFn: () => apiClient(`/ir-helper/declaration?year=${year}`),
    staleTime: 5 * 60_000,
  });

  const currentYr = new Date().getFullYear();
  const availableYears = Array.from({ length: 5 }, (_, i) => currentYr - 1 - i);

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex-1 min-w-60">
          <p className="text-sm font-semibold text-blue-800 flex items-center gap-2">
            <FileText className="h-4 w-4" />
            DIRPF {year + 1} — Ano-base {year}
          </p>
          <p className="text-xs text-blue-700 mt-1">
            Posições em 31/12/{year} com custo médio de aquisição (CMP). Use para preencher "Bens e Direitos".
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-zinc-700">Ano-base</label>
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="bg-zinc-100 border-0 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
          >
            {availableYears.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Brazil tax deadline alert */}
      {year === currentYr - 1 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 flex items-start gap-3">
          <Warning className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" weight="fill" />
          <div>
            <p className="text-sm font-semibold text-amber-800">Prazo da DIRPF {year + 1}: 30 de abril</p>
            <p className="text-xs text-amber-700 mt-0.5">
              Declare os valores abaixo na ficha "Bens e Direitos" do programa IRPF da Receita Federal.
            </p>
          </div>
        </div>
      )}

      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((n) => (
            <ShimmerSkeleton key={n} className="h-16 rounded-xl" />
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-lg bg-red-50 border-l-4 border-red-500 p-4 text-sm text-red-600 flex gap-2">
          <Warning className="h-4 w-4 shrink-0 mt-0.5" weight="fill" />
          Erro ao carregar declaração.
        </div>
      )}

      {data && data.items.length === 0 && (
        <div className="rounded-lg bg-zinc-100 p-12 text-center">
          <FileText className="h-8 w-8 text-zinc-400 mx-auto mb-3" />
          <p className="font-semibold text-zinc-900">Nenhum ativo em 31/12/{year}</p>
          <p className="text-sm text-muted-foreground mt-1">
            Não há posições abertas ou encerradas neste ano. Verifique se suas transações estão cadastradas.
          </p>
        </div>
      )}

      {data && data.items.length > 0 && (
        <>
          {/* Totals summary */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white border border-zinc-200 rounded-xl p-5">
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
                Situação em 31/12/{year - 1}
              </p>
              <p className="text-xl font-bold mt-1">{fmt(data.total_declarado_anterior)}</p>
              <p className="text-xs text-zinc-500 mt-1">ano anterior</p>
            </div>
            <div className="bg-white border border-zinc-200 rounded-xl p-5">
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
                Situação em 31/12/{year}
              </p>
              <p className="text-xl font-bold mt-1">{fmt(data.total_declarado_atual)}</p>
              <p className="text-xs text-zinc-500 mt-1">ano-base (declarar este valor)</p>
            </div>
          </div>

          {/* Main table */}
          <div>
            <h3 className="text-base font-semibold mb-3">
              Bens e Direitos — {data.items.length} {data.items.length === 1 ? "ativo" : "ativos"}
            </h3>
            <div className="overflow-x-auto rounded-xl border border-zinc-200">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-zinc-50 text-zinc-600 border-b border-zinc-200">
                    <th className="text-left px-4 py-3 font-semibold">Código RF</th>
                    <th className="text-left px-4 py-3 font-semibold">Ativo</th>
                    <th className="text-left px-4 py-3 font-semibold hidden md:table-cell">Tipo</th>
                    <th className="text-right px-4 py-3 font-semibold">Qtd em 31/12/{year}</th>
                    <th className="text-right px-4 py-3 font-semibold">Custo Médio</th>
                    <th className="text-right px-4 py-3 font-semibold">31/12/{year - 1}</th>
                    <th className="text-right px-4 py-3 font-semibold">31/12/{year}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((item) => {
                    const isLiquidated = item.situacao_ano_atual === 0 && item.quantidade_atual === 0;
                    return (
                      <tr
                        key={item.ticker}
                        className={`border-b border-zinc-100 hover:bg-zinc-50 transition-colors ${isLiquidated ? "opacity-60" : ""}`}
                      >
                        <td className="px-4 py-3">
                          <span className="font-mono text-xs bg-zinc-100 px-2 py-0.5 rounded">
                            {item.grupo}.{item.codigo}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="font-bold font-mono">{item.ticker}</div>
                          {isLiquidated && (
                            <div className="text-xs text-zinc-400">liquidado em {year}</div>
                          )}
                        </td>
                        <td className="px-4 py-3 text-zinc-600 hidden md:table-cell">
                          {ASSET_CLASS_LABELS[item.asset_class] ?? item.asset_class}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums font-mono text-sm">
                          {item.quantidade_atual > 0
                            ? item.quantidade_atual.toLocaleString("pt-BR", { maximumFractionDigits: 4 })
                            : "—"
                          }
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums font-mono text-sm">
                          {item.custo_medio_atual > 0 ? fmt(item.custo_medio_atual) : "—"}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums font-mono text-sm text-zinc-500">
                          {item.situacao_ano_anterior > 0 ? fmt(item.situacao_ano_anterior) : "—"}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums font-mono text-sm font-semibold">
                          {item.situacao_ano_atual > 0 ? fmt(item.situacao_ano_atual) : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
                <tfoot>
                  <tr className="bg-zinc-50 font-semibold border-t-2 border-zinc-200">
                    <td colSpan={5} className="px-4 py-3 text-xs text-zinc-500 uppercase tracking-wide">
                      Total
                    </td>
                    <td className="px-4 py-3 text-right font-mono">{fmt(data.total_declarado_anterior)}</td>
                    <td className="px-4 py-3 text-right font-mono text-blue-700">{fmt(data.total_declarado_atual)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
            <p className="text-xs text-zinc-400 mt-2">
              * Valores em custo de aquisição (CMP) — NÃO é valor de mercado.
            </p>
          </div>

          {/* Discriminação helper — per item */}
          <div>
            <h3 className="text-base font-semibold mb-3">
              Discriminação por ativo
              <span className="text-xs font-normal text-zinc-500 ml-2">— copie e cole no campo "Discriminação" do ReceitaNet</span>
            </h3>
            <div className="space-y-2">
              {data.items.filter(it => it.situacao_ano_atual > 0).map((item) => (
                <div key={item.ticker} className="bg-zinc-50 border border-zinc-200 rounded-lg px-4 py-3 flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-bold font-mono text-sm">{item.ticker}</span>
                      <span className="text-xs text-zinc-500 font-mono">Grupo {item.grupo} · Código {item.codigo}</span>
                    </div>
                    <p className="text-xs text-zinc-600 break-words leading-relaxed">{item.discriminacao}</p>
                  </div>
                  <CopyButton text={item.discriminacao} />
                </div>
              ))}
            </div>
          </div>

          {/* Instructions */}
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
            <h3 className="font-semibold text-blue-800 flex items-center gap-2 mb-3">
              <FileText className="h-4 w-4" />
              Como declarar no IRPF da Receita Federal
            </h3>
            <ol className="space-y-2 text-sm text-blue-700">
              <li>
                <strong>1.</strong> Abra o programa <strong>IRPF {year + 1}</strong> (baixe em gov.br/receitafederal).
              </li>
              <li>
                <strong>2.</strong> Acesse a ficha <strong>"Bens e Direitos"</strong> e clique em "Novo".
              </li>
              <li>
                <strong>3.</strong> Para cada ativo da tabela acima, informe:
                <ul className="ml-4 mt-1 space-y-0.5">
                  <li>• <strong>Grupo/Código:</strong> conforme coluna "Código RF"</li>
                  <li>• <strong>País:</strong> {data.instrucoes.pais}</li>
                  <li>• <strong>CNPJ:</strong> {data.instrucoes.cnpj_b3} (B3)</li>
                  <li>• <strong>Discriminação:</strong> use o texto copiável acima</li>
                  <li>• <strong>Situação em 31/12/{year - 1}:</strong> coluna "{year - 1}"</li>
                  <li>• <strong>Situação em 31/12/{year}:</strong> coluna "{year}" (custo de aquisição)</li>
                </ul>
              </li>
              <li>
                <strong>4.</strong> <Warning className="inline h-3.5 w-3.5 text-amber-500 align-middle -mt-0.5" weight="fill" /> {data.instrucoes.nota}
              </li>
            </ol>
          </div>
        </>
      )}
    </div>
  );
}

// ── Tax-Loss Harvesting Tab ──────────────────────────────────────────────────

interface HarvestItem {
  ticker: string;
  asset_class: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  unrealized_loss: number;
  unrealized_loss_pct: number;
  potential_tax_saving: number;
  has_gain_to_offset: boolean;
}

interface HarvestData {
  current_month: string;
  accumulated_gain_month: number;
  items: HarvestItem[];
  total_unrealized_loss: number;
  max_potential_saving: number;
}

const ASSET_LABELS: Record<string, string> = {
  acao: "Ação",
  fii: "FII",
  bdr: "BDR",
  etf: "ETF",
};

function TaxLossTab() {
  const { data, isLoading, error } = useQuery<HarvestData>({
    queryKey: ["ir-helper", "tax-loss"],
    queryFn: () => apiClient("/ir-helper/tax-loss-harvesting"),
    staleTime: 5 * 60_000,
  });

  return (
    <div className="space-y-6">
      {/* Explanation */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
        <h3 className="font-semibold text-blue-800 flex items-center gap-2 mb-2">
          <Scissors className="h-4 w-4" />
          O que é Tax-Loss Harvesting?
        </h3>
        <p className="text-sm text-blue-700">
          Vender posições com <strong>prejuízo latente</strong> antes do fim do mês para abater ganhos
          tributáveis — reduzindo ou zerando o DARF. O prejuízo realizado é deduzido do lucro do mesmo mês.
          Atenção: verifique a regra de wash-sale antes de recomprar o mesmo ativo.
        </p>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((n) => (
            <ShimmerSkeleton key={n} className="h-16 rounded-xl" />
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-lg bg-red-50 border-l-4 border-red-500 p-4 text-sm text-red-600 flex gap-2">
          <Warning className="h-4 w-4 shrink-0 mt-0.5" weight="fill" />
          Erro ao carregar dados de tax-loss harvesting.
        </div>
      )}

      {data && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-white border border-zinc-200 rounded-xl p-5">
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Ganho tributável — {data.current_month}</p>
              <p className={`text-xl font-bold mt-1 ${data.accumulated_gain_month > 0 ? "text-red-600" : "text-zinc-400"}`}>
                {data.accumulated_gain_month > 0 ? fmt(data.accumulated_gain_month) : "—"}
              </p>
              <p className="text-xs text-zinc-500 mt-1">lucro líquido do mês</p>
            </div>
            <div className="bg-white border border-zinc-200 rounded-xl p-5">
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Prejuízo latente total</p>
              <p className={`text-xl font-bold mt-1 ${data.total_unrealized_loss < 0 ? "text-orange-600" : "text-zinc-400"}`}>
                {data.total_unrealized_loss < 0 ? fmt(data.total_unrealized_loss) : "—"}
              </p>
              <p className="text-xs text-zinc-500 mt-1">{data.items.length} posição{data.items.length !== 1 ? "s" : ""} candidata{data.items.length !== 1 ? "s" : ""}</p>
            </div>
            <div className={`rounded-xl p-5 border ${data.max_potential_saving > 0 ? "bg-emerald-50 border-emerald-200" : "bg-white border-zinc-200"}`}>
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Economia potencial</p>
              <p className={`text-xl font-bold mt-1 ${data.max_potential_saving > 0 ? "text-emerald-700" : "text-zinc-400"}`}>
                {data.max_potential_saving > 0 ? fmt(data.max_potential_saving) : "—"}
              </p>
              <p className="text-xs text-zinc-500 mt-1">economia máxima em DARF</p>
            </div>
          </div>

          {data.items.length === 0 && (
            <div className="rounded-lg bg-zinc-100 p-12 text-center">
              <CheckCircle className="h-8 w-8 text-emerald-500 mx-auto mb-3" />
              <p className="font-semibold text-zinc-900">Nenhuma posição com prejuízo latente</p>
              <p className="text-sm text-muted-foreground mt-1">
                Todas as suas posições estão com resultado positivo — parabéns!
              </p>
            </div>
          )}

          {data.items.length > 0 && (
            <>
              {data.accumulated_gain_month === 0 && (
                <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-700 flex items-start gap-2">
                  <Warning className="h-4 w-4 shrink-0 mt-0.5" weight="fill" />
                  <span>
                    Sem ganho tributável no mês corrente — nenhuma economia fiscal imediata.
                    Vender para acumular prejuízo pode ser útil para meses futuros.
                  </span>
                </div>
              )}

              <div>
                <h3 className="text-base font-semibold mb-3">
                  Candidatos à venda — ordenados por prejuízo
                </h3>
                <div className="overflow-x-auto rounded-xl border border-zinc-200">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-zinc-50 text-zinc-600 border-b border-zinc-200">
                        <th className="text-left px-4 py-3 font-semibold">Ativo</th>
                        <th className="text-left px-4 py-3 font-semibold hidden sm:table-cell">Tipo</th>
                        <th className="text-right px-4 py-3 font-semibold">Qtd</th>
                        <th className="text-right px-4 py-3 font-semibold">CMP</th>
                        <th className="text-right px-4 py-3 font-semibold">Cotação</th>
                        <th className="text-right px-4 py-3 font-semibold">Prejuízo latente</th>
                        <th className="text-right px-4 py-3 font-semibold">Economia DARF</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.items.map((item) => (
                        <tr key={item.ticker} className="border-b border-zinc-100 hover:bg-zinc-50 transition-colors">
                          <td className="px-4 py-3">
                            <span className="font-bold font-mono">{item.ticker}</span>
                          </td>
                          <td className="px-4 py-3 text-zinc-500 hidden sm:table-cell">
                            {ASSET_LABELS[item.asset_class] ?? item.asset_class}
                          </td>
                          <td className="px-4 py-3 text-right font-mono">
                            {item.quantity.toLocaleString("pt-BR", { maximumFractionDigits: 4 })}
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-zinc-500">
                            {fmt(item.avg_cost)}
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums font-mono">
                            {fmt(item.current_price)}
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums">
                            <span className="text-red-600 font-semibold font-mono">
                              {fmt(item.unrealized_loss)}
                            </span>
                            <span className="ml-1.5 text-xs text-red-400">
                              ({item.unrealized_loss_pct.toFixed(1)}%)
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums">
                            {item.potential_tax_saving > 0 ? (
                              <span className="text-emerald-700 font-semibold font-mono">
                                {fmt(item.potential_tax_saving)}
                              </span>
                            ) : (
                              <span className="text-zinc-400 text-xs">sem ganho</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="text-xs text-zinc-400 mt-2">
                  CMP = custo médio ponderado de aquisição. Cotação = última snapshot do screener.
                </p>
              </div>

              {/* Warning */}
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                <p className="text-sm font-semibold text-amber-800 mb-1">Avisos importantes</p>
                <ul className="text-xs text-amber-700 space-y-1">
                  <li>• <strong>Wash-sale:</strong> recomprar o mesmo ativo em até 30 dias pode anular o benefício fiscal.</li>
                  <li>• <strong>Isenção:</strong> se suas vendas do mês ficarão abaixo de R$20.000, não haverá IR — a venda pode não ser necessária.</li>
                  <li>• <strong>FIIs:</strong> rendimentos de FIIs são isentos, mas ganhos de capital (venda da cota) são tributáveis.</li>
                  <li>• Este cálculo é estimado. Consulte um contador para decisões fiscais.</li>
                </ul>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────

type Tab = "darf" | "declaration" | "tax-loss";

export function IrHelperContent() {
  const [tab, setTab] = useState<Tab>("darf");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight">IR Helper</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Cálculo de DARF mensal, declaração DIRPF e tax-loss harvesting — Lei 11.033/2004
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-zinc-200 overflow-x-auto">
        <button
          onClick={() => setTab("darf")}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors -mb-px border-b-2 whitespace-nowrap ${
            tab === "darf"
              ? "border-blue-500 text-blue-700 bg-blue-50"
              : "border-transparent text-zinc-600 hover:text-zinc-900"
          }`}
        >
          <span className="flex items-center gap-2">
            <Receipt className="h-4 w-4" />
            DARF Mensal
          </span>
        </button>
        <button
          onClick={() => setTab("declaration")}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors -mb-px border-b-2 whitespace-nowrap ${
            tab === "declaration"
              ? "border-blue-500 text-blue-700 bg-blue-50"
              : "border-transparent text-zinc-600 hover:text-zinc-900"
          }`}
        >
          <span className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Declaração DIRPF
          </span>
        </button>
        <button
          onClick={() => setTab("tax-loss")}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors -mb-px border-b-2 whitespace-nowrap ${
            tab === "tax-loss"
              ? "border-blue-500 text-blue-700 bg-blue-50"
              : "border-transparent text-zinc-600 hover:text-zinc-900"
          }`}
        >
          <span className="flex items-center gap-2">
            <Scissors className="h-4 w-4" />
            Tax-Loss Harvesting
            <span className="bg-emerald-100 text-emerald-700 text-xs px-1.5 py-0.5 rounded-full font-semibold">
              Novo
            </span>
          </span>
        </button>
      </div>

      {/* Tab content */}
      {tab === "darf" ? <DarfTab /> : tab === "declaration" ? <DeclarationTab /> : <TaxLossTab />}
    </div>
  );
}
