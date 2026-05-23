"use client";
import { motion } from "framer-motion";
import { useMonthlyPerformance, type MonthlyPoint } from "@/features/dashboard/hooks/useMonthlyPerformance";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

const MONTH_LABELS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

function returnColor(pct: number): string {
  if (pct >= 5) return "bg-emerald-600 text-white";
  if (pct >= 2) return "bg-emerald-500 text-white";
  if (pct >= 0.5) return "bg-emerald-400 text-white";
  if (pct >= 0) return "bg-emerald-100 text-emerald-800";
  if (pct >= -0.5) return "bg-red-100 text-red-700";
  if (pct >= -2) return "bg-red-400 text-white";
  if (pct >= -5) return "bg-red-500 text-white";
  return "bg-red-700 text-white";
}

function buildGrid(months: MonthlyPoint[]): Map<string, MonthlyPoint> {
  const map = new Map<string, MonthlyPoint>();
  for (const m of months) {
    map.set(`${m.year}-${m.month}`, m);
  }
  return map;
}

export function MonthlyReturnHeatmap() {
  const { data, isLoading } = useMonthlyPerformance(3);

  if (isLoading) {
    return <ShimmerSkeleton className="h-48 w-full rounded-xl" />;
  }

  const months = data?.months ?? [];
  if (months.length === 0) {
    return null;
  }

  // Determine year range
  const years = [...new Set(months.map((m) => m.year))].sort();
  const grid = buildGrid(months);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-xl border border-zinc-200 bg-white p-5"
    >
      <h3 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 mb-4">
        Retorno mensal
      </h3>

      {/* Month header */}
      <div className="grid grid-cols-[40px_repeat(12,1fr)] gap-1 mb-1">
        <div />
        {MONTH_LABELS.map((lbl) => (
          <div key={lbl} className="text-center text-[10px] font-semibold text-zinc-400">
            {lbl}
          </div>
        ))}
      </div>

      {/* Year rows */}
      {years.map((year) => (
        <div key={year} className="grid grid-cols-[40px_repeat(12,1fr)] gap-1 mb-1">
          <div className="flex items-center text-[11px] font-semibold text-zinc-500 pr-1">
            {year}
          </div>
          {Array.from({ length: 12 }, (_, i) => i + 1).map((month) => {
            const point = grid.get(`${year}-${month}`);
            if (!point) {
              return (
                <div
                  key={month}
                  className="rounded aspect-square flex items-center justify-center bg-zinc-50"
                  title="Sem dados"
                />
              );
            }
            const colorClass = returnColor(point.return_pct);
            const isPositive = point.return_pct >= 0;
            return (
              <div
                key={month}
                className={`rounded aspect-square flex items-center justify-center text-[10px] font-bold tabular-nums cursor-default transition-opacity hover:opacity-80 ${colorClass}`}
                title={`${MONTH_LABELS[month - 1]}/${year}: ${isPositive ? "+" : ""}${point.return_pct.toFixed(2)}%`}
              >
                {isPositive ? "+" : ""}
                {point.return_pct.toFixed(1)}
              </div>
            );
          })}
        </div>
      ))}

      {/* Legend */}
      <div className="flex items-center gap-2 mt-3 flex-wrap">
        <span className="text-[10px] text-zinc-400">Retorno:</span>
        {[
          { label: "≥+5%", cls: "bg-emerald-600" },
          { label: "+2%", cls: "bg-emerald-500" },
          { label: "+0.5%", cls: "bg-emerald-400" },
          { label: "≈0%", cls: "bg-emerald-100 border border-emerald-200" },
          { label: "-0.5%", cls: "bg-red-100 border border-red-200" },
          { label: "-2%", cls: "bg-red-400" },
          { label: "≤-5%", cls: "bg-red-700" },
        ].map(({ label, cls }) => (
          <span key={label} className="flex items-center gap-1">
            <span className={`inline-block w-3 h-3 rounded ${cls}`} />
            <span className="text-[10px] text-zinc-400">{label}</span>
          </span>
        ))}
      </div>
    </motion.div>
  );
}
