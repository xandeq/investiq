"use client";
import { motion } from "framer-motion";
import Link from "next/link";
import type { RecentTransaction } from "@/features/dashboard/types";
import { formatBRL, formatDate } from "@/lib/formatters";

interface Props {
  transactions: RecentTransaction[];
}

const TYPE_LABEL: Record<string, string> = { buy: "Compra", sell: "Venda" };
const TYPE_COLOR: Record<string, string> = {
  buy: "text-emerald-600",
  sell: "text-red-500",
};
const TYPE_BG: Record<string, string> = {
  buy: "bg-emerald-50 border-emerald-200 text-emerald-700",
  sell: "bg-red-50 border-red-200 text-red-600",
};

export function RecentTransactions({ transactions }: Props) {
  if (transactions.length === 0) {
    return (
      <div className="rounded-xl border border-zinc-200 bg-white p-6">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 mb-4">
          Últimas Transações
        </h3>
        <div className="flex flex-col items-center gap-3 py-6 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-50 border border-zinc-200">
            <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5 text-zinc-400" aria-hidden>
              <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <p className="text-sm font-medium text-zinc-700">Nenhuma transação registrada</p>
            <p className="text-xs text-zinc-400 mt-0.5">Adicione operações para ver seu histórico aqui</p>
          </div>
          <Link
            href="/portfolio/transactions"
            className="text-xs font-medium text-blue-500 hover:text-blue-600 active:scale-[0.97] transition-all duration-150"
          >
            Adicionar transação →
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-5">
      <h3 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 mb-4">
        Últimas Transações
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-100">
              <th className="text-left pb-2.5 text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                Ativo
              </th>
              <th className="text-left pb-2.5 text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                Tipo
              </th>
              <th className="text-right pb-2.5 text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                Qtd
              </th>
              <th className="text-right pb-2.5 text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                Preço
              </th>
              <th className="text-right pb-2.5 text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                Data
              </th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((tx, i) => (
              <motion.tr
                key={i}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{
                  duration: 0.28,
                  ease: [0.16, 1, 0.3, 1],
                  delay: i * 0.04,
                }}
                className="border-b border-zinc-50 last:border-0 hover:bg-zinc-50/60 transition-colors"
              >
                <td className="py-2.5 font-mono font-bold text-zinc-900">
                  {tx.ticker}
                </td>
                <td className="py-2.5">
                  <span
                    className={`inline-flex text-[11px] px-2 py-0.5 rounded-full border font-semibold ${TYPE_BG[tx.type] ?? "bg-zinc-100 text-zinc-500 border-zinc-200"}`}
                  >
                    {TYPE_LABEL[tx.type] ?? tx.type}
                  </span>
                </td>
                <td className="py-2.5 text-right tabular-nums font-medium text-zinc-700">
                  {parseFloat(tx.quantity).toLocaleString("pt-BR")}
                </td>
                <td className="py-2.5 text-right tabular-nums font-medium text-zinc-900">
                  {formatBRL(tx.unit_price)}
                </td>
                <td className="py-2.5 text-right tabular-nums text-zinc-400">
                  {formatDate(tx.date)}
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
