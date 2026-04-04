"use client";
import { AnalysisResponse, EarningsResult } from "../types";
import { AnalysisLoadingSkeleton } from "./AnalysisLoadingSkeleton";

interface Props {
  data: AnalysisResponse | undefined;
  isLoading: boolean;
}

export function EarningsSection({ data, isLoading }: Props) {
  const isPending = !data || data.status === "pending" || data.status === "running";

  if (isLoading || isPending) {
    return <AnalysisLoadingSkeleton title="Lucros e Qualidade" />;
  }

  if (data.status === "failed") {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6">
        <h3 className="text-lg font-semibold text-red-700 mb-2">Lucros e Qualidade</h3>
        <p className="text-sm text-red-600">
          {data.error_message || "Dados insuficientes para análise"}
        </p>
      </div>
    );
  }

  if (data.status !== "completed" || !data.result) {
    return <AnalysisLoadingSkeleton title="Lucros e Qualidade" />;
  }

  const r = data.result as unknown as EarningsResult;

  return (
    <div className="rounded-xl border bg-card p-6 space-y-4">
      <h3 className="text-lg font-semibold">Lucros e Qualidade</h3>

      {/* CAGR + quality */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        {r.eps_cagr_5y !== null && (
          <div>
            <p className="text-xs text-muted-foreground">CAGR EPS 5 anos</p>
            <p className="text-xl font-bold">
              {(r.eps_cagr_5y * 100).toFixed(1)}%
            </p>
          </div>
        )}
        {r.quality_metrics && (
          <>
            <div>
              <p className="text-xs text-muted-foreground">Qualidade dos Lucros</p>
              <p className="font-semibold capitalize">{r.quality_metrics.earnings_quality ?? "—"}</p>
            </div>
            {r.quality_metrics.fcf_conversion !== null && (
              <div>
                <p className="text-xs text-muted-foreground">Conversão FCF</p>
                <p className="font-semibold">
                  {((r.quality_metrics.fcf_conversion ?? 0) * 100).toFixed(1)}%
                </p>
              </div>
            )}
          </>
        )}
      </div>

      {/* EPS history table */}
      {r.eps_history && r.eps_history.length > 0 && (
        <div>
          <p className="text-sm font-medium mb-2">Histórico EPS</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-muted-foreground">
                  <th className="text-left py-1 pr-4">Ano</th>
                  <th className="text-right py-1">EPS</th>
                </tr>
              </thead>
              <tbody>
                {r.eps_history.slice(-6).map((row) => (
                  <tr key={row.year} className="border-b last:border-0">
                    <td className="py-1 pr-4">{row.year}</td>
                    <td className="py-1 text-right">R$ {row.eps.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {r.narrative && (
        <p className="text-sm text-muted-foreground whitespace-pre-line">{r.narrative}</p>
      )}
    </div>
  );
}
