"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

interface DividendRankingItem {
  ticker: string;
  dy_pct: string;
  position_value: string;
  estimated_annual: string;
  sector: string | null;
}

interface DividendRankingResponse {
  items: DividendRankingItem[];
  total_estimated_annual: string;
  data_available: boolean;
}

function fmt(val: string) {
  return parseFloat(val).toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

export function DividendRankingCard() {
  const { data, isLoading } = useQuery<DividendRankingResponse>({
    queryKey: ["dividend-ranking"],
    queryFn: () => apiClient<DividendRankingResponse>("/dashboard/dividend-ranking"),
    staleTime: 15 * 60 * 1000,
  });

  if (isLoading) return null;
  if (!data?.data_available) return null;

  const top = data.items.slice(0, 8);
  const total = parseFloat(data.total_estimated_annual);

  return (
    <div className="bg-white rounded-2xl border p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-800">Ranking de Dividendos</h3>
        <span className="text-xs text-gray-400">Renda anual estimada</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-400 border-b">
              <th className="pb-2 font-medium">Ativo</th>
              <th className="pb-2 font-medium text-right">DY</th>
              <th className="pb-2 font-medium text-right hidden sm:table-cell">Posição</th>
              <th className="pb-2 font-medium text-right">Renda/ano</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {top.map((item) => {
              const dy = parseFloat(item.dy_pct);
              const dyColor =
                dy >= 10 ? "text-emerald-700 font-semibold" :
                dy >= 6  ? "text-emerald-600" :
                "text-gray-600";

              return (
                <tr key={item.ticker} className="hover:bg-gray-50 transition-colors">
                  <td className="py-2">
                    <span className="font-mono font-medium text-gray-900">{item.ticker}</span>
                    {item.sector && (
                      <span className="ml-2 text-xs text-gray-400 hidden sm:inline">{item.sector}</span>
                    )}
                  </td>
                  <td className={`py-2 text-right font-mono ${dyColor}`}>
                    {dy.toFixed(1)}%
                  </td>
                  <td className="py-2 text-right text-gray-500 hidden sm:table-cell">
                    {fmt(item.position_value)}
                  </td>
                  <td className="py-2 text-right text-gray-800">
                    {fmt(item.estimated_annual)}
                  </td>
                </tr>
              );
            })}
          </tbody>
          {total > 0 && (
            <tfoot>
              <tr className="border-t border-gray-200">
                <td colSpan={2} className="pt-2 text-xs text-gray-400">
                  Total estimado (carteira)
                </td>
                <td className="pt-2 text-right font-semibold text-gray-900 hidden sm:table-cell" />
                <td className="pt-2 text-right font-semibold text-emerald-700">
                  {fmt(data.total_estimated_annual)}
                </td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </div>
  );
}
