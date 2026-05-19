"use client";
import { motion } from "framer-motion";
import { TrendUp, TrendDown } from "@phosphor-icons/react";
import Link from "next/link";
import { usePositionMovers, type MoverItem } from "@/features/dashboard/hooks/usePositionMovers";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

function fmtBRL(v: string) {
  const n = parseFloat(v);
  const abs = Math.abs(n);
  if (abs >= 1000) return `R$${(n / 1000).toFixed(1)}K`;
  return `R$${n.toFixed(2)}`;
}

function fmtPct(v: string) {
  const n = parseFloat(v);
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

function MoverChip({ item, variant }: { item: MoverItem; variant: "gainer" | "loser" }) {
  const isGain = variant === "gainer";
  const pnl = parseFloat(item.pnl_impact);

  return (
    <Link
      href={`/stock/${item.ticker}`}
      className={`flex items-center justify-between gap-3 px-3 py-2 rounded-lg border transition-colors hover:opacity-80 ${
        isGain
          ? "bg-emerald-50 border-emerald-100"
          : "bg-red-50 border-red-100"
      }`}
    >
      <div className="flex items-center gap-2 min-w-0">
        {isGain ? (
          <TrendUp size={14} weight="bold" className="text-emerald-600 shrink-0" aria-hidden />
        ) : (
          <TrendDown size={14} weight="bold" className="text-red-500 shrink-0" aria-hidden />
        )}
        <span className="font-mono font-bold text-xs text-zinc-800">{item.ticker}</span>
      </div>
      <div className="text-right shrink-0">
        <div className={`text-xs font-bold tabular-nums ${isGain ? "text-emerald-700" : "text-red-600"}`}>
          {pnl >= 0 ? "+" : ""}
          {fmtBRL(item.pnl_impact)}
        </div>
        <div className={`text-[10px] tabular-nums ${isGain ? "text-emerald-600" : "text-red-500"}`}>
          {fmtPct(item.change_pct)}
        </div>
      </div>
    </Link>
  );
}

export function PositionMoversCard() {
  const { data, isLoading } = usePositionMovers();

  if (isLoading) {
    return <ShimmerSkeleton className="h-36 w-full rounded-xl" />;
  }

  if (!data || (data.gainers.length === 0 && data.losers.length === 0)) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-xl border border-zinc-200 bg-white p-5"
    >
      <h3 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 mb-4">
        Maiores movimentos hoje
      </h3>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {data.gainers.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-600 mb-2">
              Altas
            </p>
            <div className="space-y-1.5">
              {data.gainers.map((item) => (
                <MoverChip key={item.ticker} item={item} variant="gainer" />
              ))}
            </div>
          </div>
        )}

        {data.losers.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-red-500 mb-2">
              Baixas
            </p>
            <div className="space-y-1.5">
              {data.losers.map((item) => (
                <MoverChip key={item.ticker} item={item} variant="loser" />
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}
