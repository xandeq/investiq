"use client";
import { motion } from "framer-motion";
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
  crypto: "#f7931a",
  fundo: "#6366f1",
};

const LABELS: Record<string, string> = {
  acao: "Ações",
  fii: "FIIs",
  renda_fixa: "Renda Fixa",
  bdr: "BDRs",
  etf: "ETFs",
  crypto: "Crypto",
  fundo: "Fundos",
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
      <div className="rounded-xl border border-zinc-200 bg-white p-5">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 mb-4">
          Alocação por Classe
        </h3>
        <div className="flex items-center justify-center h-20 text-zinc-400 text-sm">
          Nenhum ativo cadastrado
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-xl border border-zinc-200 bg-white p-5"
    >
      <h3 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 mb-4">
        Alocação por Classe
      </h3>
      <ChartContainer config={chartConfig} className="h-64 w-full">
        <PieChart>
          <Pie
            data={chartData}
            dataKey="value"
            innerRadius={55}
            outerRadius={85}
            paddingAngle={2}
            animationBegin={100}
            animationDuration={700}
          >
            {chartData.map((entry, i) => (
              <Cell key={i} fill={entry.fill} />
            ))}
          </Pie>
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.[0]) return null;
              const d = payload[0].payload;
              return (
                <div className="rounded-lg bg-white border border-zinc-200 px-3 py-2 text-xs shadow-sm">
                  <p className="font-semibold text-zinc-800 mb-1">{d.name}</p>
                  <p className="text-zinc-600">{formatBRL(d.value)}</p>
                  <p className="text-zinc-400">{formatPct(d.pct)}</p>
                </div>
              );
            }}
          />
          <Legend
            formatter={(value) => (
              <span className="text-xs text-zinc-600">{value}</span>
            )}
          />
        </PieChart>
      </ChartContainer>
    </motion.div>
  );
}
