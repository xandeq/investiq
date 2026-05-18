"use client";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { apiClient } from "@/lib/api-client";
import { formatBRL } from "@/lib/formatters";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

// ─── Types ────────────────────────────────────────────────────────────────────

interface DividendEvent {
  ticker: string;
  asset_class: string;
  payment_date: string;
  ex_date: string;
  rate_per_share: string;
  quantity: string;
  estimated_income: string;
  label: string;
}

interface DividendCalendarResponse {
  events: DividendEvent[];
  data_available: boolean;
}

// ─── Date helpers ─────────────────────────────────────────────────────────────

function formatDisplayDate(dateStr: string): string {
  if (!dateStr) return "—";
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
  });
}

function isUrgent(dateStr: string): boolean {
  if (!dateStr) return false;
  const days = (new Date(dateStr).getTime() - Date.now()) / 86400000;
  return days >= 0 && days <= 14;
}

// ─── Label pill ───────────────────────────────────────────────────────────────

const LABEL_STYLES: Record<string, string> = {
  Dividendo: "bg-blue-50 text-blue-700 border-blue-200",
  JCP: "bg-violet-50 text-violet-700 border-violet-200",
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
    queryKey: ["dashboard", "dividend-calendar"],
    queryFn: () => apiClient<DividendCalendarResponse>("/dashboard/dividend-calendar"),
    staleTime: 30 * 60 * 1000,
  });

  return (
    <div className="rounded-xl border border-zinc-200 bg-white px-5 py-4 shadow-sm">
      <h2 className="mb-4 text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
        Calendário de Dividendos — próximos 90 dias
      </h2>

      {isLoading && <SkeletonRows />}

      {!isLoading && (!data || !data.data_available || data.events.length === 0) && (
        <p className="py-4 text-center text-sm text-zinc-400">
          Nenhum dividendo previsto para os próximos 90 dias
        </p>
      )}

      {!isLoading && data?.data_available && data.events.length > 0 && (() => {
        const events = data.events.slice(0, 20);
        const totalIncome = data.events.reduce(
          (sum, e) => sum + parseFloat(e.estimated_income || "0"),
          0
        );

        return (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-100">
                  <th className="pb-2.5 pr-4 text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                    Ticker
                  </th>
                  <th className="pb-2.5 pr-4 text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                    Tipo
                  </th>
                  <th className="pb-2.5 pr-4 text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                    Data Ex
                  </th>
                  <th className="pb-2.5 pr-4 text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                    Pagamento
                  </th>
                  <th className="pb-2.5 pr-4 text-right text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                    R$/cota
                  </th>
                  <th className="pb-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                    Estimado
                  </th>
                </tr>
              </thead>
              <tbody>
                {events.map((event, idx) => {
                  const urgent = isUrgent(event.payment_date);
                  return (
                    <motion.tr
                      key={`${event.ticker}-${event.ex_date}-${idx}`}
                      initial={{ opacity: 0, x: -6 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{
                        duration: 0.26,
                        ease: [0.16, 1, 0.3, 1],
                        delay: idx * 0.03,
                      }}
                      className="border-b border-zinc-50 last:border-0 hover:bg-zinc-50/60 transition-colors"
                    >
                      <td className="py-2.5 pr-4 font-bold font-mono text-zinc-900">
                        {event.ticker}
                      </td>
                      <td className="py-2.5 pr-4">
                        <LabelPill label={event.label} />
                      </td>
                      <td className="py-2.5 pr-4 text-zinc-400 tabular-nums">
                        {formatDisplayDate(event.ex_date)}
                      </td>
                      <td className={`py-2.5 pr-4 tabular-nums ${urgent ? "font-bold text-amber-600" : "text-zinc-400"}`}>
                        {formatDisplayDate(event.payment_date)}
                        {urgent && (
                          <span className="ml-1.5 inline-block rounded-full bg-amber-50 border border-amber-200 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">
                            Em breve
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 pr-4 text-right text-zinc-500 tabular-nums">
                        {formatBRL(event.rate_per_share)}
                      </td>
                      <td className="py-2.5 text-right font-medium text-emerald-600 tabular-nums">
                        {formatBRL(event.estimated_income)}
                      </td>
                    </motion.tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr className="border-t-2 border-zinc-200">
                  <td
                    colSpan={5}
                    className="pt-3 pr-4 text-right text-[11px] font-semibold uppercase tracking-wider text-zinc-400"
                  >
                    Total estimado no período
                  </td>
                  <td className="pt-3 text-right text-base font-extrabold text-emerald-600 tabular-nums">
                    {formatBRL(totalIncome)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        );
      })()}
    </div>
  );
}
