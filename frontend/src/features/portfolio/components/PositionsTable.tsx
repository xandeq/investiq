"use client";
import { usePositions } from "@/features/portfolio/hooks/usePositions";
import { formatBRL } from "@/lib/formatters";
import { Skeleton } from "@/components/ui/skeleton";

export function PositionsTable() {
  const { data: positions, isLoading } = usePositions();

  if (isLoading) return <Skeleton className="h-24 w-full rounded-xl" />;
  if (!positions || positions.length === 0) return null;

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
