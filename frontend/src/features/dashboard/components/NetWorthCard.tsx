"use client";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { motion } from "framer-motion";
import { AnimatedNumber } from "@/components/ui/AnimatedNumber";
import { NetWorthSkeleton } from "@/components/ui/ShimmerSkeleton";

interface Props {
  netWorth: string;
  totalReturn: string;
  totalReturnPct: string;
  dailyPnl: string;
  dailyPnlPct: string;
  dataStale: boolean;
  isLoading: boolean;
}

const pctFormatter = (v: number) =>
  (v >= 0 ? "+" : "") +
  v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) +
  "%";

const brlFormatter = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export function NetWorthCard({
  netWorth,
  totalReturn,
  totalReturnPct,
  dailyPnl,
  dailyPnlPct,
  dataStale,
  isLoading,
}: Props) {
  if (isLoading) return <NetWorthSkeleton />;

  const netWorthNum = parseFloat(netWorth);
  const totalReturnNum = parseFloat(totalReturn);
  const totalReturnPctNum = parseFloat(totalReturnPct);
  const dailyPnlNum = parseFloat(dailyPnl);
  const dailyPnlPctNum = parseFloat(dailyPnlPct);

  const isPositiveReturn = totalReturnNum >= 0;
  const isPositiveDaily = dailyPnlNum >= 0;
  const isZeroDaily = dailyPnlNum === 0;

  const DailyIcon = isZeroDaily ? Minus : isPositiveDaily ? TrendingUp : TrendingDown;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-xl bg-zinc-900 text-white p-6 relative overflow-hidden"
    >
      {/* Decorative orbs — pointer-events-none, no scroll GPU impact */}
      <div
        className="absolute -right-8 -top-8 h-40 w-40 rounded-full bg-blue-500/8 pointer-events-none"
        aria-hidden
      />
      <div
        className="absolute right-4 bottom-4 h-20 w-20 rounded-full bg-emerald-500/8 pointer-events-none"
        aria-hidden
      />

      {/* Status row */}
      <div className="flex items-center gap-2 mb-4">
        {!dataStale ? (
          <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-400">
            <span
              className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse-dot inline-block"
              aria-hidden
            />
            Ao vivo
          </span>
        ) : (
          <span className="flex items-center gap-1.5 text-xs font-medium text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-md">
            Cotações desatualizadas
          </span>
        )}
      </div>

      {/* Main value */}
      <p className="text-xs font-semibold uppercase tracking-widest text-zinc-400 mb-1">
        Patrimônio Total
      </p>
      <p className="text-4xl font-extrabold tracking-tight tabular-nums">
        <AnimatedNumber value={netWorthNum} formatter={brlFormatter} />
      </p>

      {/* Secondary metrics */}
      <div className="flex flex-wrap gap-6 mt-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-zinc-400 mb-1">
            Retorno total
          </p>
          <p
            className={`text-base font-bold tabular-nums flex items-baseline gap-1 ${
              isPositiveReturn ? "text-emerald-400" : "text-red-400"
            }`}
          >
            <AnimatedNumber value={totalReturnNum} formatter={brlFormatter} />
            <span className="text-sm font-medium opacity-75">
              (<AnimatedNumber value={totalReturnPctNum} formatter={pctFormatter} />)
            </span>
          </p>
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-zinc-400 mb-1">
            Hoje
          </p>
          <div
            className={`flex items-center gap-1.5 text-base font-bold tabular-nums ${
              isZeroDaily
                ? "text-zinc-400"
                : isPositiveDaily
                ? "text-emerald-400"
                : "text-red-400"
            }`}
          >
            <DailyIcon className="h-4 w-4 shrink-0" strokeWidth={2.5} />
            <AnimatedNumber value={dailyPnlNum} formatter={brlFormatter} />
            <span className="text-sm font-medium opacity-75">
              (<AnimatedNumber value={dailyPnlPctNum} formatter={pctFormatter} />)
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
