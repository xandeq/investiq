"use client";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Warning } from "@phosphor-icons/react";
import { apiClient } from "@/lib/api-client";
import { formatBRL } from "@/lib/formatters";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

// ─── Types ────────────────────────────────────────────────────────────────────

interface DividendCalendarEntry {
  ticker: string;
  asset_class: string;
  label: string;
  ex_div_date: string;
  payment_date: string | null;
  rate_per_share: string;
  quantity: string;
  projected_income: string;
  source: "brapi" | "estimated";
}

interface DividendCalendarResponse {
  entries: DividendCalendarEntry[];
  total_projected_30d: string;
  total_projected_60d: string;
  total_projected_90d: string;
  generated_at: string;
}

// ─── Date helpers ─────────────────────────────────────────────────────────────

function formatDisplayDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
  });
}

function isUrgent(dateStr: string | null | undefined): boolean {
  if (!dateStr) return false;
  const days = (new Date(dateStr).getTime() - Date.now()) / 86400000;
  return days >= 0 && days <= 14;
}

// ─── Label pill ───────────────────────────────────────────────────────────────

const LABEL_STYLES: Record<string, string> = {
  DIVIDENDO: "bg-blue-50 text-blue-700 border-blue-200",
  JCP: "bg-violet-50 text-violet-700 border-violet-200",
  RENDIMENTO: "bg-emerald-50 text-emerald-700 border-emerald-200",
  Dividendo: "bg-blue-50 text-blue-700 border-blue-200",
  Rendimento: "bg-emerald-50 text-emerald-700 border-emerald-200",
};

function LabelPill({ label }: { label: string }) {
  const style = LABEL_STYLES[label] ?? "bg-zinc-100 text-zinc-600 border-zinc-200";
  return (
    <span
      className={`inline-block rounded-full border px-2 py-0.5 text-[11px] font-semibold leading-tight ${style}`}
    >
      {label}
    </span>
  );
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function SkeletonRows() {
  return (
    <div className="space-y-2">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: i * 0.06 }}
          className="flex items-center gap-3 py-2"
        >
          <ShimmerSkeleton className="h-4 w-16" />
          <ShimmerSkeleton className="h-5 w-20 rounded-full" />
          <ShimmerSkeleton className="h-3 w-14 ml-auto" />
          <ShimmerSkeleton className="h-3 w-14" />
          <ShimmerSkeleton className="h-3 w-16" />
        </motion.div>
      ))}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function DividendCalendarCard() {
  const { data, isLoading } = useQuery({
    queryKey: ["portfolio", "dividend-calendar"],
    queryFn: () => apiClient<DividendCalendarResponse>("/portfolio/dividend-calendar?days=90"),
    staleTime: 30 * 60 * 1000,
  });

  const summaryChips = data
    ? [
        { label: "Próx. 30d", value: formatBRL(data.total_projected_30d), color: "text-zinc-700" },
        { label: "Próx. 60d", value: formatBRL(data.total_projected_60d), color: "text-blue-700" },
        { label: "Próx. 90d", value: formatBRL(data.total_projected_90d), color: "text-emerald-700" },
      ]
    : [];

  return (
    <div className="rounded-xl border border-zinc-200 bg-white px-5 py-4 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
          Calendário de Dividendos
        </h2>
        <span className="text-[11px] text-zinc-300">próximos 90 dias</span>
      </div>

      {isLoading && (
        <>
          <div className="grid grid-cols-3 gap-2 mb-4">
            {[0, 1, 2].map((i) => <ShimmerSkeleton key={i} className="h-12 rounded-lg" />)}
          </div>
          <SkeletonRows />
        </>
      )}

      {!isLoading && data && data.entries.length > 0 && (
        <>
          {/* Summary chips */}
          <div className="grid grid-cols-3 gap-2 mb-4">
            {summaryChips.map(({ label, value, color }, i) => (
              <motion.div
                key={label}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] as const, delay: i * 0.05 }}
                className="rounded-lg bg-zinc-50 border border-zinc-100 px-3 py-2"
              >
                <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide">{label}</p>
                <p className={`text-sm font-extrabold mt-0.5 tabular-nums ${color}`}>{value}</p>
              </motion.div>
            ))}
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-100">
                  <th className="pb-2.5 pr-4 text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-400">Ticker</th>
                  <th className="pb-2.5 pr-4 text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-400">Tipo</th>
                  <th className="pb-2.5 pr-4 text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-400">Data Ex</th>
                  <th className="pb-2.5 pr-4 text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-400">Pagamento</th>
                  <th className="pb-2.5 pr-4 text-right text-[11px] font-semibold uppercase tracking-wider text-zinc-400">R$/cota</th>
                  <th className="pb-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-zinc-400">Projetado</th>
                </tr>
              </thead>
              <tbody>
                {data.entries.slice(0, 20).map((entry, idx) => {
                  const urgent = isUrgent(entry.payment_date);
                  const estimated = entry.source === "estimated";
                  return (
                    <motion.tr
                      key={`${entry.ticker}-${entry.ex_div_date}-${idx}`}
                      initial={{ opacity: 0, x: -6 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.26, ease: [0.16, 1, 0.3, 1] as const, delay: idx * 0.03 }}
                      className="border-b border-zinc-50 last:border-0 hover:bg-zinc-50/60 transition-colors"
                    >
                      <td className="py-2.5 pr-4 font-bold font-mono text-zinc-900">
                        {entry.ticker}
                        {estimated && (
                          <Warning size={12} weight="fill" className="inline ml-1 text-amber-400" aria-label="estimado" />
                        )}
                      </td>
                      <td className="py-2.5 pr-4">
                        <LabelPill label={entry.label} />
                      </td>
                      <td className="py-2.5 pr-4 text-zinc-400 tabular-nums">
                        {formatDisplayDate(entry.ex_div_date)}
                      </td>
                      <td className={`py-2.5 pr-4 tabular-nums ${urgent ? "font-bold text-amber-600" : "text-zinc-400"}`}>
                        {formatDisplayDate(entry.payment_date)}
                        {urgent && (
                          <span className="ml-1.5 inline-block rounded-full bg-amber-50 border border-amber-200 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">
                            Em breve
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 pr-4 text-right text-zinc-500 tabular-nums">
                        {formatBRL(entry.rate_per_share)}
                      </td>
                      <td className="py-2.5 text-right font-medium text-emerald-600 tabular-nums">
                        {formatBRL(entry.projected_income)}
                      </td>
                    </motion.tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}

      {!isLoading && data && data.entries.length === 0 && (
        <p className="py-6 text-center text-sm text-zinc-400">
          Nenhum dividendo previsto para os próximos 90 dias
        </p>
      )}
    </div>
  );
}
