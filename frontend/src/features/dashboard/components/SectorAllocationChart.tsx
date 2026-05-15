"use client";
import { useQuery } from "@tanstack/react-query";
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
      <div className="rounded-lg bg-white p-6">
        <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground mb-4">
          Alocação por Setor
        </h3>
        <div className="h-48 rounded bg-gray-100 animate-pulse" />
      </div>
    );
  }

  if (!data || data.sectors.length === 0) {
    return (
      <div className="rounded-lg bg-white p-6">
        <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground mb-4">
          Alocação por Setor
        </h3>
        <div className="flex items-center justify-center h-20 text-muted-foreground text-sm">
          Registre transações de ações para ver alocação por setor
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
    <div className="rounded-lg bg-white p-6">
      <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground mb-4">
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
                <div className="rounded-md bg-white border border-gray-100 px-3 py-2 text-xs shadow-sm">
                  <p className="font-semibold mb-1">{d.sectorFull}</p>
                  <p>{formatBRL(d.value)}</p>
                  <p>{formatPct(d.pctLabel)}</p>
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
    </div>
  );
}
