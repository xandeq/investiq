"use client";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { apiClient } from "@/lib/api-client";
import { formatPct } from "@/lib/formatters";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

interface MacroCache {
  selic: string;
  cdi: string;
  ipca: string;
  ptax_usd: string;
  unemployment_pct?: string | null;
  gdp_growth_pct?: string | null;
  data_stale: boolean;
  fetched_at: string | null;
}

const INDICATOR_STYLES = [
  { bg: "bg-blue-50 border-blue-100", label: "text-blue-600" },
  { bg: "bg-emerald-50 border-emerald-100", label: "text-emerald-600" },
  { bg: "bg-amber-50 border-amber-100", label: "text-amber-600" },
  { bg: "bg-zinc-50 border-zinc-200", label: "text-zinc-500" },
  { bg: "bg-rose-50 border-rose-100", label: "text-rose-600" },
  { bg: "bg-violet-50 border-violet-100", label: "text-violet-600" },
];

export function MacroIndicators() {
  const { data: macro, isLoading } = useQuery({
    queryKey: ["market-data", "macro"],
    queryFn: () => apiClient<MacroCache>("/market-data/macro"),
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: i * 0.05 }}
            className="rounded-xl border border-zinc-100 bg-white px-4 py-3 space-y-2"
          >
            <ShimmerSkeleton className="h-2.5 w-10" />
            <ShimmerSkeleton className="h-6 w-16" />
          </motion.div>
        ))}
      </div>
    );
  }
  if (!macro) return null;

  const indicators: { label: string; value: string; isCurrency?: boolean }[] = [
    { label: "SELIC", value: macro.selic },
    { label: "CDI", value: macro.cdi },
    { label: "IPCA", value: macro.ipca },
    { label: "PTAX", value: macro.ptax_usd, isCurrency: true },
    ...(macro.unemployment_pct != null
      ? [{ label: "Desemprego", value: macro.unemployment_pct }]
      : []),
    ...(macro.gdp_growth_pct != null
      ? [{ label: "PIB (trim.)", value: macro.gdp_growth_pct }]
      : []),
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {indicators.map(({ label, value, isCurrency }, i) => {
        const style = INDICATOR_STYLES[i] ?? INDICATOR_STYLES[INDICATOR_STYLES.length - 1];
        return (
          <motion.div
            key={label}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1], delay: i * 0.05 }}
            className={`rounded-xl border px-4 py-3 ${style.bg}`}
          >
            <p className={`text-[10px] font-semibold uppercase tracking-wider ${style.label}`}>
              {label}
            </p>
            <p className="text-lg font-extrabold mt-0.5 tracking-tight text-zinc-900 tabular-nums">
              {isCurrency
                ? `R$ ${parseFloat(value).toFixed(2)}`
                : formatPct(value)}
            </p>
          </motion.div>
        );
      })}
    </div>
  );
}
