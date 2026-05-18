"use client";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { apiClient } from "@/lib/api-client";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

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

function MetricSkeleton({ index }: { index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: index * 0.04 }}
      className="rounded-xl border border-zinc-100 bg-white px-4 py-3 space-y-2"
    >
      <ShimmerSkeleton className="h-2.5 w-24" />
      <ShimmerSkeleton className="h-5 w-16" />
    </motion.div>
  );
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
          {[0, 1, 2, 3, 4, 5].map((n) => (
            <MetricSkeleton key={n} index={n} />
          ))}
        </div>
      </div>
    );
  }

  if (!data) return null;

  if (!data.data_available || data.trading_days < 5) {
    return (
      <div className="rounded-xl bg-zinc-50 border border-zinc-200 px-4 py-3 text-sm text-zinc-400">
        Dados insuficientes para métricas de risco (mínimo 5 sessões de mercado)
      </div>
    );
  }

  const sharpe = data.sharpe_ratio != null ? parseFloat(data.sharpe_ratio) : null;
  const sharpeColor =
    sharpe == null
      ? "text-zinc-900"
      : sharpe >= 1
      ? "text-emerald-600"
      : sharpe >= 0
      ? "text-amber-600"
      : "text-red-500";

  const annualReturn =
    data.annual_return_pct != null ? parseFloat(data.annual_return_pct) : null;
  const returnColor =
    annualReturn == null
      ? "text-zinc-900"
      : annualReturn >= 0
      ? "text-emerald-600"
      : "text-red-500";

  const metrics = [
    {
      label: "Volatilidade a.a.",
      value: `${fmt(data.volatility_annual_pct)}%`,
      bg: "bg-amber-50 border-amber-100",
      labelColor: "text-amber-600",
      valueColor: "text-zinc-900",
    },
    {
      label: "Max Drawdown",
      value: `-${fmt(data.max_drawdown_pct)}%`,
      bg: "bg-red-50 border-red-100",
      labelColor: "text-red-500",
      valueColor: "text-zinc-900",
    },
    {
      label: "Dias positivos",
      value: `${fmt(data.positive_days_pct)}%`,
      bg: "bg-emerald-50 border-emerald-100",
      labelColor: "text-emerald-600",
      valueColor: "text-zinc-900",
    },
    {
      label: "Retorno anual",
      value:
        annualReturn != null
          ? `${annualReturn >= 0 ? "+" : ""}${fmt(data.annual_return_pct)}%`
          : "—",
      bg: "bg-blue-50 border-blue-100",
      labelColor: "text-blue-600",
      valueColor: returnColor,
    },
    {
      label: "Sharpe (CDI)",
      value: sharpe != null ? fmt(data.sharpe_ratio, 2) : "—",
      bg: "bg-violet-50 border-violet-100",
      labelColor: "text-violet-600",
      valueColor: sharpeColor,
    },
    {
      label: "VaR 95% diário",
      value: data.var_95_brl != null ? `-${fmtBrl(data.var_95_brl)}` : "—",
      bg: "bg-orange-50 border-orange-100",
      labelColor: "text-orange-600",
      valueColor: "text-red-600",
    },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {metrics.map(({ label, value, bg, labelColor, valueColor }, i) => (
          <motion.div
            key={label}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1], delay: i * 0.04 }}
            className={`rounded-xl border px-4 py-3 ${bg}`}
          >
            <p className={`text-[10px] font-semibold uppercase tracking-wider ${labelColor}`}>
              {label}
            </p>
            <p className={`text-base font-extrabold mt-0.5 tracking-tight tabular-nums ${valueColor}`}>
              {value}
            </p>
          </motion.div>
        ))}
      </div>

      {data.stress_scenarios && data.stress_scenarios.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1], delay: 0.28 }}
          className="rounded-xl border border-zinc-200 bg-white p-4"
        >
          <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400 mb-3">
            Cenários de Stress — impacto estimado
          </p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            {data.stress_scenarios.map((s, i) => {
              const impact = parseFloat(s.impact_brl);
              const pct = parseFloat(s.impact_pct);
              const isNeg = impact < 0;
              return (
                <motion.div
                  key={s.label}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.3 + i * 0.06 }}
                  className="rounded-lg border border-dashed border-zinc-200 px-3 py-2.5"
                >
                  <p className="text-xs font-semibold text-zinc-700">{s.label}</p>
                  <p className="text-xs text-zinc-400 mb-1.5">{s.assumption}</p>
                  <p className={`text-sm font-bold tabular-nums ${isNeg ? "text-red-600" : "text-emerald-600"}`}>
                    {impact === 0
                      ? "Neutro"
                      : `${isNeg ? "" : "+"}${new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(impact)}`}
                  </p>
                  {impact !== 0 && (
                    <p className={`text-xs tabular-nums ${isNeg ? "text-red-400" : "text-emerald-400"}`}>
                      ({pct >= 0 ? "+" : ""}
                      {pct.toFixed(1)}% da carteira)
                    </p>
                  )}
                </motion.div>
              );
            })}
          </div>
          <p className="text-[10px] text-zinc-300 mt-2 leading-relaxed">
            Cenários simplificados. Ibov usa beta unitário. RF assume duration média de 2 anos. Não constitui recomendação de investimento.
          </p>
        </motion.div>
      )}
    </div>
  );
}
