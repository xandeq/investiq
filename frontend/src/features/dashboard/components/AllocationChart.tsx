"use client";
import { PieChart, Pie, Cell, Tooltip, Legend } from "recharts";
import { ChartContainer } from "@/components/ui/chart";
import type { AllocationItem } from "@/features/dashboard/types";
import { formatBRL, formatPct } from "@/lib/formatters";

const CHART_COLORS: Record<string, string> = {
  acao: "hsl(var(--chart-1))",
  fii: "hsl(var(--chart-2))",
  renda_fixa: "hsl(var(--chart-3))",
  bdr: "hsl(var(--chart-4))",
  etf: "hsl(var(--chart-5))",
};

const LABELS: Record<string, string> = {
  acao: "Ações", fii: "FIIs", renda_fixa: "Renda Fixa", bdr: "BDRs", etf: "ETFs",
};

interface Props {
  allocation: AllocationItem[];
}

export function AllocationChart({ allocation }: Props) {
  const chartData = allocation.map((item) => ({
    name: LABELS[item.asset_class] ?? item.asset_class,
    value: parseFloat(item.value),
    pct: item.pct,
    fill: CHART_COLORS[item.asset_class] ?? "#888",
  }));

  const chartConfig = Object.fromEntries(
    allocation.map((item) => [
      item.asset_class,
      { label: LABELS[item.asset_class] ?? item.asset_class },
    ])
  );

  if (allocation.length === 0) {
    return (
      <div className="rounded-lg bg-white p-6">
        <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground mb-4">Alocação por Classe</h3>
        <div className="flex items-center justify-center h-20 text-muted-foreground text-sm">
          Nenhum ativo cadastrado
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg bg-white p-6">
      <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground mb-4">Alocação por Classe</h3>
      <ChartContainer config={chartConfig} className="h-64 w-full">
        <PieChart>
          <Pie data={chartData} dataKey="value" innerRadius={55} outerRadius={85} paddingAngle={2}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={entry.fill} />
            ))}
          </Pie>
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.[0]) return null;
              const d = payload[0].payload;
              return (
                <div className="rounded-md bg-white border border-gray-100 px-3 py-2 text-xs">
                  <p className="font-semibold">{d.name}</p>
                  <p>{formatBRL(d.value)}</p>
                  <p>{formatPct(d.pct)}</p>
                </div>
              );
            }}
          />
          <Legend formatter={(value) => <span className="text-xs">{value}</span>} />
        </PieChart>
      </ChartContainer>
    </div>
  );
}
