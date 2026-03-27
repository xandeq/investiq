"use client";
import { useState, useMemo } from "react";
import { useDividends } from "@/features/portfolio/hooks/useDividends";
import { formatBRL, formatDate } from "@/lib/formatters";
import { Skeleton } from "@/components/ui/skeleton";

const TX_TYPE_LABELS: Record<string, string> = {
  dividend: "Dividendo", jscp: "JSCP", amortization: "Amortização",
};
const ASSET_CLASS_LABELS: Record<string, string> = {
  acao: "Ações", fii: "FIIs", renda_fixa: "Renda Fixa", bdr: "BDRs", etf: "ETFs",
};

export function DividendHistory() {
  const { data: dividends, isLoading } = useDividends();
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

  if (isLoading) return <Skeleton className="h-48 w-full rounded-xl" />;

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
          <span className="ml-auto text-sm font-medium text-green-600">
            Total filtrado: {formatBRL(totalFiltered)}
          </span>
        )}
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          {dividends?.length === 0
            ? "Nenhum provento registrado"
            : "Nenhum resultado para os filtros selecionados"}
        </p>
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
                <tr key={d.id} className="border-b last:border-0 hover:bg-muted/30">
                  <td className="py-2 pr-4 font-medium">{d.ticker}</td>
                  <td className="py-2 pr-4 text-muted-foreground">
                    {TX_TYPE_LABELS[d.transaction_type] ?? d.transaction_type}
                  </td>
                  <td className="py-2 pr-4 text-muted-foreground text-xs">
                    {ASSET_CLASS_LABELS[d.asset_class] ?? d.asset_class}
                  </td>
                  <td className="py-2 pr-4 text-right">
                    {parseFloat(d.quantity).toLocaleString("pt-BR")}
                  </td>
                  <td className="py-2 pr-4 text-right">{formatBRL(d.unit_price)}</td>
                  <td className="py-2 pr-4 text-right font-medium text-green-600">
                    {formatBRL(d.total_value)}
                  </td>
                  <td className="py-2 pr-4 text-right text-muted-foreground">
                    {formatDate(d.transaction_date)}
                  </td>
                  <td className="py-2 text-right">
                    {d.is_exempt ? (
                      <span className="text-xs text-green-600">Sim</span>
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
