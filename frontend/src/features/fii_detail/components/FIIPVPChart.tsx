"use client";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

interface Props {
  pvp: number | null;
  bookValue: number | null;
  priceHistory?: { date: string; price: number }[];
}

export function FIIPVPChart({ pvp, bookValue, priceHistory }: Props) {
  if (!bookValue || !priceHistory || priceHistory.length === 0) {
    return (
      <div>
        <h3 className="text-sm font-medium mb-2">P/VP</h3>
        {pvp != null ? (
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold">{pvp.toFixed(2)}</span>
            <span className="text-sm text-muted-foreground">P/VP atual</span>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">P/VP nao disponivel</p>
        )}
      </div>
    );
  }

  const chartData = priceHistory.map((p) => ({
    date: p.date,
    pvp: parseFloat((p.price / bookValue).toFixed(2)),
  }));

  return (
    <div>
      <h3 className="text-sm font-medium mb-2">P/VP Historico (aproximado)</h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <XAxis dataKey="date" tick={{ fontSize: 10 }} />
          <YAxis domain={["auto", "auto"]} width={40} />
          <Tooltip formatter={(v: number) => [v.toFixed(2), "P/VP"]} />
          <Line
            type="monotone"
            dataKey="pvp"
            stroke="hsl(var(--chart-1))"
            dot={false}
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
      <p className="text-xs text-muted-foreground mt-1">
        * Aproximacao: preco historico / valor patrimonial atual
      </p>
    </div>
  );
}
