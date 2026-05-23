"use client";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from "recharts";
import type { ExpectancyByPattern } from "../types";

interface Props {
  data: ExpectancyByPattern[];
}

interface TooltipPayload {
  active?: boolean;
  payload?: Array<{ payload: ExpectancyByPattern & { expectancy: number } }>;
}

function CustomTooltip({ active, payload }: TooltipPayload) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs shadow-md">
      <p className="font-semibold text-zinc-800 mb-1">{d.pattern}</p>
      <p className="text-zinc-500">Expectativa: <span className={`tabular-nums ${d.expectancy >= 0 ? "text-emerald-600 font-medium" : "text-red-500 font-medium"}`}>{d.expectancy >= 0 ? "+" : ""}{d.expectancy.toFixed(2)}R</span></p>
      <p className="text-zinc-500">Taxa de acerto: <span className="font-medium text-zinc-700 tabular-nums">{(d.winrate * 100).toFixed(0)}%</span></p>
      <p className="text-zinc-500">Média R: <span className="font-medium text-zinc-700 tabular-nums">{d.avg_r >= 0 ? "+" : ""}{d.avg_r.toFixed(2)}</span></p>
      <p className="text-zinc-500">Operações: <span className="font-medium text-zinc-700 tabular-nums">{d.count}</span></p>
    </div>
  );
}

export function ExpectancyChart({ data }: Props) {
  if (!data || data.length === 0) return null;

  const chartData = data.map((d) => ({
    ...d,
    expectancy: parseFloat(d.expectancy.toFixed(3)),
  }));

  return (
    <div className="rounded-xl border border-zinc-100 bg-zinc-50 p-4">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-zinc-800">Expectativa por Setup</h3>
        <p className="text-xs text-zinc-400 mt-0.5">R médio esperado por operação, agrupado por padrão</p>
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart
          data={chartData}
          margin={{ top: 4, right: 4, left: 0, bottom: 4 }}
          barCategoryGap="28%"
        >
          <XAxis
            dataKey="pattern"
            tick={{ fontSize: 10, fill: "#71717a" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tickFormatter={(v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(1)}R`}
            tick={{ fontSize: 10, fill: "#71717a" }}
            axisLine={false}
            tickLine={false}
            width={42}
          />
          <ReferenceLine y={0} stroke="#e4e4e7" strokeWidth={1} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(0,0,0,0.03)" }} />
          <Bar dataKey="expectancy" radius={[3, 3, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.expectancy >= 0 ? "#10b981" : "#ef4444"}
                fillOpacity={0.85}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
