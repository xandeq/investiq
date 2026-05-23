"use client";

import { Info } from "@phosphor-icons/react";
import type { CashParkingRow } from "../types";

function asNumber(value: string | number | null | undefined): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function formatBRL(value: string | number): string {
  return asNumber(value).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatPct(value: string | number, multiplier = 1): string {
  return `${(asNumber(value) * multiplier).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}%`;
}

function displayLabel(label: string): string {
  return label === "Poupanca" ? "Poupança" : label;
}

export function CashParkingTable({ rows }: { rows: CashParkingRow[] }) {
  if (rows.length === 0) return null;

  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-200 bg-white">
      <table className="min-w-full divide-y divide-zinc-200 text-sm">
        <thead className="bg-zinc-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-zinc-500">Rank</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-zinc-500">Alternativa</th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-zinc-500">Taxa bruta</th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-zinc-500">IOF</th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-zinc-500">IR</th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-zinc-500">Líquido</th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-zinc-500">Retorno</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100">
          {rows.map((row) => {
            const isTop = row.rank === 1;
            return (
              <tr key={row.label} className={isTop ? "bg-emerald-50" : "hover:bg-zinc-50"}>
                <td className="px-4 py-3">
                  <span className={`inline-flex h-7 min-w-7 items-center justify-center rounded-full px-2 text-xs font-bold ${
                    isTop ? "bg-emerald-600 text-white" : "bg-zinc-100 text-zinc-700"
                  }`}>
                    {row.rank}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="font-semibold text-zinc-900">{displayLabel(row.label)}</div>
                  {row.note && (
                    <div className="mt-1 flex max-w-md items-start gap-1.5 text-xs text-amber-700">
                      <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
                      {row.note}
                    </div>
                  )}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-zinc-700">{formatPct(row.gross_annual_pct)} a.a.</td>
                <td className="px-4 py-3 text-right tabular-nums text-zinc-700">{formatPct(row.iof_pct, 100)}</td>
                <td className="px-4 py-3 text-right tabular-nums text-zinc-700">{formatPct(row.ir_pct, 100)}</td>
                <td className="px-4 py-3 text-right tabular-nums font-semibold text-zinc-900">{formatBRL(row.net_value_brl)}</td>
                <td className={`px-4 py-3 text-right tabular-nums font-semibold ${isTop ? "text-emerald-700" : "text-zinc-700"}`}>
                  {formatPct(row.net_pct)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
