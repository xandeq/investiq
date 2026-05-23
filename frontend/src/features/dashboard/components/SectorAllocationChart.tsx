"use client";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from "recharts";
import { apiClient } from "@/lib/api-client";
import { formatBRL, formatPct } from "@/lib/formatters";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

interface SectorItem {
  sector: string;
  value: string;
  pct: string;
}

interface SectorAllocation {
  sectors: SectorItem[];
}

// Blue gradient palette cycling through chart CSS vars then falling back to hsl values
const BAR_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
];

function truncate(text: string, max: number): string {
  return text.length > max ? text.slice(0, max) + "…" : text;
}

export function SectorAllocationChart() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard", "sector-allocation"],
    queryFn: () => apiClient<SectorAllocation>("/dashboard/sector-allocation"),
    staleTime: 10 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="rounded-xl border border-zinc-200 bg-white p-5 space-y-4">
        <ShimmerSkeleton className="h-3 w-32" />
        <ShimmerSkeleton className="h-44 rounded-lg" />
      </div>
    );
  }

  if (!data || data.sectors.length === 0) {
    return (
      <div className="rounded-xl border border-zinc-200 bg-white p-5">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 mb-4">
          Alocação por Setor
        </h3>
        <div className="flex flex-col items-center justify-center gap-3 py-6 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-50 border border-zinc-200">
            <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden>
              <rect x="3" y="3" width="7" height="7" rx="1" stroke="#a1a1aa" strokeWidth="1.5" />
              <rect x="14" y="3" width="7" height="7" rx="1" stroke="#a1a1aa" strokeWidth="1.5" />
              <rect x="3" y="14" width="7" height="7" rx="1" stroke="#a1a1aa" strokeWidth="1.5" />
              <rect x="14" y="14" width="7" height="7" rx="1" stroke="#a1a1aa" strokeWidth="1.5" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-medium text-zinc-700">Nenhuma alocação por setor</p>
            <p className="text-xs text-zinc-400 mt-0.5">Registre ações para ver a distribuição setorial.</p>
          </div>
        </div>
      </div>
    );
  }

  const chartData = data.sectors.map((item) => ({
    sector: truncate(item.sector, 20),
    sectorFull: item.sector,
    pct: parseFloat(item.pct),
    value: parseFloat(item.value),
    pctLabel: item.pct,
  }));

  // Dynamic chart height: at least 180px, 40px per bar
  const chartHeight = Math.max(180, chartData.length * 40);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-xl border border-zinc-200 bg-white p-5"
    >
      <h3 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 mb-4">
        Alocação por Setor
      </h3>
      <ResponsiveContainer width="100%" height={chartHeight}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 0, right: 24, left: 8, bottom: 0 }}
        >
          <XAxis
            type="number"
            unit="%"
            tick={{ fontSize: 11 }}
            tickFormatter={(v) => `${v}%`}
            domain={[0, "dataMax"]}
          />
          <YAxis
            type="category"
            dataKey="sector"
            width={130}
            tick={{ fontSize: 11 }}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.[0]) return null;
              const d = payload[0].payload as typeof chartData[number];
              return (
                <div className="rounded-lg bg-white border border-zinc-200 px-3 py-2 text-xs shadow-sm">
                  <p className="font-semibold text-zinc-800 mb-1">{d.sectorFull}</p>
                  <p className="text-zinc-600 tabular-nums">{formatBRL(d.value)}</p>
                  <p className="text-zinc-400 tabular-nums">{formatPct(d.pctLabel)}</p>
                </div>
              );
            }}
          />
          <Bar dataKey="pct" radius={[0, 4, 4, 0]}>
            {chartData.map((_, i) => (
              <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </motion.div>
  );
}
