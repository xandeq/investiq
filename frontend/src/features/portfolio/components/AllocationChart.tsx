"use client";
import { motion } from "framer-motion";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import { usePnl } from "@/features/portfolio/hooks/usePnl";

const CLASS_LABELS: Record<string, string> = {
  acao: "Ações",
  fii: "FIIs",
  renda_fixa: "Renda Fixa",
  bdr: "BDRs",
  etf: "ETFs",
  crypto: "Cripto",
  fundo: "Fundos",
};

const CLASS_COLORS: Record<string, string> = {
  acao: "#6366f1",
  fii: "#10b981",
  renda_fixa: "#f59e0b",
  bdr: "#3b82f6",
  etf: "#8b5cf6",
  crypto: "#f97316",
  fundo: "#14b8a6",
};

const FALLBACK_COLORS = ["#94a3b8", "#cbd5e1", "#e2e8f0"];

function fmtBRL(v: number) {
  if (v >= 1_000_000) return `R$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `R$${(v / 1_000).toFixed(0)}K`;
  return `R$${v.toFixed(0)}`;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-white border border-zinc-200 rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold text-zinc-800">{d.label}</p>
      <p className="text-zinc-500 mt-0.5 tabular-nums">
        {fmtBRL(d.value)} · {parseFloat(d.pct).toFixed(1)}%
      </p>
    </div>
  );
}

export function AllocationChart() {
  const { data: pnl, isLoading } = usePnl();

  if (isLoading) return <ShimmerSkeleton className="h-48 w-full rounded-xl" />;

  const allocation = pnl?.allocation ?? [];
  if (allocation.length === 0) return null;

  const chartData = allocation.map((item, i) => ({
    label: CLASS_LABELS[item.asset_class] ?? item.asset_class,
    value: parseFloat(item.total_value),
    pct: item.percentage,
    color: CLASS_COLORS[item.asset_class] ?? FALLBACK_COLORS[i % FALLBACK_COLORS.length],
  }));

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-xl border border-zinc-200 bg-white p-6"
    >
      <h3 className="text-[11px] font-bold uppercase tracking-wider text-zinc-400 mb-4">
        Alocação por Classe de Ativo
      </h3>

      <div className="flex items-center gap-6 flex-wrap">
        <div className="shrink-0" style={{ width: 160, height: 160 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={52}
                outerRadius={76}
                paddingAngle={2}
                dataKey="value"
                strokeWidth={0}
              >
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="flex flex-col gap-2 min-w-0">
          {chartData.map((item) => (
            <div key={item.label} className="flex items-center gap-2 text-xs">
              <span
                className="shrink-0 h-2.5 w-2.5 rounded-full"
                style={{ background: item.color }}
              />
              <span className="text-zinc-600 font-medium w-24 truncate">{item.label}</span>
              <span className="tabular-nums text-zinc-400 ml-auto pl-4">
                {parseFloat(item.pct).toFixed(1)}%
              </span>
              <span className="tabular-nums text-zinc-500 font-semibold w-20 text-right">
                {fmtBRL(item.value)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
