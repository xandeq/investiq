"use client";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

interface RiskMetrics {
  volatility_annual_pct: string;
  max_drawdown_pct: string;
  positive_days_pct: string;
  trading_days: number;
  data_available: boolean;
}

const METRIC_STYLES = [
  { bg: "bg-amber-50", label: "text-amber-600" },
  { bg: "bg-red-50", label: "text-red-600" },
  { bg: "bg-green-50", label: "text-green-600" },
];

export function RiskMetricsCard() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard", "risk-metrics"],
    queryFn: () => apiClient<RiskMetrics>("/dashboard/risk-metrics"),
    staleTime: 10 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {[1, 2, 3].map((n) => (
          <div key={n} className="h-16 rounded-lg bg-gray-100 animate-pulse" />
        ))}
      </div>
    );
  }

  if (!data) return null;

  if (!data.data_available || data.trading_days < 5) {
    return (
      <div className="rounded-lg bg-gray-50 px-4 py-3 text-sm text-muted-foreground">
        Dados insuficientes (mínimo 5 sessões)
      </div>
    );
  }

  const metrics = [
    {
      label: "Volatilidade",
      value: `${parseFloat(data.volatility_annual_pct).toFixed(2)}% a.a.`,
    },
    {
      label: "Max Drawdown",
      value: `-${parseFloat(data.max_drawdown_pct).toFixed(2)}%`,
    },
    {
      label: "Dias positivos",
      value: `${parseFloat(data.positive_days_pct).toFixed(2)}%`,
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {metrics.map(({ label, value }, i) => {
        const style = METRIC_STYLES[i];
        return (
          <div key={label} className={`rounded-lg ${style.bg} px-4 py-3`}>
            <p className={`text-xs font-bold uppercase tracking-wider ${style.label}`}>{label}</p>
            <p className="text-lg font-extrabold mt-0.5 tracking-tight text-foreground">{value}</p>
          </div>
        );
      })}
    </div>
  );
}
