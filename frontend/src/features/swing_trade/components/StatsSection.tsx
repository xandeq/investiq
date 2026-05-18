"use client";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ChartBar } from "@phosphor-icons/react";
import { apiClient } from "@/lib/api-client";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

interface SwingStats {
  total_closed: number;
  data_available: boolean;
  winrate: number | null;
  avg_return_pct: number | null;
  profit_factor: number | null;
  r_sharpe: number | null;
  max_consecutive_losses: number;
  max_consecutive_wins: number;
  avg_holding_days: number | null;
  best_trade_pct: number | null;
  worst_trade_pct: number | null;
}

function fmt(v: number | null, suffix = "%", decimals = 1): string {
  if (v == null) return "—";
  return `${v.toFixed(decimals)}${suffix}`;
}

function StatCard({
  label,
  value,
  subtext,
  color = "text-zinc-900",
  index = 0,
}: {
  label: string;
  value: string;
  subtext?: string;
  color?: string;
  index?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1], delay: index * 0.04 }}
      className="rounded-xl border border-zinc-200 bg-white px-4 py-3"
    >
      <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">{label}</p>
      <p className={`text-xl font-extrabold mt-0.5 tabular-nums ${color}`}>{value}</p>
      {subtext && <p className="text-xs text-zinc-400 mt-0.5">{subtext}</p>}
    </motion.div>
  );
}

function StatCardSkeleton({ index }: { index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: index * 0.04 }}
      className="rounded-xl border border-zinc-100 bg-white px-4 py-3 space-y-2"
    >
      <ShimmerSkeleton className="h-2.5 w-20" />
      <ShimmerSkeleton className="h-6 w-14" />
      <ShimmerSkeleton className="h-2 w-28" />
    </motion.div>
  );
}

export function StatsSection() {
  const { data, isLoading } = useQuery<SwingStats>({
    queryKey: ["swing-trade-stats"],
    queryFn: () => apiClient<SwingStats>("/swing-trade/stats"),
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <StatCardSkeleton key={i} index={i} />
        ))}
      </div>
    );
  }

  if (!data || !data.data_available) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="rounded-xl border border-dashed border-zinc-200 bg-white p-10 text-center"
      >
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-zinc-50">
          <ChartBar size={22} className="text-zinc-400" aria-hidden />
        </div>
        <p className="font-semibold text-zinc-700">Nenhuma operação encerrada ainda</p>
        <p className="text-sm text-zinc-400 mt-1">
          Feche operações para ver suas estatísticas de performance.
        </p>
      </motion.div>
    );
  }

  const winColor = (data.winrate ?? 0) >= 50 ? "text-emerald-600" : "text-red-500";
  const pfColor = (data.profit_factor ?? 0) >= 1 ? "text-emerald-600" : "text-red-500";
  const avgColor = (data.avg_return_pct ?? 0) >= 0 ? "text-emerald-600" : "text-red-500";

  return (
    <div className="space-y-4">
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
        className="text-xs text-zinc-400"
      >
        Baseado em <strong className="text-zinc-700">{data.total_closed}</strong> operações encerradas
      </motion.p>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        <StatCard index={0} label="Taxa de acerto" value={fmt(data.winrate)} subtext="% de operações lucrativas" color={winColor} />
        <StatCard index={1} label="Retorno médio" value={fmt(data.avg_return_pct)} subtext="por operação encerrada" color={avgColor} />
        <StatCard index={2} label="Profit Factor" value={fmt(data.profit_factor, "×", 2)} subtext="lucro bruto / perda bruta" color={pfColor} />
        <StatCard index={3} label="R-Sharpe" value={fmt(data.r_sharpe, "", 2)} subtext="consistência dos retornos" />
        <StatCard index={4} label="Melhor trade" value={fmt(data.best_trade_pct)} color="text-emerald-600" />
        <StatCard index={5} label="Pior trade" value={fmt(data.worst_trade_pct)} color="text-red-500" />
        <StatCard
          index={6}
          label="Seq. perdas máx."
          value={`${data.max_consecutive_losses}`}
          subtext="operações seguidas no vermelho"
          color={data.max_consecutive_losses >= 3 ? "text-red-500" : "text-zinc-900"}
        />
        <StatCard
          index={7}
          label="Tempo médio"
          value={data.avg_holding_days != null ? `${data.avg_holding_days}d` : "—"}
          subtext="dias por operação"
        />
      </div>
    </div>
  );
}
