"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import { usePortfolioHistory, type HistoryRange } from "../hooks/usePortfolioHistory";

const RANGES: { label: string; value: HistoryRange }[] = [
  { label: "1M", value: "1m" },
  { label: "3M", value: "3m" },
  { label: "6M", value: "6m" },
  { label: "1A", value: "1y" },
  { label: "Tudo", value: "all" },
];

function fmtBRL(value: number) {
  if (value >= 1_000_000) return `R$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `R$${(value / 1_000).toFixed(0)}K`;
  return `R$${value.toFixed(0)}`;
}

function fmtDate(dateStr: string) {
  const d = new Date(dateStr + "T12:00:00");
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-zinc-200 rounded-lg shadow-lg p-3 text-sm">
      <p className="font-semibold text-zinc-700 mb-2">
        {new Date(label + "T12:00:00").toLocaleDateString("pt-BR", {
          day: "2-digit", month: "short", year: "numeric",
        })}
      </p>
      {payload.map((entry: { color: string; name: string; value: number }) => (
        <div key={entry.name} className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ background: entry.color }} />
          <span className="text-zinc-400">{entry.name}:</span>
          <span className="font-semibold tabular-nums">
            {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(entry.value)}
          </span>
        </div>
      ))}
      {payload.length === 2 && (
        <div className="mt-2 pt-2 border-t border-zinc-100 text-xs">
          {(() => {
            const val = payload.find((p: { name: string }) => p.name === "Patrimônio")?.value ?? 0;
            const inv = payload.find((p: { name: string }) => p.name === "Investido")?.value ?? 0;
            if (inv <= 0) return null;
            const retPct = ((val - inv) / inv * 100).toFixed(2);
            const positive = parseFloat(retPct) >= 0;
            return (
              <span className={positive ? "text-emerald-600 font-semibold" : "text-red-500 font-semibold"}>
                Retorno: {positive ? "+" : ""}{retPct}%
              </span>
            );
          })()}
        </div>
      )}
    </div>
  );
}

export function PortfolioHistoryChart() {
  const [range, setRange] = useState<HistoryRange>("3m");
  const { data, isLoading } = usePortfolioHistory(range);

  const points = data?.points ?? [];
  const hasData = points.length > 0;

  const chartData = points.map((p) => ({
    date: p.date,
    total_value: parseFloat(p.total_value),
    total_invested: parseFloat(p.total_invested),
  }));

  const firstPoint = chartData[0];
  const lastPoint = chartData[chartData.length - 1];
  const periodReturn =
    firstPoint && lastPoint && firstPoint.total_invested > 0
      ? ((lastPoint.total_value - firstPoint.total_invested) / firstPoint.total_invested) * 100
      : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-xl border border-zinc-200 bg-white p-6"
    >
      <div className="flex items-start justify-between flex-wrap gap-3 mb-6">
        <div>
          <h3 className="text-[11px] font-bold uppercase tracking-wider text-zinc-400">
            Evolução do Patrimônio
          </h3>
          {periodReturn !== null && (
            <p className={`text-xs mt-1 font-semibold ${periodReturn >= 0 ? "text-emerald-600" : "text-red-500"}`}>
              {periodReturn >= 0 ? "+" : ""}{periodReturn.toFixed(2)}% no período
            </p>
          )}
        </div>

        <div className="flex gap-1 bg-zinc-100 rounded-lg p-1">
          {RANGES.map((r) => (
            <button
              key={r.value}
              onClick={() => setRange(r.value)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all duration-150 ${
                range === r.value
                  ? "bg-white text-zinc-900 shadow-sm"
                  : "text-zinc-400 hover:text-zinc-700"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <ShimmerSkeleton className="h-64 w-full rounded-lg" />}

      {!isLoading && !hasData && (
        <div className="h-64 flex flex-col items-center justify-center text-center gap-3 bg-zinc-50 rounded-lg">
          <div className="h-10 w-10 rounded-full bg-zinc-100 border border-zinc-200 flex items-center justify-center">
            <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden>
              <path d="M3 17l5-5 4 4 5-6 4 4" stroke="#a1a1aa" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-zinc-700">Dados históricos em construção</p>
            <p className="text-xs text-zinc-400 mt-1">
              O gráfico é populado diariamente após o fechamento do mercado.
              <br />Volte amanhã após as 18h30.
            </p>
          </div>
        </div>
      )}

      {!isLoading && hasData && (
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="gradValue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradInvested" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.1} />
                <stop offset="95%" stopColor="#94a3b8" stopOpacity={0} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="#f4f4f5" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={fmtDate}
              tick={{ fontSize: 11, fill: "#a1a1aa" }}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tickFormatter={fmtBRL}
              tick={{ fontSize: 11, fill: "#a1a1aa" }}
              axisLine={false}
              tickLine={false}
              width={64}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: "12px", paddingTop: "12px" }}
            />

            <Area
              type="monotone"
              dataKey="total_invested"
              name="Investido"
              stroke="#94a3b8"
              strokeWidth={1.5}
              strokeDasharray="4 2"
              fill="url(#gradInvested)"
              dot={false}
              activeDot={{ r: 4 }}
            />
            <Area
              type="monotone"
              dataKey="total_value"
              name="Patrimônio"
              stroke="#6366f1"
              strokeWidth={2.5}
              fill="url(#gradValue)"
              dot={false}
              activeDot={{ r: 5, strokeWidth: 2, stroke: "#fff" }}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}

      <p className="text-[10px] text-zinc-400 mt-3 text-right">
        Atualizado diariamente às 18h30 BRT · Patrimônio = preços de fechamento × quantidade
      </p>
    </motion.div>
  );
}
