"use client";
import { formatBRL, formatPct } from "@/lib/formatters";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface Props {
  netWorth: string;
  totalReturn: string;
  totalReturnPct: string;
  dailyPnl: string;
  dailyPnlPct: string;
  dataStale: boolean;
  isLoading: boolean;
}

export function NetWorthCard({ netWorth, totalReturn, totalReturnPct, dailyPnl, dailyPnlPct, dataStale, isLoading }: Props) {
  if (isLoading) return <div className="h-32 w-full rounded-lg bg-gray-100 animate-pulse" />;

  const isPositiveReturn = parseFloat(totalReturn) >= 0;
  const isPositiveDaily = parseFloat(dailyPnl) >= 0;
  const isZeroDaily = parseFloat(dailyPnl) === 0;

  const DailyIcon = isZeroDaily ? Minus : isPositiveDaily ? TrendingUp : TrendingDown;

  return (
    <div className="rounded-lg bg-[#111827] text-white p-6 relative overflow-hidden">
      <div className="absolute -right-8 -top-8 h-32 w-32 rounded-full bg-blue-500/10" />
      <div className="absolute -right-2 top-8 h-16 w-16 rounded-full bg-emerald-500/10" />

      {dataStale && (
        <span className="inline-flex items-center gap-1 text-xs bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded-md mb-3 font-medium">
          Cotações desatualizadas
        </span>
      )}

      <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Patrimônio Total</p>
      <p className="text-4xl font-extrabold mt-1 tracking-tight">{formatBRL(netWorth)}</p>

      <div className="flex flex-wrap gap-6 mt-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">Retorno total</p>
          <p className={`text-base font-bold ${isPositiveReturn ? "text-emerald-400" : "text-red-400"}`}>
            {formatBRL(totalReturn)} <span className="text-sm font-medium">({formatPct(totalReturnPct)})</span>
          </p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">Hoje</p>
          <div className={`flex items-center gap-1 text-base font-bold ${isZeroDaily ? "text-gray-400" : isPositiveDaily ? "text-emerald-400" : "text-red-400"}`}>
            <DailyIcon className="h-4 w-4" strokeWidth={2.5} />
            {formatBRL(dailyPnl)} <span className="text-sm font-medium">({formatPct(dailyPnlPct)})</span>
          </div>
        </div>
      </div>
    </div>
  );
}
