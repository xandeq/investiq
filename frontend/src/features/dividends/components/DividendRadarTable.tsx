"use client";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import { tickerPath } from "@/lib/formatters";

// ─── Types ─────────────────────────────────────────────────────────────────────

export interface DividendRadarItem {
  ticker: string;
  dy_pct: number;
  ex_dividend_date: string | null;
  payout_ratio: number | null;
  technical_signal: "BUY" | "HOLD" | "SELL" | null;
  buy_score: number;
}

interface DividendRadarResponse {
  dividends: DividendRadarItem[];
}

// ─── Helpers ───────────────────────────────────────────────────────────────────

const MARKET_AVG_DY = 6.5; // benchmark for green highlight

function formatExDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function formatPayout(ratio: number | null): string {
  if (ratio === null || ratio === undefined) return "—";
  return `${(ratio * 100).toFixed(0)}%`;
}

// ─── Sub-components ────────────────────────────────────────────────────────────

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 71
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : score >= 31
      ? "bg-amber-50 text-amber-700 border-amber-200"
      : "bg-red-50 text-red-600 border-red-200";

  return (
    <span
      className={`inline-flex items-center justify-center rounded-full border px-2.5 py-0.5 text-[11px] font-bold tabular-nums leading-tight ${color}`}
    >
      {score}
    </span>
  );
}

const SIGNAL_STYLES: Record<string, string> = {
  BUY: "bg-emerald-50 text-emerald-700 border-emerald-200",
  HOLD: "bg-zinc-100 text-zinc-500 border-zinc-200",
  SELL: "bg-red-50 text-red-600 border-red-200",
};

const SIGNAL_LABELS: Record<string, string> = {
  BUY: "Comprar",
  HOLD: "Aguardar",
  SELL: "Vender",
};

function SignalBadge({ signal }: { signal: DividendRadarItem["technical_signal"] }) {
  if (!signal) {
    return <span className="text-[11px] text-zinc-300">—</span>;
  }
  const style = SIGNAL_STYLES[signal] ?? "bg-zinc-100 text-zinc-500 border-zinc-200";
  return (
    <span
      className={`inline-block rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest leading-tight ${style}`}
    >
      {SIGNAL_LABELS[signal] ?? signal}
    </span>
  );
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function SkeletonRows() {
  return (
    <>
      {[0, 1, 2, 3, 4].map((i) => (
        <tr key={i} className="border-b border-zinc-100 last:border-0">
          <td className="py-3 pr-4">
            <ShimmerSkeleton className="h-4 w-16" />
          </td>
          <td className="py-3 pr-4 text-right">
            <ShimmerSkeleton className="h-4 w-10 ml-auto" />
          </td>
          <td className="py-3 pr-4 hidden sm:table-cell">
            <ShimmerSkeleton className="h-4 w-24" />
          </td>
          <td className="py-3 pr-4 hidden sm:table-cell">
            <ShimmerSkeleton className="h-4 w-10 ml-auto" />
          </td>
          <td className="py-3 pr-4">
            <ShimmerSkeleton className="h-5 w-16 rounded-full" />
          </td>
          <td className="py-3">
            <ShimmerSkeleton className="h-5 w-10 rounded-full ml-auto" />
          </td>
        </tr>
      ))}
    </>
  );
}

// ─── Empty State ──────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <tr>
      <td colSpan={6}>
        <div className="flex flex-col items-center gap-2 py-10 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-50 border border-zinc-100">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              className="h-5 w-5 text-zinc-400"
              aria-hidden
            >
              <path
                d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <p className="text-sm text-zinc-400">Nenhum ativo com dividendo disponivel</p>
        </div>
      </td>
    </tr>
  );
}

// ─── Main Component ────────────────────────────────────────────────────────────

export function DividendRadarTable() {
  const router = useRouter();

  const { data, isLoading } = useQuery<DividendRadarResponse>({
    queryKey: ["dividends", "radar"],
    queryFn: () => apiClient<DividendRadarResponse>("/dividends/radar?limit=30"),
    staleTime: 15 * 60 * 1000,
  });

  // Already sorted by buy_score DESC from API; sort defensively on client too
  const rows = (data?.dividends ?? []).slice().sort((a, b) => b.buy_score - a.buy_score);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-xl border border-zinc-200/60 bg-white px-5 py-4 shadow-sm"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
          Dividend Radar
        </h2>
        <span className="text-[11px] text-zinc-300">
          ordenado por score de compra
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-100">
              {/* col 1 — always visible */}
              <th className="pb-2.5 pr-4 text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                Ticker
              </th>
              {/* col 2 — always visible */}
              <th className="pb-2.5 pr-4 text-right text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                DY %
              </th>
              {/* col 3 — hidden on mobile */}
              <th className="pb-2.5 pr-4 text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-400 hidden sm:table-cell">
                Data Ex-Div
              </th>
              {/* col 4 — hidden on mobile */}
              <th className="pb-2.5 pr-4 text-right text-[11px] font-semibold uppercase tracking-wider text-zinc-400 hidden sm:table-cell">
                Payout
              </th>
              {/* col 5 — always visible */}
              <th className="pb-2.5 pr-4 text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                Tecnico
              </th>
              {/* col 6 — always visible */}
              <th className="pb-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                Score
              </th>
            </tr>
          </thead>

          <tbody className="divide-y divide-zinc-100/60">
            {isLoading ? (
              <SkeletonRows />
            ) : rows.length === 0 ? (
              <EmptyState />
            ) : (
              rows.map((item, idx) => {
                const dyAboveAvg = item.dy_pct > MARKET_AVG_DY;
                const payoutUnsustainable =
                  item.payout_ratio !== null && item.payout_ratio > 1;

                return (
                  <motion.tr
                    key={item.ticker}
                    initial={{ opacity: 0, x: -4 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{
                      duration: 0.26,
                      ease: [0.16, 1, 0.3, 1],
                      delay: idx * 0.03,
                    }}
                    onClick={() => router.push(tickerPath(item.ticker))}
                    className="border-b border-zinc-50 last:border-0 hover:bg-zinc-50/70 cursor-pointer transition-colors duration-100"
                  >
                    {/* Ticker */}
                    <td className="py-2.5 pr-4">
                      <span className="font-mono font-bold text-zinc-900">
                        {item.ticker}
                      </span>
                    </td>

                    {/* DY % */}
                    <td className="py-2.5 pr-4 text-right tabular-nums">
                      <span
                        className={`text-sm font-semibold ${
                          dyAboveAvg ? "text-emerald-600" : "text-zinc-500"
                        }`}
                      >
                        {item.dy_pct.toFixed(1)}%
                      </span>
                    </td>

                    {/* Ex-Div Date — hidden on mobile */}
                    <td className="py-2.5 pr-4 text-zinc-400 tabular-nums text-xs hidden sm:table-cell">
                      {formatExDate(item.ex_dividend_date)}
                    </td>

                    {/* Payout Ratio — hidden on mobile */}
                    <td className="py-2.5 pr-4 text-right tabular-nums hidden sm:table-cell">
                      <span
                        className={`text-xs font-medium ${
                          payoutUnsustainable
                            ? "text-amber-600 font-semibold"
                            : "text-zinc-500"
                        }`}
                        title={
                          payoutUnsustainable
                            ? "Payout acima de 100% pode ser insustentavel"
                            : undefined
                        }
                      >
                        {formatPayout(item.payout_ratio)}
                        {payoutUnsustainable && (
                          <span className="ml-1 text-amber-400" aria-label="payout elevado">
                            !
                          </span>
                        )}
                      </span>
                    </td>

                    {/* Technical Signal */}
                    <td className="py-2.5 pr-4">
                      <SignalBadge signal={item.technical_signal} />
                    </td>

                    {/* Buy Score */}
                    <td className="py-2.5 text-right">
                      <ScoreBadge score={item.buy_score} />
                    </td>
                  </motion.tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}
