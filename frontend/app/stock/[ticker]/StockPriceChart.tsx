"use client";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import { useHistorical } from "@/hooks/useHistorical";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const close = payload[0]?.value as number;
  const d = new Date(label * 1000);
  return (
    <div className="bg-white border border-zinc-200 rounded-lg shadow-md px-3 py-2 text-xs">
      <p className="text-zinc-400">
        {d.toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" })}
      </p>
      <p className="font-semibold tabular-nums text-zinc-900 mt-0.5">
        {close.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
      </p>
    </div>
  );
}

function fmtBRL(v: number) {
  if (v >= 1_000) return `R$${(v / 1_000).toFixed(0)}K`;
  return `R$${v.toFixed(0)}`;
}

function fmtAxisDate(epoch: number) {
  const d = new Date(epoch * 1000);
  return d.toLocaleDateString("pt-BR", { month: "short" });
}

interface Props {
  ticker: string;
}

export function StockPriceChart({ ticker }: Props) {
  const { data, isLoading } = useHistorical(ticker);

  if (isLoading) return <ShimmerSkeleton className="h-48 w-full rounded-xl" />;
  if (!data || data.data_stale || data.points.length === 0) return null;

  const chartData = data.points.map((p) => ({
    date: p.date,
    close: parseFloat(p.close),
  }));

  const prices = chartData.map((p) => p.close);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const range = maxPrice - minPrice;
  const first = chartData[0].close;
  const last = chartData[chartData.length - 1].close;
  const returnPct = ((last - first) / first) * 100;
  const positive = returnPct >= 0;

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wider text-zinc-400">
            Evolução de Preço — 1 Ano
          </p>
          <p className={`text-xs mt-0.5 font-semibold ${positive ? "text-emerald-600" : "text-red-500"}`}>
            {positive ? "+" : ""}{returnPct.toFixed(2)}% no período
          </p>
        </div>
        <p className="text-xs text-zinc-400">
          {data.points.length} pregões
        </p>
      </div>

      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={`grad-${ticker}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={positive ? "#6366f1" : "#ef4444"} stopOpacity={0.15} />
              <stop offset="95%" stopColor={positive ? "#6366f1" : "#ef4444"} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f4f4f5" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={fmtAxisDate}
            tick={{ fontSize: 10, fill: "#a1a1aa" }}
            axisLine={false}
            tickLine={false}
            interval={Math.floor(chartData.length / 6)}
          />
          <YAxis
            domain={[minPrice - range * 0.05, maxPrice + range * 0.05]}
            tickFormatter={fmtBRL}
            tick={{ fontSize: 10, fill: "#a1a1aa" }}
            axisLine={false}
            tickLine={false}
            width={56}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="close"
            stroke={positive ? "#6366f1" : "#ef4444"}
            strokeWidth={2}
            fill={`url(#grad-${ticker})`}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 2, stroke: "#fff" }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
