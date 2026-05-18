"use client";
import { motion } from "framer-motion";
import { usePnl } from "@/features/portfolio/hooks/usePnl";
import { formatBRL, formatPct } from "@/lib/formatters";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

function MetricCard({
  label,
  value,
  sub,
  valueClass = "",
  index = 0,
}: {
  label: string;
  value: string;
  sub?: string;
  valueClass?: string;
  index?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1], delay: index * 0.05 }}
      className="rounded-xl border border-zinc-200 bg-white px-5 py-4"
    >
      <p className="text-[10px] uppercase tracking-wider font-semibold text-zinc-400 mb-1">{label}</p>
      <p className={`text-xl font-bold tabular-nums ${valueClass}`}>{value}</p>
      {sub && <p className="text-[11px] text-zinc-400 mt-0.5">{sub}</p>}
    </motion.div>
  );
}

function pnlColor(val: string | null): string {
  if (!val) return "";
  return parseFloat(val) >= 0 ? "text-emerald-600" : "text-red-500";
}

export function PortfolioSummary() {
  const { data: pnl, isLoading, isError, refetch } = usePnl();

  if (isError) {
    return (
      <div className="flex items-center justify-between gap-2 rounded-xl border border-zinc-100 bg-white px-5 py-3">
        <p className="text-sm text-zinc-400">Erro ao carregar resumo do portfólio.</p>
        <button
          onClick={() => refetch()}
          className="text-xs text-zinc-500 hover:text-blue-600 transition-colors underline underline-offset-2"
        >
          Tentar novamente
        </button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: i * 0.05 }}
            className="rounded-xl border border-zinc-100 bg-white px-5 py-4 space-y-2"
          >
            <ShimmerSkeleton className="h-2.5 w-20" />
            <ShimmerSkeleton className="h-6 w-28" />
            <ShimmerSkeleton className="h-2 w-32" />
          </motion.div>
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
      <MetricCard index={0} label="Patrimônio Total" value={formatBRL(pnl.total_portfolio_value)} sub="valor de mercado atual" />
      <MetricCard index={1} label="Total Investido" value={formatBRL(pnl.total_invested)} sub="custo médio das posições" />
      <MetricCard index={2} label="Retorno Total" value={totalReturnLabel} sub="realiz. + não realiz. / investido" valueClass={pnlColor(pnl.total_return_pct)} />
      <MetricCard index={3} label="P&L Não Realizado" value={formatBRL(pnl.unrealized_pnl_total)} sub={unrealizedPct !== null ? `${parseFloat(unrealizedPct) >= 0 ? "+" : ""}${unrealizedPct}% sobre custo` : undefined} valueClass={pnlColor(pnl.unrealized_pnl_total)} />
      <MetricCard index={4} label="P&L Realizado" value={formatBRL(pnl.realized_pnl_total)} sub="lucro bruto em vendas" valueClass={pnlColor(pnl.realized_pnl_total)} />
    </div>
  );
}
