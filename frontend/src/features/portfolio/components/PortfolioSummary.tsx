"use client";
import { usePnl } from "@/features/portfolio/hooks/usePnl";
import { formatBRL, formatPct } from "@/lib/formatters";

function MetricCard({
  label,
  value,
  sub,
  valueClass = "",
}: {
  label: string;
  value: string;
  sub?: string;
  valueClass?: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-5 py-4">
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground mb-1">{label}</p>
      <p className={`text-xl font-bold tabular-nums ${valueClass}`}>{value}</p>
      {sub && <p className="text-[11px] text-muted-foreground mt-0.5">{sub}</p>}
    </div>
  );
}

function pnlColor(val: string | null): string {
  if (!val) return "";
  return parseFloat(val) >= 0 ? "text-emerald-600" : "text-red-500";
}

export function PortfolioSummary() {
  const { data: pnl, isLoading } = usePnl();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 animate-pulse">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-20 rounded-lg bg-gray-100" />
        ))}
      </div>
    );
  }

  if (!pnl || pnl.positions.length === 0) return null;

  const totalReturnLabel =
    pnl.total_return_pct !== null
      ? `${parseFloat(pnl.total_return_pct) >= 0 ? "+" : ""}${formatPct(pnl.total_return_pct)}`
      : "—";

  const unrealizedPct =
    pnl.total_invested && parseFloat(pnl.total_invested) > 0
      ? ((parseFloat(pnl.unrealized_pnl_total) / parseFloat(pnl.total_invested)) * 100).toFixed(2)
      : null;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
      <MetricCard
        label="Patrimônio Total"
        value={formatBRL(pnl.total_portfolio_value)}
        sub="valor de mercado atual"
      />
      <MetricCard
        label="Total Investido"
        value={formatBRL(pnl.total_invested)}
        sub="custo médio das posições"
      />
      <MetricCard
        label="Retorno Total"
        value={totalReturnLabel}
        sub="realiz. + não realiz. / investido"
        valueClass={pnlColor(pnl.total_return_pct)}
      />
      <MetricCard
        label="P&L Não Realizado"
        value={formatBRL(pnl.unrealized_pnl_total)}
        sub={unrealizedPct !== null ? `${parseFloat(unrealizedPct) >= 0 ? "+" : ""}${unrealizedPct}% sobre custo` : undefined}
        valueClass={pnlColor(pnl.unrealized_pnl_total)}
      />
      <MetricCard
        label="P&L Realizado"
        value={formatBRL(pnl.realized_pnl_total)}
        sub="lucro bruto em vendas"
        valueClass={pnlColor(pnl.realized_pnl_total)}
      />
    </div>
  );
}
