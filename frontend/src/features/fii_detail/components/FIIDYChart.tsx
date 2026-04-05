"use client";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import type { FIIDividendMonth } from "../types";

interface Props {
  data: FIIDividendMonth[];
}

export function FIIDYChart({ data }: Props) {
  if (!data || data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Historico de dividendos nao disponivel
      </p>
    );
  }

  const chartData = data.map((d) => ({
    month: formatMonth(d.month),
    dy_pct: d.rate,
  }));

  return (
    <div>
      <h3 className="text-sm font-medium mb-2">Dividendos Mensais (ultimos 12 meses)</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <XAxis dataKey="month" tick={{ fontSize: 10 }} />
          <YAxis tickFormatter={(v: number) => `R$${v.toFixed(2)}`} width={50} />
          <Tooltip formatter={(v: number) => [`R$${v.toFixed(2)}`, "Dividendo"]} />
          <Bar dataKey="dy_pct" fill="hsl(var(--chart-2))" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function formatMonth(ym: string): string {
  const [y, m] = ym.split("-");
  const months = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
  return `${months[parseInt(m, 10) - 1]}/${y.slice(2)}`;
}
