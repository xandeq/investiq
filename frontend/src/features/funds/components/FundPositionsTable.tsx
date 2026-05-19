"use client";
import { motion, AnimatePresence } from "framer-motion";
import { TrendUp, TrendDown, Warning, Bank } from "@phosphor-icons/react";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import type { FundPosition } from "../types";

interface Props {
  positions: FundPosition[];
  isLoading: boolean;
}

function fmt(v: string | null, decimals = 2): string {
  if (v == null) return "—";
  const n = parseFloat(v);
  return n.toLocaleString("pt-BR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function fmtBRL(v: string | null): string {
  if (v == null) return "—";
  const n = parseFloat(v);
  return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function fmtPct(v: string | null): string {
  if (v == null) return "—";
  const n = parseFloat(v) * 100;
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

function PnLCell({ pnl, pct }: { pnl: string | null; pct: string | null }) {
  if (pnl == null) return <span className="text-zinc-400 text-xs">—</span>;
  const n = parseFloat(pnl);
  const isPos = n >= 0;
  return (
    <div className={`flex items-center gap-1 ${isPos ? "text-emerald-600" : "text-red-500"}`}>
      {isPos ? <TrendUp size={12} /> : <TrendDown size={12} />}
      <span className="text-xs font-medium tabular-nums">{fmtBRL(pnl)}</span>
      <span className="text-[10px] opacity-80">({fmtPct(pct)})</span>
    </div>
  );
}

export function FundPositionsTable({ positions, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="rounded-xl border border-zinc-100 bg-white px-4 py-3 space-y-2">
            <ShimmerSkeleton className="h-3 w-48" />
            <ShimmerSkeleton className="h-3 w-32" />
          </div>
        ))}
      </div>
    );
  }

  if (positions.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-zinc-200 bg-zinc-50 py-12 text-center">
        <Bank size={32} className="text-zinc-300" />
        <p className="text-sm font-medium text-zinc-500">Nenhuma posição em fundos</p>
        <p className="text-xs text-zinc-400 max-w-xs">
          Registre transações com tipo "fundo" para ver suas posições aqui.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-zinc-200 bg-white">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-zinc-100 text-zinc-400 uppercase tracking-wider">
            <th className="px-4 py-3 text-left font-semibold">Fundo</th>
            <th className="px-4 py-3 text-right font-semibold">Cotas</th>
            <th className="px-4 py-3 text-right font-semibold hidden sm:table-cell">CMP</th>
            <th className="px-4 py-3 text-right font-semibold hidden md:table-cell">Custo Total</th>
            <th className="px-4 py-3 text-right font-semibold hidden sm:table-cell">NAV Atual</th>
            <th className="px-4 py-3 text-right font-semibold">P&L</th>
          </tr>
        </thead>
        <AnimatePresence initial={false}>
          <tbody className="divide-y divide-zinc-100">
            {positions.map((pos, i) => (
              <motion.tr
                key={pos.cnpj}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, delay: i * 0.04 }}
                className="hover:bg-zinc-50 transition-colors"
              >
                <td className="px-4 py-3">
                  <p className="font-semibold text-zinc-800 max-w-[180px] truncate">{pos.name}</p>
                  <p className="font-mono text-[10px] text-zinc-400">{pos.cnpj}</p>
                  {pos.nav_stale && (
                    <span className="inline-flex items-center gap-0.5 text-amber-500 text-[10px]">
                      <Warning size={10} />
                      cota desatualizada
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-zinc-700">
                  {fmt(pos.quantity, 6)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-zinc-600 hidden sm:table-cell">
                  {fmtBRL(pos.cmp)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-zinc-600 hidden md:table-cell">
                  {fmtBRL(pos.total_cost)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-zinc-700 hidden sm:table-cell">
                  {pos.current_nav != null ? fmtBRL(pos.current_nav) : <span className="text-zinc-400">—</span>}
                  {pos.quote_date && (
                    <p className="text-[10px] text-zinc-400">
                      {new Date(pos.quote_date + "T00:00:00").toLocaleDateString("pt-BR")}
                    </p>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  <PnLCell pnl={pos.unrealized_pnl} pct={pos.unrealized_pnl_pct} />
                </td>
              </motion.tr>
            ))}
          </tbody>
        </AnimatePresence>
      </table>
    </div>
  );
}
