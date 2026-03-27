"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Calculator, TrendingDown, TrendingUp, Receipt, AlertCircle, CheckCircle2 } from "lucide-react";

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

function fmt(value: number) {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function currentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export function IrHelperContent() {
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
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">IR Helper</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Cálculo de DARF mensal para swing trade (Lei 11.033/2004)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">Mês</label>
          <input
            type="month"
            value={month}
            onChange={(e) => setMonth(e.target.value)}
            className="bg-gray-100 border-0 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
          />
        </div>
      </div>

      {isLoading && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="h-24 rounded-xl bg-gray-100 animate-pulse" />
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-lg bg-red-50 border-l-4 border-red-500 p-4 text-sm text-red-600 flex gap-2">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          Erro ao carregar dados do IR Helper.
        </div>
      )}

      {summary && (
        <>
          {/* Status badge */}
          <div className="flex items-center gap-3">
            {summary.isento ? (
              <div className="flex items-center gap-2 bg-emerald-100 text-emerald-700 px-4 py-2 rounded-full font-semibold text-sm">
                <CheckCircle2 className="h-4 w-4" />
                ISENTO — vendas abaixo de R$20.000
              </div>
            ) : summary.darf_gerado ? (
              <div className="flex items-center gap-2 bg-red-100 text-red-700 px-4 py-2 rounded-full font-semibold text-sm">
                <Receipt className="h-4 w-4" />
                DARF DEVIDA — {fmt(summary.darf_valor)}
              </div>
            ) : (
              <div className="flex items-center gap-2 bg-amber-100 text-amber-700 px-4 py-2 rounded-full font-semibold text-sm">
                <AlertCircle className="h-4 w-4" />
                IR abaixo de R$10 — sem DARF
              </div>
            )}
          </div>

          {/* Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white border border-gray-200 rounded-xl p-5">
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Total Vendas</p>
              <p className="text-xl font-bold mt-1">{fmt(summary.total_vendas)}</p>
              <p className="text-xs text-gray-500 mt-1">{summary.transactions_count} operações</p>
            </div>
            <div className="bg-white border border-gray-200 rounded-xl p-5">
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Lucro Bruto</p>
              <p className={`text-xl font-bold mt-1 ${summary.lucro_bruto >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                {fmt(summary.lucro_bruto)}
              </p>
              {summary.lucro_bruto >= 0 ? (
                <TrendingUp className="h-4 w-4 text-emerald-500 mt-1" />
              ) : (
                <TrendingDown className="h-4 w-4 text-red-500 mt-1" />
              )}
            </div>
            <div className="bg-white border border-gray-200 rounded-xl p-5">
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Prejuízo Acumulado</p>
              <p className={`text-xl font-bold mt-1 ${summary.prejuizo_acumulado > 0 ? "text-red-600" : "text-gray-400"}`}>
                {summary.prejuizo_acumulado > 0 ? `−${fmt(summary.prejuizo_acumulado)}` : "—"}
              </p>
              <p className="text-xs text-gray-500 mt-1">meses anteriores</p>
            </div>
            <div className={`rounded-xl p-5 border ${summary.darf_gerado ? "bg-red-50 border-red-200" : "bg-white border-gray-200"}`}>
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">DARF</p>
              <p className={`text-xl font-bold mt-1 ${summary.darf_gerado ? "text-red-600" : "text-gray-400"}`}>
                {summary.darf_gerado ? fmt(summary.darf_valor) : "—"}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {summary.darf_gerado ? `Vencimento: último dia útil do mês` : "sem DARF"}
              </p>
            </div>
          </div>

          {/* Instruções DARF */}
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

          {/* Regras */}
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
            <h3 className="font-semibold text-blue-800 flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
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

          {/* Tabela de transações do mês */}
          {summary.transactions.length > 0 && (
            <div>
              <h3 className="text-base font-semibold mb-3">Vendas em {summary.month}</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-100 text-gray-600">
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
                      <tr key={tx.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-3 font-bold font-mono">{tx.ticker}</td>
                        <td className="px-4 py-3 text-gray-600">
                          {new Date(tx.date + "T00:00:00").toLocaleDateString("pt-BR")}
                        </td>
                        <td className="px-4 py-3 text-right">{tx.quantity.toLocaleString("pt-BR")}</td>
                        <td className="px-4 py-3 text-right">{fmt(tx.unit_price)}</td>
                        <td className="px-4 py-3 text-right font-medium">{fmt(tx.total_value)}</td>
                        <td className="px-4 py-3 text-right font-semibold">
                          {tx.gross_profit !== null ? (
                            <span className={tx.gross_profit >= 0 ? "text-emerald-600" : "text-red-600"}>
                              {tx.gross_profit >= 0 ? "+" : ""}{fmt(tx.gross_profit)}
                            </span>
                          ) : (
                            <span className="text-gray-400 text-xs">não informado</span>
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

      {/* Histórico mensal */}
      {history.length > 0 && (
        <div>
          <h3 className="text-base font-semibold mb-3 flex items-center gap-2">
            <Calculator className="h-4 w-4" />
            Histórico Anual
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-100 text-gray-600">
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
                    className={`border-b border-gray-100 hover:bg-gray-50 transition-colors cursor-pointer ${row.month === month ? "bg-blue-50" : ""}`}
                    onClick={() => setMonth(row.month)}
                  >
                    <td className="px-4 py-3 font-medium">{row.month}</td>
                    <td className="px-4 py-3 text-right">{fmt(row.total_vendas)}</td>
                    <td className={`px-4 py-3 text-right font-medium ${row.lucro_bruto >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                      {fmt(row.lucro_bruto)}
                    </td>
                    <td className="px-4 py-3 text-right">{row.ir_devido > 0 ? fmt(row.ir_devido) : "—"}</td>
                    <td className="px-4 py-3 text-right">
                      {row.isento ? (
                        <span className="bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full text-xs font-medium">Isento</span>
                      ) : row.darf_gerado ? (
                        <span className="bg-red-100 text-red-700 px-2 py-0.5 rounded-full text-xs font-medium">DARF</span>
                      ) : (
                        <span className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full text-xs font-medium">Sem DARF</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-gray-400 mt-2">Clique em uma linha para ver os detalhes do mês.</p>
        </div>
      )}

      {!isLoading && summary && summary.transactions_count === 0 && history.length === 0 && (
        <div className="rounded-lg bg-gray-100 p-12 text-center">
          <Calculator className="h-8 w-8 text-gray-400 mx-auto mb-3" />
          <p className="font-semibold text-gray-900">Nenhuma venda registrada</p>
          <p className="text-sm text-muted-foreground mt-1">
            Registre transações de venda na carteira para calcular o IR.
          </p>
        </div>
      )}
    </div>
  );
}
