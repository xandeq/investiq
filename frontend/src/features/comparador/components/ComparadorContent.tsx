"use client";
import { useState } from "react";
import { useComparador } from "../hooks/useComparador";
import type { ComparadorRow, PrazoLabel } from "../types";

const PRAZOS: PrazoLabel[] = ["6m", "1a", "2a", "5a"];
const PRAZO_LABELS: Record<PrazoLabel, string> = {
  "6m": "6 meses", "1a": "1 ano", "2a": "2 anos", "5a": "5 anos",
};

const RISK_COLORS: Record<string, string> = {
  "Baixíssimo": "bg-emerald-100 text-emerald-700",
  "Baixo": "bg-blue-100 text-blue-700",
  "Moderado": "bg-amber-100 text-amber-700",
  "Alto": "bg-red-100 text-red-700",
  "Variável": "bg-purple-100 text-purple-700",
};

const CAT_COLORS: Record<string, string> = {
  cdb: "border-l-blue-400",
  lci: "border-l-green-400",
  lca: "border-l-emerald-400",
  tesouro: "border-l-yellow-400",
  cdi: "border-l-gray-400",
  ibovespa: "border-l-orange-400",
  portfolio: "border-l-purple-400",
};

function fmt(val: string | null, decimals = 2): string {
  if (!val) return "—";
  const n = parseFloat(val);
  return isNaN(n) ? "—" : n.toFixed(decimals);
}

function fmtBRL(val: string | null): string {
  if (!val) return "—";
  const n = parseFloat(val);
  if (isNaN(n)) return "—";
  return `R$ ${n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function RowCard({ row, showValue }: { row: ComparadorRow; showValue: boolean }) {
  const borderColor = CAT_COLORS[row.category] ?? "border-l-gray-200";
  const isPositive = row.net_pct && parseFloat(row.net_pct) >= 0;

  return (
    <div className={`relative rounded-lg border border-gray-200 border-l-4 ${borderColor} bg-white p-4 ${row.is_best ? "ring-2 ring-blue-400" : ""}`}>
      {row.is_best && (
        <span className="absolute -top-2.5 right-3 text-xs bg-blue-500 text-white px-2 py-0.5 rounded-full font-semibold">
          Melhor retorno
        </span>
      )}
      {row.is_portfolio && (
        <span className="absolute -top-2.5 left-3 text-xs bg-purple-500 text-white px-2 py-0.5 rounded-full font-semibold">
          Minha carteira
        </span>
      )}

      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-bold truncate">{row.label}</p>
          {row.note && <p className="text-xs text-gray-400 mt-0.5">{row.note}</p>}
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${RISK_COLORS[row.risk_label] ?? "bg-gray-100 text-gray-600"}`}>
          {row.risk_label}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2">
        <div>
          <p className="text-xs text-gray-500">Bruto</p>
          <p className="text-sm font-semibold">{fmt(row.gross_pct)}%</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">IR</p>
          <p className="text-sm font-semibold">
            {row.is_exempt ? <span className="text-green-600">Isento</span> : `${fmt(row.ir_rate_pct)}%`}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Líquido</p>
          <p className={`text-base font-bold ${isPositive ? "text-emerald-600" : "text-red-500"}`}>
            {fmt(row.net_pct)}%
          </p>
        </div>
      </div>

      {showValue && row.net_value && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <p className="text-xs text-gray-500">Valor projetado</p>
          <p className="text-base font-bold text-gray-800">{fmtBRL(row.net_value)}</p>
        </div>
      )}
    </div>
  );
}

export function ComparadorContent() {
  const [prazo, setPrazo] = useState<PrazoLabel>("1a");
  const [valorInput, setValorInput] = useState("");
  const [valor, setValor] = useState<number | undefined>();

  const { data, isLoading, error } = useComparador(prazo, valor);

  const showValue = !!valor;
  const portfolioRow = data?.rows.find((r) => r.is_portfolio);
  const rfRows = data?.rows.filter((r) => ["cdb", "lci", "lca", "tesouro", "cdi"].includes(r.category)) ?? [];
  const rvRows = data?.rows.filter((r) => ["ibovespa"].includes(r.category)) ?? [];

  return (
    <div className="space-y-6">
      {/* Disclaimer */}
      <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
        <strong>Análise informativa</strong> — não constitui recomendação de investimento (CVM Res. 19/2021).
        Retornos históricos não garantem retornos futuros.
      </div>

      {/* Controls */}
      <div className="rounded-lg border border-gray-200 bg-white p-4 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Prazo</label>
          <div className="flex rounded-lg border border-gray-200 overflow-hidden">
            {PRAZOS.map((p) => (
              <button
                key={p}
                onClick={() => setPrazo(p)}
                className={`px-4 py-2 text-sm font-medium transition-colors ${prazo === p ? "bg-blue-500 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
              >
                {PRAZO_LABELS[p]}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Valor inicial (opcional)</label>
          <div className="flex gap-2">
            <input
              type="number"
              placeholder="Ex: 10000"
              value={valorInput}
              onChange={(e) => setValorInput(e.target.value)}
              className="w-36 rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            />
            <button
              onClick={() => setValor(valorInput ? +valorInput : undefined)}
              className="px-3 py-2 text-sm rounded-md bg-blue-500 text-white hover:bg-blue-600 transition-colors"
            >
              Aplicar
            </button>
          </div>
        </div>
        {data?.cdi_annual_pct && (
          <div className="text-xs text-gray-500 ml-auto self-center">
            CDI atual: <strong>{parseFloat(data.cdi_annual_pct).toFixed(2)}% a.a.</strong>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-100 px-4 py-3 text-sm text-red-600">
          {error instanceof Error ? error.message : "Erro ao carregar comparador"}
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-32 rounded-lg bg-gray-100 animate-pulse" />
          ))}
        </div>
      )}

      {/* Results */}
      {!isLoading && data && (
        <>
          {/* COMP-02: portfolio summary */}
          {portfolioRow && (
            <div className="rounded-lg bg-purple-50 border border-purple-200 px-4 py-3">
              <p className="text-sm font-semibold text-purple-800">
                Sua carteira rendeu <strong>{fmt(portfolioRow.gross_pct)}% a.a.</strong>
                {data.portfolio_cdb_equivalent && (
                  <span className="ml-1">
                    — equivalente a um CDB de <strong>{fmt(data.portfolio_cdb_equivalent)}% a.a.</strong> brutos
                  </span>
                )}
              </p>
            </div>
          )}

          {/* Renda Variável */}
          {rvRows.length > 0 && (
            <section>
              <h2 className="text-sm font-bold uppercase tracking-wider text-gray-500 mb-3">Renda Variável</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {rvRows.map((row, i) => <RowCard key={i} row={row} showValue={showValue} />)}
              </div>
              {data.ibovespa_data_stale && (
                <p className="text-xs text-amber-600 mt-2">* Dados IBOVESPA em cache — reconectando ao Yahoo Finance</p>
              )}
            </section>
          )}

          {/* Renda Fixa */}
          {rfRows.length > 0 && (
            <section>
              <h2 className="text-sm font-bold uppercase tracking-wider text-gray-500 mb-3">Renda Fixa</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {rfRows.map((row, i) => <RowCard key={i} row={row} showValue={showValue} />)}
              </div>
            </section>
          )}

          {/* Carteira */}
          {portfolioRow && (
            <section>
              <h2 className="text-sm font-bold uppercase tracking-wider text-gray-500 mb-3">Sua carteira</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <RowCard row={portfolioRow} showValue={showValue} />
              </div>
            </section>
          )}

          {data.rows.length === 0 && (
            <div className="text-center py-12 text-sm text-gray-500">
              Nenhum dado disponível — aguarde os pipelines de dados (Tesouro, CDI) ou verifique o Redis.
            </div>
          )}
        </>
      )}
    </div>
  );
}
