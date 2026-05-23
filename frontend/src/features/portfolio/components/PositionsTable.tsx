"use client";
import Link from "next/link";
import { motion } from "framer-motion";
import { usePositions } from "@/features/portfolio/hooks/usePositions";
import { formatBRL } from "@/lib/formatters";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

export function PositionsTable() {
  const { data: positions, isLoading } = usePositions();

  if (isLoading) return <ShimmerSkeleton className="h-24 w-full rounded-xl" />;

  if (!positions || positions.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="rounded-xl border border-dashed border-zinc-200 bg-zinc-50 p-8 text-center"
      >
        <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-white border border-zinc-200">
          <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden>
            <path d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0H4" stroke="#A1A1AA" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <p className="font-semibold text-zinc-700 text-sm">Nenhuma posição na carteira</p>
        <p className="text-xs text-zinc-400 mt-1 mb-4">
          Adicione transações de compra para ver seus ativos aqui.
        </p>
        <Link
          href="/portfolio/transactions"
          className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold bg-blue-500 text-white rounded-lg hover:bg-blue-600 active:scale-[0.97] transition-all duration-150"
        >
          + Adicionar transação
        </Link>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm"
    >
      <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 mb-2">
        {positions.length} ativos em carteira
      </p>
      <div className="flex flex-wrap gap-2">
        {positions.map((pos, i) => (
          <motion.span
            key={pos.ticker}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.2, delay: i * 0.025 }}
            className="inline-flex items-center gap-1 rounded-lg bg-zinc-50 border border-zinc-200 px-2.5 py-1 text-xs font-medium text-zinc-800"
          >
            <span className="font-mono font-bold">{pos.ticker}</span>
            {pos.current_price && !pos.current_price_stale && (
              <span className="text-zinc-400 tabular-nums">{formatBRL(pos.current_price)}</span>
            )}
          </motion.span>
        ))}
      </div>
    </motion.div>
  );
}
