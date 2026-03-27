"use client";
import type { RecentTransaction } from "@/features/dashboard/types";
import { formatBRL, formatDate } from "@/lib/formatters";

interface Props {
  transactions: RecentTransaction[];
}

const TYPE_LABEL: Record<string, string> = { buy: "Compra", sell: "Venda" };
const TYPE_COLOR: Record<string, string> = { buy: "text-emerald-600", sell: "text-red-500" };

export function RecentTransactions({ transactions }: Props) {
  if (transactions.length === 0) {
    return (
      <div className="rounded-lg bg-white p-6">
        <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground mb-4">Últimas Transações</h3>
        <p className="text-sm text-muted-foreground">Nenhuma transação registrada</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg bg-white p-6">
      <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground mb-4">Últimas Transações</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="text-left px-3 py-2.5 text-xs font-bold uppercase tracking-wider text-muted-foreground rounded-l-md">Ativo</th>
              <th className="text-left px-3 py-2.5 text-xs font-bold uppercase tracking-wider text-muted-foreground">Tipo</th>
              <th className="text-right px-3 py-2.5 text-xs font-bold uppercase tracking-wider text-muted-foreground">Qtd</th>
              <th className="text-right px-3 py-2.5 text-xs font-bold uppercase tracking-wider text-muted-foreground">Preço</th>
              <th className="text-right px-3 py-2.5 text-xs font-bold uppercase tracking-wider text-muted-foreground rounded-r-md">Data</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((tx, i) => (
              <tr key={i} className="border-b border-gray-50 last:border-0 hover:bg-gray-50/50 transition-colors">
                <td className="py-2.5 px-3 font-semibold">{tx.ticker}</td>
                <td className={`py-2.5 px-3 font-medium ${TYPE_COLOR[tx.type] ?? ""}`}>
                  {TYPE_LABEL[tx.type] ?? tx.type}
                </td>
                <td className="py-2.5 px-3 text-right tabular-nums font-medium">{parseFloat(tx.quantity).toLocaleString("pt-BR")}</td>
                <td className="py-2.5 px-3 text-right tabular-nums font-medium">{formatBRL(tx.unit_price)}</td>
                <td className="py-2.5 px-3 text-right text-muted-foreground tabular-nums">{formatDate(tx.date)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
