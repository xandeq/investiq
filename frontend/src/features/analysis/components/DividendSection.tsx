"use client";
import { AnalysisResponse, DividendResult } from "../types";
import { AnalysisLoadingSkeleton } from "./AnalysisLoadingSkeleton";

interface Props {
  data: AnalysisResponse | undefined;
  isLoading: boolean;
}

const sustainabilityConfig = {
  safe: { label: "Seguro", className: "bg-green-100 text-green-700 border-green-200" },
  warning: { label: "Atenção", className: "bg-yellow-100 text-yellow-700 border-yellow-200" },
  risk: { label: "Risco", className: "bg-red-100 text-red-700 border-red-200" },
};

function pct(v: number | null): string {
  if (v === null) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

export function DividendSection({ data, isLoading }: Props) {
  const isPending = !data || data.status === "pending" || data.status === "running";

  if (isLoading || isPending) {
    return <AnalysisLoadingSkeleton title="Dividendos" />;
  }

  if (data.status === "failed") {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6">
        <h3 className="text-lg font-semibold text-red-700 mb-2">Dividendos</h3>
        <p className="text-sm text-red-600">
          {data.error_message || "Dados insuficientes para análise"}
        </p>
      </div>
    );
  }

  if (data.status !== "completed" || !data.result) {
    return <AnalysisLoadingSkeleton title="Dividendos" />;
  }

  const r = data.result as unknown as DividendResult;
  const sustainCfg = sustainabilityConfig[r.sustainability] ?? sustainabilityConfig.warning;

  return (
    <div className="rounded-xl border bg-card p-6 space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h3 className="text-lg font-semibold">Dividendos</h3>
        <span
          className={`text-xs font-medium px-2 py-1 rounded-full border ${sustainCfg.className}`}
        >
          {sustainCfg.label}
        </span>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div>
          <p className="text-xs text-muted-foreground">Dividend Yield</p>
          <p className="text-xl font-bold">{pct(r.current_yield)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Payout Ratio</p>
          <p className="font-semibold">{pct(r.payout_ratio)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Cobertura</p>
          <p className="font-semibold">{pct(r.coverage_ratio)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Consistência</p>
          <p className="font-semibold">{r.consistency?.score?.toFixed(1) ?? "—"}</p>
        </div>
      </div>

      {/* Dividend history */}
      {r.dividend_history && r.dividend_history.length > 0 && (
        <div>
          <p className="text-sm font-medium mb-2">Histórico de Dividendos</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-muted-foreground">
                  <th className="text-left py-1 pr-4">Ano</th>
                  <th className="text-right py-1">DPS</th>
                </tr>
              </thead>
              <tbody>
                {r.dividend_history.slice(-6).map((row) => (
                  <tr key={row.year} className="border-b last:border-0">
                    <td className="py-1 pr-4">{row.year}</td>
                    <td className="py-1 text-right">R$ {row.dps.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
