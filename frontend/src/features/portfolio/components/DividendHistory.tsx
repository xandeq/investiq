"use client";
import { useState, useMemo } from "react";
import { useDividends } from "@/features/portfolio/hooks/useDividends";
import { formatBRL, formatDate } from "@/lib/formatters";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

const TX_TYPE_LABELS: Record<string, string> = {
  dividend: "Dividendo", jscp: "JSCP", amortization: "Amortização",
};
const ASSET_CLASS_LABELS: Record<string, string> = {
  acao: "Ações", fii: "FIIs", renda_fixa: "Renda Fixa", bdr: "BDRs", etf: "ETFs",
  crypto: "Crypto", fundo: "Fundos",
};

export function DividendHistory() {
  const { data: dividends, isLoading, isError, refetch } = useDividends();
  const [yearFilter, setYearFilter] = useState<string>("all");
  const [classFilter, setClassFilter] = useState<string>("all");

  const availableYears = useMemo(() => {
    if (!dividends) return [];
    const years = [...new Set(dividends.map((d) => d.transaction_date.slice(0, 4)))].sort().reverse();
    return years;
  }, [dividends]);

  const availableClasses = useMemo(() => {
    if (!dividends) return [];
    return [...new Set(dividends.map((d) => d.asset_class))];
  }, [dividends]);

  const filtered = useMemo(() => {
    if (!dividends) return [];
    return dividends.filter((d) => {
      const year = d.transaction_date.slice(0, 4);
      return (
        (yearFilter === "all" || year === yearFilter) &&
        (classFilter === "all" || d.asset_class === classFilter)
      );
    });
  }, [dividends, yearFilter, classFilter]);

  const totalFiltered = useMemo(
    () => filtered.reduce((sum, d) => sum + parseFloat(d.total_value), 0),
    [filtered]
  );

  if (isLoading) return <ShimmerSkeleton className="h-48 w-full rounded-xl" />;

  if (isError) {
    return (
      <div className="rounded-xl border bg-card p-6 flex items-center justify-between gap-2">
        <p className="text-sm text-zinc-400">Erro ao carregar histórico de dividendos.</p>
        <button
          onClick={() => refetch()}
          className="text-xs text-zinc-500 hover:text-blue-600 active:scale-[0.97] transition-all duration-150 underline underline-offset-2"
        >
          Tentar novamente
        </button>
      </div>
    );
  }

  return (
    <div className="rounded-xl border bg-card p-6">
      <h3 className="text-sm font-medium mb-4">Dividendos e Proventos</h3>

      <div className="flex flex-wrap gap-3 mb-4">
        <select
          value={yearFilter}
          onChange={(e) => setYearFilter(e.target.value)}
          className="rounded border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="all">Todos os anos</option>
          {availableYears.map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
        <select
          value={classFilter}
          onChange={(e) => setClassFilter(e.target.value)}
          className="rounded border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="all">Todas as classes</option>
          {availableClasses.map((c) => (
            <option key={c} value={c}>{ASSET_CLASS_LABELS[c] ?? c}</option>
          ))}
        </select>
        {filtered.length > 0 && (
          <span className="ml-auto text-sm font-medium text-emerald-600">
            Total filtrado: {formatBRL(totalFiltered)}
          </span>
        )}
      </div>

      {filtered.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-8 text-center">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-50 border border-zinc-200">
              <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden>
                <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke="#A1A1AA" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div>
              <p className="text-sm font-medium text-zinc-700">
                {dividends?.length === 0 ? "Nenhum provento registrado" : "Nenhum resultado"}
              </p>
              <p className="text-xs text-zinc-400 mt-0.5">
                {dividends?.length === 0
                  ? "Os proventos aparecerão aqui quando forem registrados."
                  : "Tente ajustar os filtros de ano ou classe."}
              </p>
            </div>
          </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-muted-foreground text-xs">
                <th className="text-left py-2 pr-4">Ativo</th>
                <th className="text-left py-2 pr-4">Tipo</th>
                <th className="text-left py-2 pr-4">Classe</th>
                <th className="text-right py-2 pr-4">Qtd</th>
                <th className="text-right py-2 pr-4">Valor Unit.</th>
                <th className="text-right py-2 pr-4">Total</th>
                <th className="text-right py-2 pr-4">Data</th>
                <th className="text-right py-2">Isento IR</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((d) => (
                <tr key={d.id} className="border-b border-zinc-100 last:border-0 hover:bg-zinc-50 transition-colors">
                  <td className="py-2 pr-4 font-medium">{d.ticker}</td>
                  <td className="py-2 pr-4 text-muted-foreground">
                    {TX_TYPE_LABELS[d.transaction_type] ?? d.transaction_type}
                  </td>
                  <td className="py-2 pr-4 text-muted-foreground text-xs">
                    {ASSET_CLASS_LABELS[d.asset_class] ?? d.asset_class}
                  </td>
                  <td className="py-2 pr-4 text-right tabular-nums">
                    {parseFloat(d.quantity).toLocaleString("pt-BR")}
                  </td>
                  <td className="py-2 pr-4 text-right tabular-nums">{formatBRL(d.unit_price)}</td>
                  <td className="py-2 pr-4 text-right tabular-nums font-medium text-emerald-600">
                    {formatBRL(d.total_value)}
                  </td>
                  <td className="py-2 pr-4 text-right tabular-nums text-muted-foreground">
                    {formatDate(d.transaction_date)}
                  </td>
                  <td className="py-2 text-right tabular-nums">
                    {d.is_exempt ? (
                      <span className="text-xs text-emerald-600">Sim</span>
                    ) : (
                      <span className="text-xs text-muted-foreground">Não</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
