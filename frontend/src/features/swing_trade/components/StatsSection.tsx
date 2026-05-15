"use client";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

interface SwingStats {
  total_closed: number;
  data_available: boolean;
  winrate: number | null;
  avg_return_pct: number | null;
  profit_factor: number | null;
  r_sharpe: number | null;
  max_consecutive_losses: number;
  max_consecutive_wins: number;
  avg_holding_days: number | null;
  best_trade_pct: number | null;
  worst_trade_pct: number | null;
}

function fmt(v: number | null, suffix = "%", decimals = 1): string {
  if (v == null) return "—";
  return `${v.toFixed(decimals)}${suffix}`;
}

function StatCard({
  label,
  value,
  subtext,
  color = "text-foreground",
}: {
  label: string;
  value: string;
  subtext?: string;
  color?: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-white px-4 py-3">
      <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className={`text-xl font-extrabold mt-0.5 tabular-nums ${color}`}>{value}</p>
      {subtext && <p className="text-xs text-muted-foreground mt-0.5">{subtext}</p>}
    </div>
  );
}

export function StatsSection() {
  const { data, isLoading } = useQuery<SwingStats>({
    queryKey: ["swing-trade-stats"],
    queryFn: () => apiClient<SwingStats>("/swing-trade/stats"),
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
          <div key={n} className="h-20 rounded-xl bg-gray-100 animate-pulse" />
        ))}
      </div>
    );
  }

  if (!data || !data.data_available) {
    return (
      <div className="rounded-xl border border-dashed border-gray-200 bg-white p-10 text-center">
        <p className="text-2xl mb-2">📊</p>
        <p className="font-semibold text-gray-700">Nenhuma operação encerrada ainda</p>
        <p className="text-sm text-muted-foreground mt-1">
          Feche operações para ver suas estatísticas de performance.
        </p>
      </div>
    );
  }

  const winColor =
    (data.winrate ?? 0) >= 50 ? "text-green-600" : "text-red-600";
  const pfColor =
    (data.profit_factor ?? 0) >= 1 ? "text-green-600" : "text-red-600";
  const avgColor =
    (data.avg_return_pct ?? 0) >= 0 ? "text-green-600" : "text-red-600";

  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground">
        Baseado em <strong>{data.total_closed}</strong> operações encerradas
      </p>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        <StatCard
          label="Taxa de acerto"
          value={fmt(data.winrate)}
          subtext="% de operações lucrativas"
          color={winColor}
        />
        <StatCard
          label="Retorno médio"
          value={fmt(data.avg_return_pct)}
          subtext="por operação encerrada"
          color={avgColor}
        />
        <StatCard
          label="Profit Factor"
          value={fmt(data.profit_factor, "×", 2)}
          subtext="lucro bruto / perda bruta"
          color={pfColor}
        />
        <StatCard
          label="R-Sharpe"
          value={fmt(data.r_sharpe, "", 2)}
          subtext="consistência dos retornos"
        />
        <StatCard
          label="Melhor trade"
          value={fmt(data.best_trade_pct)}
          color="text-green-600"
        />
        <StatCard
          label="Pior trade"
          value={fmt(data.worst_trade_pct)}
          color="text-red-600"
        />
        <StatCard
          label="Seq. perdas máx."
          value={`${data.max_consecutive_losses}`}
          subtext="operações seguidas no vermelho"
          color={data.max_consecutive_losses >= 3 ? "text-red-600" : "text-foreground"}
        />
        <StatCard
          label="Tempo médio"
          value={data.avg_holding_days != null ? `${data.avg_holding_days}d` : "—"}
          subtext="dias por operação"
        />
      </div>
    </div>
  );
}
