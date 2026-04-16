"use client";
import { usePositions } from "@/features/portfolio/hooks/usePositions";
import { formatBRL } from "@/lib/formatters";
import { Skeleton } from "@/components/ui/skeleton";

export function PositionsTable() {
  const { data: positions, isLoading } = usePositions();

  if (isLoading) return <Skeleton className="h-24 w-full rounded-xl" />;
  if (!positions || positions.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 p-8 text-center">
        <p className="text-2xl mb-2">📭</p>
        <p className="font-semibold text-gray-700 text-sm">Nenhuma posição na carteira</p>
        <p className="text-xs text-muted-foreground mt-1 mb-4">
          Adicione transações de compra para ver seus ativos aqui.
        </p>
        <a
          href="/portfolio/transactions"
          className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
        >
          + Adicionar transação
        </a>
      </div>
    );
  }

  return (
    <div className="rounded-xl border bg-card p-4 shadow-sm">
      <p className="text-xs text-muted-foreground mb-2">{positions.length} ativos em carteira</p>
      <div className="flex flex-wrap gap-2">
        {positions.map((pos) => (
          <span key={pos.ticker} className="inline-flex items-center gap-1 rounded bg-muted px-2 py-1 text-xs font-medium">
            {pos.ticker}
            {pos.current_price && !pos.current_price_stale && (
              <span className="text-muted-foreground">{formatBRL(pos.current_price)}</span>
            )}
          </span>
        ))}
      </div>
    </div>
  );
}
