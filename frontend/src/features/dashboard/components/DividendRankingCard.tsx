"use client";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import { apiClient } from "@/lib/api-client";

interface DividendRankingItem {
  ticker: string;
  dy_pct: string;
  position_value: string;
  estimated_annual: string;
  sector: string | null;
}

interface DividendRankingResponse {
  items: DividendRankingItem[];
  total_estimated_annual: string;
  data_available: boolean;
}

function fmt(val: string) {
  return parseFloat(val).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  });
}

function DyBar({ dy }: { dy: number }) {
  const pct = Math.min(100, (dy / 20) * 100);
  const color = dy >= 10 ? "bg-emerald-400" : dy >= 6 ? "bg-blue-400" : "bg-zinc-300";
  return (
    <div className="flex items-center gap-2 justify-end">
      <div className="h-1 w-14 rounded-full bg-zinc-100 overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        />
      </div>
      <span
        className={`tabular-nums font-mono text-xs font-semibold ${
          dy >= 10 ? "text-emerald-700" : dy >= 6 ? "text-emerald-600" : "text-zinc-500"
        }`}
      >
        {dy.toFixed(1)}%
      </span>
    </div>
  );
}

export function DividendRankingCard() {
  const { data, isLoading } = useQuery<DividendRankingResponse>({
    queryKey: ["dividend-ranking"],
    queryFn: () => apiClient<DividendRankingResponse>("/dashboard/dividend-ranking"),
    staleTime: 15 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl border border-zinc-200 p-5 space-y-3">
        <ShimmerSkeleton className="h-4 w-44" />
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="flex items-center gap-3">
            <ShimmerSkeleton className="h-3.5 w-16" />
            <ShimmerSkeleton className="h-1.5 flex-1 rounded-full" />
            <ShimmerSkeleton className="h-3.5 w-12" />
          </div>
        ))}
      </div>
    );
  }
  if (!data?.data_available) return null;

  const top = data.items.slice(0, 8);
  const total = parseFloat(data.total_estimated_annual);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="bg-white rounded-2xl border border-zinc-200 p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-zinc-900">Ranking de Dividendos</h3>
        <span className="text-[11px] text-zinc-400 uppercase tracking-wide">
          Renda anual estimada
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-100">
              <th className="pb-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                Ativo
              </th>
              <th className="pb-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                DY
              </th>
              <th className="pb-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-zinc-400 hidden sm:table-cell">
                Posição
              </th>
              <th className="pb-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                Renda/ano
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-50">
            {top.map((item, i) => {
              const dy = parseFloat(item.dy_pct);
              return (
                <motion.tr
                  key={item.ticker}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{
                    duration: 0.28,
                    ease: [0.16, 1, 0.3, 1],
                    delay: i * 0.04,
                  }}
                  className="hover:bg-zinc-50 transition-colors"
                >
                  <td className="py-2.5">
                    <span className="font-mono font-bold text-zinc-900">{item.ticker}</span>
                    {item.sector && (
                      <span className="ml-2 text-[11px] text-zinc-400 hidden sm:inline">
                        {item.sector}
                      </span>
                    )}
                  </td>
                  <td className="py-2.5 text-right">
                    <DyBar dy={dy} />
                  </td>
                  <td className="py-2.5 text-right text-zinc-500 tabular-nums hidden sm:table-cell">
                    {fmt(item.position_value)}
                  </td>
                  <td className="py-2.5 text-right text-zinc-800 tabular-nums font-medium">
                    {fmt(item.estimated_annual)}
                  </td>
                </motion.tr>
              );
            })}
          </tbody>
          {total > 0 && (
            <tfoot>
              <tr className="border-t border-zinc-200">
                <td colSpan={2} className="pt-2.5 text-[11px] text-zinc-400 uppercase tracking-wide">
                  Total estimado
                </td>
                <td className="pt-2.5 text-right font-semibold text-zinc-900 hidden sm:table-cell" />
                <td className="pt-2.5 text-right font-bold text-emerald-700 tabular-nums">
                  {fmt(data.total_estimated_annual)}
                </td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </motion.div>
  );
}
