"use client";
import { AnalysisResponse, DCFResult } from "../types";
import { AnalysisLoadingSkeleton } from "./AnalysisLoadingSkeleton";

interface Props {
  data: AnalysisResponse | undefined;
  isLoading: boolean;
}

export function DCFSection({ data, isLoading }: Props) {
  const isPending = !data || data.status === "pending" || data.status === "running";

  if (isLoading || isPending) {
    return <AnalysisLoadingSkeleton title="Valuation DCF" />;
  }

  if (data.status === "failed") {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6">
        <h3 className="text-lg font-semibold text-red-700 mb-2">Valuation DCF</h3>
        <p className="text-sm text-red-600">
          {data.error_message || "Dados insuficientes para análise"}
        </p>
      </div>
    );
  }

  if (data.status !== "completed" || !data.result) {
    return <AnalysisLoadingSkeleton title="Valuation DCF" />;
  }

  const r = data.result as unknown as DCFResult;
  const upside = r.upside_pct;
  const upsideColor = upside === null ? "" : upside >= 0 ? "text-green-600" : "text-red-600";

  return (
    <div className="rounded-xl border bg-card p-6 space-y-4">
      <div className="flex items-start justify-between gap-4">
        <h3 className="text-lg font-semibold">Valuation DCF</h3>
        {r.data_timestamp && (
          <span className="text-xs text-muted-foreground shrink-0">
            {new Date(r.data_timestamp).toLocaleDateString("pt-BR")}
          </span>
        )}
      </div>

      {/* Fair value */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <div>
          <p className="text-xs text-muted-foreground">Valor Justo</p>
          <p className="text-xl font-bold">R$ {r.fair_value.toFixed(2)}</p>
          <p className="text-xs text-muted-foreground">
            R$ {r.fair_value_range.low.toFixed(2)} – R$ {r.fair_value_range.high.toFixed(2)}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Preço Atual</p>
          <p className="text-xl font-bold">R$ {r.current_price.toFixed(2)}</p>
        </div>
        {upside !== null && (
          <div>
            <p className="text-xs text-muted-foreground">Upside/Downside</p>
            <p className={`text-xl font-bold ${upsideColor}`}>
              {upside >= 0 ? "+" : ""}
              {upside.toFixed(1)}%
            </p>
          </div>
        )}
      </div>

      {/* Scenarios */}
      {r.scenarios && (
        <div>
          <p className="text-sm font-medium mb-2">Cenários</p>
          <div className="grid grid-cols-3 gap-2 text-sm">
            {(["bear", "base", "bull"] as const).map((s) => {
              const scenario = r.scenarios[s] as Record<string, unknown>;
              const fv = scenario?.fair_value as number | undefined;
              return (
                <div key={s} className="rounded-lg border bg-muted/30 p-3 text-center">
                  <p className="text-xs text-muted-foreground capitalize">{s}</p>
                  {fv !== undefined && (
                    <p className="font-semibold">R$ {fv.toFixed(2)}</p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Key drivers */}
      {r.key_drivers && r.key_drivers.length > 0 && (
        <div>
          <p className="text-sm font-medium mb-2">Principais Fatores</p>
          <ul className="space-y-1">
            {r.key_drivers.map((d, i) => (
              <li key={i} className="text-sm text-muted-foreground flex gap-2">
                <span className="text-primary shrink-0">•</span>
                {d}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
