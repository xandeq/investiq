"use client";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Building2 } from "lucide-react";

interface FundPosition {
  cnpj: string;
  name: string;
  quantity: string;
  cmp: string;
  total_cost: string;
  current_nav: string | null;
  nav_stale: boolean;
  unrealized_pnl: string | null;
  unrealized_pnl_pct: string | null;
  quote_date: string | null;
}

function fmtBrl(v: string | number | null) {
  if (v === null || v === undefined) return "—";
  const n = typeof v === "string" ? parseFloat(v) : v;
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(n);
}

function fmtPct(v: string | null) {
  if (!v) return null;
  const n = parseFloat(v);
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

function pnlColor(v: string | null) {
  if (!v) return "text-gray-500";
  return parseFloat(v) >= 0 ? "text-emerald-600" : "text-red-600";
}

function formatCnpj(digits: string) {
  const d = digits.padStart(14, "0");
  return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5,8)}/${d.slice(8,12)}-${d.slice(12,14)}`;
}

export function FundPositionsCard() {
  const { data: positions, isLoading } = useQuery({
    queryKey: ["funds", "positions"],
    queryFn: () => apiClient<FundPosition[]>("/funds/positions"),
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) return <div className="h-32 rounded-xl bg-gray-100 animate-pulse" />;
  if (!positions || positions.length === 0) return null;

  const totalCost = positions.reduce((s, p) => s + parseFloat(p.total_cost), 0);
  const totalNav = positions.reduce((s, p) => s + (p.current_nav ? parseFloat(p.current_nav) * parseFloat(p.quantity) : parseFloat(p.total_cost)), 0);
  const totalPnl = totalNav - totalCost;

  return (
    <div className="rounded-xl border bg-white p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Building2 className="h-4 w-4 text-indigo-500" />
          <p className="text-xs font-bold uppercase tracking-wider text-gray-500">Fundos de Investimento</p>
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span>Total investido: <span className="font-semibold text-gray-800">{fmtBrl(totalCost)}</span></span>
          {totalPnl !== 0 && (
            <span className={`font-semibold ${totalPnl >= 0 ? "text-emerald-600" : "text-red-600"}`}>
              {totalPnl >= 0 ? "+" : ""}{fmtBrl(totalPnl)}
            </span>
          )}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-[11px] uppercase text-gray-400 font-semibold">
              <th className="text-left py-1.5">Fundo</th>
              <th className="text-right py-1.5">Cotas</th>
              <th className="text-right py-1.5">CMC</th>
              <th className="text-right py-1.5">Cota Atual</th>
              <th className="text-right py-1.5">Total</th>
              <th className="text-right py-1.5">P&L</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {positions.map((p) => {
              const currentValue = p.current_nav
                ? parseFloat(p.current_nav) * parseFloat(p.quantity)
                : null;
              return (
                <tr key={p.cnpj} className="hover:bg-gray-50/50">
                  <td className="py-2">
                    <p className="font-medium text-gray-800 text-xs leading-tight max-w-[200px] truncate" title={p.name}>
                      {p.name}
                    </p>
                    <p className="text-[10px] text-gray-400">{formatCnpj(p.cnpj)}</p>
                  </td>
                  <td className="text-right text-gray-600 py-2 text-xs">
                    {parseFloat(p.quantity).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                  </td>
                  <td className="text-right text-gray-600 py-2 text-xs">
                    {fmtBrl(p.cmp)}
                  </td>
                  <td className="text-right py-2 text-xs">
                    {p.nav_stale ? (
                      <span className="text-gray-400 italic">—</span>
                    ) : (
                      <>
                        <span className="font-medium">{fmtBrl(p.current_nav)}</span>
                        {p.quote_date && (
                          <span className="block text-[10px] text-gray-400">
                            {new Date(p.quote_date + "T00:00:00").toLocaleDateString("pt-BR")}
                          </span>
                        )}
                      </>
                    )}
                  </td>
                  <td className="text-right py-2 text-xs font-medium">
                    {currentValue !== null ? fmtBrl(currentValue) : fmtBrl(p.total_cost)}
                  </td>
                  <td className="text-right py-2 text-xs">
                    {p.unrealized_pnl !== null ? (
                      <span className={`font-semibold ${pnlColor(p.unrealized_pnl)}`}>
                        {fmtPct(p.unrealized_pnl_pct)}
                        <span className="block text-[10px]">{fmtBrl(p.unrealized_pnl)}</span>
                      </span>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {positions.some((p) => p.nav_stale) && (
        <p className="text-[11px] text-amber-600 bg-amber-50 rounded px-3 py-1.5">
          Cotações atualizadas diariamente às 19h via CVM. Primeira atualização pode levar até 24h.
        </p>
      )}
    </div>
  );
}
