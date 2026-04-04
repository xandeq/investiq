"use client";
import { AnalysisResponse, SectorResult } from "../types";
import { AnalysisLoadingSkeleton } from "./AnalysisLoadingSkeleton";

interface Props {
  data: AnalysisResponse | undefined;
  isLoading: boolean;
}

function fmt(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return v.toFixed(2);
  return String(v);
}

export function SectorSection({ data, isLoading }: Props) {
  const isPending = !data || data.status === "pending" || data.status === "running";

  if (isLoading || isPending) {
    return <AnalysisLoadingSkeleton title="Comparação Setorial" />;
  }

  if (data.status === "failed") {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6">
        <h3 className="text-lg font-semibold text-red-700 mb-2">Comparação Setorial</h3>
        <p className="text-sm text-red-600">
          {data.error_message || "Dados insuficientes para análise"}
        </p>
      </div>
    );
  }

  if (data.status !== "completed" || !data.result) {
    return <AnalysisLoadingSkeleton title="Comparação Setorial" />;
  }

  const r = data.result as unknown as SectorResult;
  const metricLabels: Record<string, string> = {
    pe_ratio: "P/L",
    price_to_book: "P/VPA",
    dividend_yield: "Dividend Yield",
    roe: "ROE",
  };

  return (
    <div className="rounded-xl border bg-card p-6 space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold">Comparação Setorial</h3>
          <p className="text-sm text-muted-foreground">
            {r.sector} · {r.peers_found} de {r.peers_attempted} peers
          </p>
        </div>
      </div>

      {/* Metrics comparison table */}
      <div>
        <p className="text-sm font-medium mb-2">Métricas vs. Setor</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-muted-foreground">
                <th className="text-left py-1 pr-4">Métrica</th>
                <th className="text-right py-1 pr-4">{r.ticker}</th>
                <th className="text-right py-1 pr-4">Média</th>
                <th className="text-right py-1">Mediana</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(r.target_metrics).map(([key, val]) => (
                <tr key={key} className="border-b last:border-0">
                  <td className="py-1 pr-4 text-muted-foreground">
                    {metricLabels[key] ?? key}
                  </td>
                  <td className="py-1 pr-4 text-right font-medium">{fmt(val)}</td>
                  <td className="py-1 pr-4 text-right">
                    {fmt((r.sector_averages as Record<string, unknown>)[key])}
                  </td>
                  <td className="py-1 text-right">
                    {fmt((r.sector_medians as Record<string, unknown>)[key])}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Peer list */}
      {r.peers && r.peers.length > 0 && (
        <div>
          <p className="text-sm font-medium mb-2">Peers ({r.peers.length})</p>
          <div className="flex flex-wrap gap-2">
            {r.peers.map((p) => (
              <span
                key={p.ticker}
                className="rounded-md border bg-muted/40 px-2 py-1 text-xs font-mono"
              >
                {p.ticker}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
