"use client";
import { usePnl } from "@/features/portfolio/hooks/usePnl";
import { formatBRL, formatPct } from "@/lib/formatters";

const ASSET_CLASS_LABELS: Record<string, string> = {
  acao: "Ação", fii: "FII", renda_fixa: "Renda Fixa", bdr: "BDR", etf: "ETF",
};

function PnlCell({ value, pct }: { value: string | null; pct: string | null }) {
  if (value === null) return <span className="text-muted-foreground text-xs">—</span>;
  const isPositive = parseFloat(value) >= 0;
  return (
    <div className={isPositive ? "text-emerald-600" : "text-red-500"}>
      <div className="font-bold tabular-nums">{formatBRL(value)}</div>
      {pct && <div className="text-xs font-medium tabular-nums">{formatPct(pct)}</div>}
    </div>
  );
}

export function PnlTable() {
  const { data: pnl, isLoading } = usePnl();

  if (isLoading) return <div className="h-48 w-full rounded-lg bg-gray-100 animate-pulse" />;
  if (!pnl || pnl.positions.length === 0) {
    return (
      <div className="rounded-lg bg-white p-6">
        <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground mb-4">P&L por Ativo</h3>
        <p className="text-sm text-muted-foreground">Nenhum ativo na carteira</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg bg-white p-6">
      <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground mb-1">P&L por Ativo</h3>
      <p className="text-xs text-muted-foreground mb-4">desde a compra / no mês / no ano</p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="text-left px-3 py-2.5 text-xs font-bold uppercase tracking-wider text-muted-foreground rounded-l-md">Ativo</th>
              <th className="text-left px-3 py-2.5 text-xs font-bold uppercase tracking-wider text-muted-foreground">Classe</th>
              <th className="text-right px-3 py-2.5 text-xs font-bold uppercase tracking-wider text-muted-foreground">Qtd</th>
              <th className="text-right px-3 py-2.5 text-xs font-bold uppercase tracking-wider text-muted-foreground">Preço Médio</th>
              <th className="text-right px-3 py-2.5 text-xs font-bold uppercase tracking-wider text-muted-foreground">Custo Total</th>
              <th className="text-right px-3 py-2.5 text-xs font-bold uppercase tracking-wider text-muted-foreground">Preço Atual</th>
              <th className="text-right px-3 py-2.5 text-xs font-bold uppercase tracking-wider text-muted-foreground rounded-r-md">P&L Não Realiz.</th>
            </tr>
          </thead>
          <tbody>
            {pnl.positions.map((pos) => (
              <tr key={pos.ticker} className="border-b border-gray-50 last:border-0 hover:bg-gray-50/50 transition-colors">
                <td className="py-2.5 px-3 font-semibold">{pos.ticker}</td>
                <td className="py-2.5 px-3 text-muted-foreground text-xs">
                  {ASSET_CLASS_LABELS[pos.asset_class] ?? pos.asset_class}
                </td>
                <td className="py-2.5 px-3 text-right tabular-nums font-medium">
                  {parseFloat(pos.quantity).toLocaleString("pt-BR")}
                </td>
                <td className="py-2.5 px-3 text-right tabular-nums font-medium">{formatBRL(pos.cmp)}</td>
                <td className="py-2.5 px-3 text-right tabular-nums font-medium">{formatBRL(pos.total_cost)}</td>
                <td className="py-2.5 px-3 text-right tabular-nums font-medium">
                  {pos.current_price_stale ? (
                    <span className="text-xs text-amber-500">—</span>
                  ) : (
                    formatBRL(pos.current_price ?? "0")
                  )}
                </td>
                <td className="py-2.5 px-3 text-right">
                  <PnlCell value={pos.unrealized_pnl} pct={pos.unrealized_pnl_pct} />
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-gray-100 font-semibold bg-gray-50/50">
              <td colSpan={4} className="py-2.5 px-3 text-xs font-bold uppercase tracking-wider text-muted-foreground">Total</td>
              <td className="py-2.5 px-3 text-right tabular-nums font-bold">{formatBRL(pnl.total_portfolio_value)}</td>
              <td />
              <td className="py-2.5 px-3 text-right">
                <PnlCell value={pnl.unrealized_pnl_total} pct={null} />
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
