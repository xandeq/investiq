"use client";
import { useState, useMemo } from "react";
import { useMacroRates, useFixedIncomeCatalog } from "@/features/screener_v2/hooks/useRendaFixa";
import { useComparadorCalc, getDefaultRateForTipo } from "../hooks/useComparadorCalc";
import type { TipoRF, ComparadorInputs } from "../types";

function fmt(n: number, decimals = 2): string {
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(decimals);
}

function fmtBRL(n: number): string {
  if (!Number.isFinite(n)) return "—";
  return "R$ " + n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function IRBadge({ isExempt, irPct }: { isExempt: boolean; irPct: number }) {
  if (isExempt) {
    return <span className="text-xs text-green-600 font-semibold">Isento</span>;
  }
  return <span className="text-xs text-gray-600">{fmt(irPct)}%</span>;
}

const TIPO_RF_OPTIONS: { value: TipoRF; label: string }[] = [
  { value: "CDB", label: "CDB" },
  { value: "LCI", label: "LCI" },
  { value: "LCA", label: "LCA" },
  { value: "TESOURO_SELIC", label: "Tesouro Selic" },
  { value: "TESOURO_IPCA", label: "Tesouro IPCA+" },
];

const CATEGORY_COLORS: Record<string, string> = {
  produto_rf: "bg-blue-50 text-blue-800 font-semibold",
  cdi: "bg-gray-50 text-gray-700",
  selic: "bg-gray-50 text-gray-700",
  ipca: "bg-gray-50 text-gray-700",
};

export function ComparadorContent() {
  const [valor, setValor] = useState<number>(10000);
  const [prazoMeses, setPrazoMeses] = useState<number>(24);
  const [tipoRF, setTipoRF] = useState<TipoRF>("CDB");
  const [taxaPct, setTaxaPct] = useState<number | null>(null); // null = use default from catalog
  const [spreadPct, setSpreadPct] = useState<number>(5.5);

  const { data: macro, isLoading: loadingMacro } = useMacroRates();
  const { data: catalog, isLoading: loadingCatalog } = useFixedIncomeCatalog();

  const defaultTaxa = useMemo(
    () => getDefaultRateForTipo(tipoRF, catalog, macro),
    [tipoRF, catalog, macro]
  );
  const effectiveTaxa = taxaPct ?? defaultTaxa;

  const inputs: ComparadorInputs = {
    valor,
    prazoMeses,
    tipoRF,
    taxaPct: effectiveTaxa,
    spreadPct,
  };

  const result = useComparadorCalc(inputs, macro, catalog);

  const cdiNominal = result.rows.find((r) => r.category === "cdi")?.retornoNominalPct ?? 0;

  return (
    <div className="space-y-6">
      {/* CVM Disclaimer */}
      <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
        Análise informativa — não constitui recomendação de investimento (CVM Res. 19/2021).
      </div>

      {/* Form card */}
      <div className="rounded-lg border border-gray-200 bg-white p-4 flex flex-wrap gap-4 items-end">
        {/* Valor */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Valor (R$)</label>
          <input
            type="number"
            value={valor}
            onChange={(e) => setValor(parseFloat(e.target.value) || 0)}
            min="0"
            className="w-36 rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
          />
        </div>

        {/* Prazo */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Prazo (meses)</label>
          <input
            type="number"
            value={prazoMeses}
            onChange={(e) => setPrazoMeses(parseInt(e.target.value, 10) || 1)}
            min="1"
            max="360"
            className="w-28 rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
          />
        </div>

        {/* Tipo RF */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Tipo RF</label>
          <select
            value={tipoRF}
            onChange={(e) => {
              setTipoRF(e.target.value as TipoRF);
              setTaxaPct(null);
            }}
            className="rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400 bg-white"
          >
            <option value="CDB">CDB</option>
            <option value="LCI">LCI</option>
            <option value="LCA">LCA</option>
            <option value="TESOURO_SELIC">Tesouro Selic</option>
            <option value="TESOURO_IPCA">Tesouro IPCA+</option>
          </select>
        </div>

        {/* Taxa */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Taxa (% a.a.)</label>
          <input
            type="number"
            step="0.01"
            value={effectiveTaxa.toFixed(2)}
            onChange={(e) => setTaxaPct(parseFloat(e.target.value) || 0)}
            className="w-28 rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
          />
          <p className="text-xs text-gray-400 mt-0.5">Padrão: {defaultTaxa.toFixed(2)}% a.a.</p>
        </div>

        {/* Spread (only for TESOURO_IPCA) */}
        {tipoRF === "TESOURO_IPCA" && (
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Spread (% a.a.)</label>
            <input
              type="number"
              step="0.01"
              value={spreadPct}
              onChange={(e) => setSpreadPct(parseFloat(e.target.value) || 0)}
              className="w-28 rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            />
          </div>
        )}
      </div>

      {/* Loading skeleton */}
      {(loadingMacro || loadingCatalog) && (
        <div className="h-40 rounded-lg bg-gray-100 animate-pulse" />
      )}

      {/* Comparison table */}
      {!loadingMacro && !loadingCatalog && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Alternativa</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Taxa Bruta (% a.a.)</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Taxa Líquida IR (% a.a.)</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Retorno Nominal (%)</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Retorno Real (%)</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Total Acumulado (R$)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {result.rows.map((row) => {
                const isHighlight = row.category === "produto_rf";
                const beatsCDI = row.retornoNominalPct > cdiNominal;

                return (
                  <tr
                    key={row.category}
                    className={isHighlight ? "bg-blue-50" : "hover:bg-gray-50"}
                  >
                    <td className="px-4 py-3 font-medium">
                      <span className={`inline-flex items-center gap-1 ${CATEGORY_COLORS[row.category] ?? ""}`}>
                        {row.label}
                        {isHighlight && (
                          <span className="ml-1 text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full">selecionado</span>
                        )}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">{fmt(row.taxaBrutaAnualPct)}%</td>
                    <td className="px-4 py-3 text-right">
                      {row.isExempt ? (
                        <IRBadge isExempt={true} irPct={0} />
                      ) : (
                        <div>
                          <span>{fmt(row.taxaLiquidaAnualPct)}%</span>
                          <div className="text-xs text-gray-400">IR: {fmt(row.irRateAnualPct)}%</div>
                        </div>
                      )}
                    </td>
                    <td className={`px-4 py-3 text-right font-semibold ${beatsCDI ? "text-emerald-600" : "text-gray-700"}`}>
                      {fmt(row.retornoNominalPct)}%
                    </td>
                    <td className="px-4 py-3 text-right">
                      {!result.ipcaAvailable ? (
                        <span title="IPCA indisponível" className="text-gray-400">—</span>
                      ) : (
                        <span>{fmt(row.retornoRealPct)}%</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-semibold">{fmtBRL(row.totalAcumuladoBRL)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Plan 03 will render the chart here using result.projection */}

      {/* Footer */}
      <p className="text-center text-xs text-gray-400">
        Taxas macro atualizadas via BCB (6h) — valores indicativos.
      </p>
    </div>
  );
}
