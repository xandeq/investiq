"use client";
import { motion } from "framer-motion";
import { TrendUp, TrendDown, ChartLineUp, Target, Pulse, Hourglass } from "@phosphor-icons/react";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import type { OutcomeStats } from "../types";

interface Props {
  stats: OutcomeStats | undefined;
  isLoading: boolean;
}

function fmtR(v: number | null, decimals = 2): string {
  if (v == null) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(decimals)}R`;
}

function fmtPct(v: number | null): string {
  if (v == null) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

function fmtDays(v: number | null): string {
  if (v == null) return "—";
  return `${v.toFixed(0)}d`;
}

interface StatChipProps {
  label: string;
  value: string;
  icon: React.ReactNode;
  color?: string;
  index: number;
  // Add perpetual animation: "pulse" for Sharpe/holding, normal for others
  animation?: "pulse";
}

function StatChip({ label, value, icon, color = "text-zinc-700", index, animation }: StatChipProps) {
  const variants = animation === "pulse" ? {
    initial: { opacity: 0, scale: 0.95 },
    animate: {
      opacity: [0.7, 1, 0.7],
      scale: 1,
      transition: {
        duration: 3,
        repeat: Infinity,
        ease: "easeInOut",
        delay: index * 0.15,
      },
    },
  } : {
    initial: { opacity: 0, y: 6 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.28, ease: [0.16, 1, 0.3, 1], delay: index * 0.05 },
  };

  return (
    <motion.div
      initial={variants.initial}
      animate={variants.animate}
      transition={variants.transition}
      className="flex items-center gap-3 rounded-[1.25rem] border border-zinc-200/60 bg-white/70 backdrop-blur-sm px-4 py-3 hover:border-zinc-300 transition-colors"
    >
      <span className="shrink-0 text-zinc-400">{icon}</span>
      <div className="flex-1">
        <p className="text-xs font-semibold uppercase tracking-widest text-zinc-400">{label}</p>
        <p className={`text-base font-bold tabular-nums ${color}`}>{value}</p>
      </div>
    </motion.div>
  );
}

export function OutcomeStatsBar({ stats, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="rounded-[1.25rem] border border-zinc-100 bg-white px-4 py-3 space-y-2">
            <ShimmerSkeleton className="h-2 w-16" />
            <ShimmerSkeleton className="h-4 w-14" />
          </div>
        ))}
      </div>
    );
  }

  if (!stats || stats.total_closed === 0) return null;

  const winColor = (stats.winrate ?? 0) >= 0.5 ? "text-emerald-600" : "text-red-500";
  const rColor = (stats.avg_r ?? 0) >= 0 ? "text-emerald-600" : "text-red-500";
  const expColor = (stats.expectancy ?? 0) >= 0 ? "text-emerald-600" : "text-red-500";
  const pfColor = (stats.profit_factor ?? 0) >= 1 ? "text-emerald-600" : "text-red-500";
  const sharpeColor = (stats.r_sharpe ?? 0) >= 1 ? "text-emerald-600" : (stats.r_sharpe ?? 0) >= 0 ? "text-amber-500" : "text-red-500";

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {/* Win rate */}
      <StatChip
        index={0}
        label="Taxa de acerto"
        value={fmtPct(stats.winrate)}
        icon={<Target size={16} weight="duotone" />}
        color={winColor}
      />

      {/* Avg R */}
      <StatChip
        index={1}
        label="R médio"
        value={fmtR(stats.avg_r)}
        icon={<ChartLineUp size={16} weight="duotone" />}
        color={rColor}
      />

      {/* Profit Factor */}
      <StatChip
        index={2}
        label="Profit Factor"
        value={stats.profit_factor != null ? `${stats.profit_factor.toFixed(2)}×` : "—"}
        icon={<Pulse size={16} weight="duotone" />}
        color={pfColor}
      />

      {/* Expectancy */}
      <StatChip
        index={3}
        label="Expectativa"
        value={fmtR(stats.expectancy)}
        icon={
          stats.expectancy != null && stats.expectancy >= 0
            ? <TrendUp size={16} weight="duotone" />
            : <TrendDown size={16} weight="duotone" />
        }
        color={expColor}
      />

      {/* R Sharpe (perpetual pulse) */}
      <StatChip
        index={4}
        label="R Sharpe"
        value={stats.r_sharpe != null ? `${stats.r_sharpe.toFixed(2)}` : "—"}
        icon={<Pulse size={16} weight="duotone" />}
        color={sharpeColor}
        animation="pulse"
      />

      {/* Avg Holding Days (perpetual pulse) */}
      <StatChip
        index={5}
        label="Holding médio"
        value={fmtDays(stats.avg_holding_days)}
        icon={<Hourglass size={16} weight="duotone" />}
        color="text-zinc-600"
        animation="pulse"
      />
    </div>
  );
}
