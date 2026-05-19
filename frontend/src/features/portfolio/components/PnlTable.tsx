"use client";
import { motion } from "framer-motion";
import Link from "next/link";
import { usePnl } from "@/features/portfolio/hooks/usePnl";
import { formatBRL, formatPct } from "@/lib/formatters";
import { useSortedData } from "@/hooks/useSort";
import { SortableHeader } from "@/components/ui/SortableHeader";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import { PortfolioExportButtons } from "./PortfolioExportButtons";

const ASSET_CLASS_LABELS: Record<string, string> = {
  acao: "Ação", fii: "FII", renda_fixa: "Renda Fixa", bdr: "BDR", etf: "ETF", crypto: "Crypto",
  fundo: "Fundo",
};

const TH = "text-xs font-bold uppercase tracking-wider text-zinc-400 px-3 py-2.5";

function PnlCell({ value, pct }: { value: string | null; pct: string | null }) {
  if (value === null) return <span className="text-zinc-400 text-xs">—</span>;
  const isPositive = parseFloat(value) >= 0;
  return (
    <div className={isPositive ? "text-emerald-600" : "text-red-500"}>
      <div className="font-bold tabular-nums">{formatBRL(value)}</div>
      {pct && <div className="text-xs font-medium tabular-nums">{formatPct(pct)}</div>}
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="space-y-2 pt-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: i * 0.05 }}
          className="flex gap-3 px-3 py-2"
        >
          <ShimmerSkeleton className="h-4 w-14" />
          <ShimmerSkeleton className="h-4 w-12" />
          <ShimmerSkeleton className="h-4 w-10 ml-auto" />
          <ShimmerSkeleton className="h-4 w-20" />
          <ShimmerSkeleton className="h-4 w-20" />
          <ShimmerSkeleton className="h-4 w-16" />
          <ShimmerSkeleton className="h-4 w-20" />
        </motion.div>
      ))}
    </div>
  );
}

export function PnlTable() {
  const { data: pnl, isLoading } = usePnl();
  const { sorted, col, dir, toggle } = useSortedData(
    pnl?.positions ?? [],
    "ticker",
    "asc"
  );

  if (isLoading) {
    return (
      <div className="rounded-xl border border-zinc-200 bg-white p-6">
        <ShimmerSkeleton className="h-4 w-32 mb-4" />
        <TableSkeleton />
      </div>
    );
  }

  if (!pnl || pnl.positions.length === 0) {
    return (
      <div className="rounded-xl border border-zinc-200 bg-white p-6">
        <h3 className="text-[11px] font-bold uppercase tracking-wider text-zinc-400 mb-4">P&L por Ativo</h3>
        <p className="text-sm text-zinc-400">Nenhum ativo na carteira</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-xl border border-zinc-200 bg-white p-6"
    >
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-[11px] font-bold uppercase tracking-wider text-zinc-400">P&L por Ativo</h3>
        <PortfolioExportButtons pnl={pnl} />
      </div>
      <p className="text-xs text-zinc-400 mb-4">desde a compra / no mês / no ano</p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-100">
              <SortableHeader col="ticker" label="Ativo" activeCol={col} dir={dir} onSort={toggle} className={`${TH} rounded-l-md`} />
              <SortableHeader col="asset_class" label="Classe" activeCol={col} dir={dir} onSort={toggle} className={TH} />
              <SortableHeader col="quantity" label="Qtd" activeCol={col} dir={dir} onSort={toggle} className={`${TH} text-right`} align="right" />
              <SortableHeader col="cmp" label="Preço Médio" activeCol={col} dir={dir} onSort={toggle} className={`${TH} text-right`} align="right" />
              <SortableHeader col="total_cost" label="Custo Total" activeCol={col} dir={dir} onSort={toggle} className={`${TH} text-right`} align="right" />
              <SortableHeader col="current_price" label="Preço Atual" activeCol={col} dir={dir} onSort={toggle} className={`${TH} text-right`} align="right" />
              <SortableHeader col="unrealized_pnl" label="P&L Não Realiz." activeCol={col} dir={dir} onSort={toggle} className={`${TH} text-right rounded-r-md`} align="right" />
            </tr>
          </thead>
          <tbody>
            {sorted.map((pos, i) => (
              <motion.tr
                key={pos.ticker as string}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1], delay: i * 0.03 }}
                className="border-b border-zinc-50 last:border-0 hover:bg-zinc-50/60 transition-colors"
              >
                <td className="py-2.5 px-3 font-semibold">
                  <Link
                    href={`/stock/${pos.ticker as string}`}
                    className="font-mono hover:text-blue-600 transition-colors"
                    title={`Ver análise de ${pos.ticker as string}`}
                  >
                    {pos.ticker as string}
                  </Link>
                </td>
                <td className="py-2.5 px-3 text-zinc-400 text-xs">
                  {ASSET_CLASS_LABELS[pos.asset_class as string] ?? (pos.asset_class as string)}
                </td>
                <td className="py-2.5 px-3 text-right tabular-nums font-medium">
                  {parseFloat(pos.quantity as string).toLocaleString("pt-BR")}
                </td>
                <td className="py-2.5 px-3 text-right tabular-nums font-medium">{formatBRL(pos.cmp as string)}</td>
                <td className="py-2.5 px-3 text-right tabular-nums font-medium">{formatBRL(pos.total_cost as string)}</td>
                <td className="py-2.5 px-3 text-right tabular-nums font-medium">
                  {pos.current_price_stale ? (
                    <span className="text-xs text-amber-500">—</span>
                  ) : (
                    formatBRL((pos.current_price ?? "0") as string)
                  )}
                </td>
                <td className="py-2.5 px-3 text-right">
                  <PnlCell value={pos.unrealized_pnl as string | null} pct={pos.unrealized_pnl_pct as string | null} />
                </td>
              </motion.tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-zinc-100 font-semibold bg-zinc-50/50">
              <td colSpan={4} className="py-2.5 px-3 text-[10px] font-bold uppercase tracking-wider text-zinc-400">Total</td>
              <td className="py-2.5 px-3 text-right tabular-nums font-bold">{formatBRL(pnl.total_portfolio_value)}</td>
              <td className="py-2.5 px-3 text-right">
                <div className="text-[10px] text-zinc-400 font-normal">Realizado</div>
                <PnlCell value={pnl.realized_pnl_total} pct={null} />
              </td>
              <td className="py-2.5 px-3 text-right">
                <div className="text-[10px] text-zinc-400 font-normal">Não Realizado</div>
                <PnlCell value={pnl.unrealized_pnl_total} pct={null} />
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </motion.div>
  );
}
