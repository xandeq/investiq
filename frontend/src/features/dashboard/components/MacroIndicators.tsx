"use client";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { formatPct } from "@/lib/formatters";

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
  { bg: "bg-blue-50", label: "text-blue-600" },
  { bg: "bg-emerald-50", label: "text-emerald-600" },
  { bg: "bg-amber-50", label: "text-amber-600" },
  { bg: "bg-gray-100", label: "text-gray-600" },
  { bg: "bg-rose-50", label: "text-rose-600" },
  { bg: "bg-violet-50", label: "text-violet-600" },
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
        {[1, 2, 3, 4].map((n) => (
          <div key={n} className="h-16 rounded-lg bg-gray-100 animate-pulse" />
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
          <div key={label} className={`rounded-lg ${style.bg} px-4 py-3`}>
            <p className={`text-xs font-bold uppercase tracking-wider ${style.label}`}>{label}</p>
            <p className="text-lg font-extrabold mt-0.5 tracking-tight text-foreground">
              {isCurrency
                ? `R$ ${parseFloat(value).toFixed(2)}`
                : formatPct(value)}
            </p>
          </div>
        );
      })}
    </div>
  );
}
