"use client";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

interface StressScenario {
  label: string;
  assumption: string;
  impact_brl: string;
  impact_pct: string;
}

interface RiskMetrics {
  volatility_annual_pct: string;
  max_drawdown_pct: string;
  positive_days_pct: string;
  sharpe_ratio: string | null;
  annual_return_pct: string | null;
  var_95_pct: string | null;
  var_95_brl: string | null;
  stress_scenarios: StressScenario[];
  portfolio_value_brl: string | null;
  trading_days: number;
  data_available: boolean;
}

function fmt(v: string | null, decimals = 2) {
  if (v == null) return "—";
  return parseFloat(v).toFixed(decimals);
}

function fmtBrl(v: string | null) {
  if (v == null) return "—";
  const n = parseFloat(v);
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(n);
}

export function RiskMetricsCard() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard", "risk-metrics"],
    queryFn: () => apiClient<RiskMetrics>("/dashboard/risk-metrics"),
    staleTime: 10 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((n) => (
            <div key={n} className="h-16 rounded-lg bg-gray-100 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!data) return null;

  if (!data.data_available || data.trading_days < 5) {
    return (
      <div className="rounded-lg bg-gray-50 px-4 py-3 text-sm text-muted-foreground">
        Dados insuficientes para métricas de risco (mínimo 5 sessões de mercado)
      </div>
    );
  }

  const sharpe = data.sharpe_ratio != null ? parseFloat(data.sharpe_ratio) : null;
  const sharpeColor =
    sharpe == null ? "text-foreground" : sharpe >= 1 ? "text-emerald-700" : sharpe >= 0 ? "text-amber-600" : "text-red-600";

  const annualReturn = data.annual_return_pct != null ? parseFloat(data.annual_return_pct) : null;
  const returnColor = annualReturn == null ? "text-foreground" : annualReturn >= 0 ? "text-emerald-700" : "text-red-600";

  const metrics = [
    {
      label: "Volatilidade a.a.",
      value: `${fmt(data.volatility_annual_pct)}%`,
      bg: "bg-amber-50",
      labelColor: "text-amber-600",
      valueColor: "text-foreground",
    },
    {
      label: "Max Drawdown",
      value: `-${fmt(data.max_drawdown_pct)}%`,
      bg: "bg-red-50",
      labelColor: "text-red-600",
      valueColor: "text-foreground",
    },
    {
      label: "Dias positivos",
      value: `${fmt(data.positive_days_pct)}%`,
      bg: "bg-green-50",
      labelColor: "text-green-600",
      valueColor: "text-foreground",
    },
    {
      label: "Retorno anual",
      value: annualReturn != null ? `${annualReturn >= 0 ? "+" : ""}${fmt(data.annual_return_pct)}%` : "—",
      bg: "bg-blue-50",
      labelColor: "text-blue-600",
      valueColor: returnColor,
    },
    {
      label: "Sharpe (CDI)",
      value: sharpe != null ? fmt(data.sharpe_ratio, 2) : "—",
      bg: "bg-violet-50",
      labelColor: "text-violet-600",
      valueColor: sharpeColor,
    },
    {
      label: "VaR 95% diário",
      value: data.var_95_brl != null ? `-${fmtBrl(data.var_95_brl)}` : "—",
      bg: "bg-orange-50",
      labelColor: "text-orange-600",
      valueColor: "text-red-700",
    },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {metrics.map(({ label, value, bg, labelColor, valueColor }) => (
          <div key={label} className={`rounded-lg ${bg} px-4 py-3`}>
            <p className={`text-xs font-bold uppercase tracking-wider ${labelColor}`}>{label}</p>
            <p className={`text-base font-extrabold mt-0.5 tracking-tight ${valueColor}`}>{value}</p>
          </div>
        ))}
      </div>

      {data.stress_scenarios && data.stress_scenarios.length > 0 && (
        <div className="rounded-xl border bg-white p-4">
          <p className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">
            Cenários de Stress — impacto estimado
          </p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            {data.stress_scenarios.map((s) => {
              const impact = parseFloat(s.impact_brl);
              const pct = parseFloat(s.impact_pct);
              const isNegative = impact < 0;
              return (
                <div key={s.label} className="rounded-lg border border-dashed px-3 py-2.5">
                  <p className="text-xs font-semibold text-gray-700">{s.label}</p>
                  <p className="text-xs text-gray-400 mb-1.5">{s.assumption}</p>
                  <p className={`text-sm font-bold ${isNegative ? "text-red-600" : "text-emerald-600"}`}>
                    {impact === 0
                      ? "Neutro"
                      : `${isNegative ? "" : "+"}${new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(impact)}`}
                  </p>
                  {impact !== 0 && (
                    <p className={`text-xs ${isNegative ? "text-red-400" : "text-emerald-400"}`}>
                      ({pct >= 0 ? "+" : ""}{pct.toFixed(1)}% da carteira)
                    </p>
                  )}
                </div>
              );
            })}
          </div>
          <p className="text-[10px] text-gray-400 mt-2">
            Cenários simplificados. Ibov usa beta unitário. RF assume duration média de 2 anos. Não constitui recomendação de investimento.
          </p>
        </div>
      )}
    </div>
  );
}
