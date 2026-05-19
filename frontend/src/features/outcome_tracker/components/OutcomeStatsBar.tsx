"use client";
import { motion } from "framer-motion";
import { TrendUp, TrendDown, ChartLineUp, Target } from "@phosphor-icons/react";
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

interface StatChipProps {
  label: string;
  value: string;
  icon: React.ReactNode;
  color?: string;
  index: number;
}

function StatChip({ label, value, icon, color = "text-zinc-700", index }: StatChipProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1], delay: index * 0.05 }}
      className="flex items-center gap-2.5 rounded-lg border border-zinc-200 bg-white px-3 py-2"
    >
      <span className="shrink-0 text-zinc-400">{icon}</span>
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">{label}</p>
        <p className={`text-sm font-bold tabular-nums ${color}`}>{value}</p>
      </div>
    </motion.div>
  );
}

export function OutcomeStatsBar({ stats, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-zinc-100 bg-white px-3 py-2 space-y-1.5">
            <ShimmerSkeleton className="h-2 w-16" />
            <ShimmerSkeleton className="h-4 w-12" />
          </div>
        ))}
      </div>
    );
  }

  if (!stats || stats.total_closed === 0) return null;

  const winColor = (stats.winrate ?? 0) >= 0.5 ? "text-emerald-600" : "text-red-500";
  const rColor = (stats.avg_r ?? 0) >= 0 ? "text-emerald-600" : "text-red-500";
  const expColor = (stats.expectancy ?? 0) >= 0 ? "text-emerald-600" : "text-red-500";

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      <StatChip
        index={0}
        label="Taxa de acerto"
        value={`${fmtPct(stats.winrate)} (${stats.total_closed} ops)`}
        icon={<Target size={14} />}
        color={winColor}
      />
      <StatChip
        index={1}
        label="R médio"
        value={fmtR(stats.avg_r)}
        icon={<ChartLineUp size={14} />}
        color={rColor}
      />
      <StatChip
        index={2}
        label="Expectativa"
        value={fmtR(stats.expectancy)}
        icon={stats.expectancy != null && stats.expectancy >= 0
          ? <TrendUp size={14} />
          : <TrendDown size={14} />
        }
        color={expColor}
      />
      <StatChip
        index={3}
        label="Profit factor"
        value={stats.profit_factor != null ? `${stats.profit_factor.toFixed(2)}×` : "—"}
        icon={<ChartLineUp size={14} />}
        color={(stats.profit_factor ?? 0) >= 1 ? "text-emerald-600" : "text-red-500"}
      />
    </div>
  );
}
