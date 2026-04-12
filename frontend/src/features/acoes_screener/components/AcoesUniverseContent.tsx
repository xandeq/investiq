"use client";
import { useState, useMemo } from "react";
import Link from "next/link";
import { useAcoesUniverse } from "../hooks/useAcoesUniverse";
import type { AcoesUniverseRow } from "../types";

const PAGE_SIZE = 50;

function fmt(val: string | number | null, decimals = 2, suffix = ""): string {
  if (val === null || val === undefined) return "—";
  const n = typeof val === "string" ? parseFloat(val) : val;
  if (isNaN(n)) return "—";
  return n.toFixed(decimals) + suffix;
}

function fmtBRL(val: number | null): string {
  if (val === null) return "—";
  if (val >= 1_000_000_000) return `R$ ${(val / 1_000_000_000).toFixed(1)}B`;
  if (val >= 1_000_000) return `R$ ${(val / 1_000_000).toFixed(0)}M`;
  return `R$ ${val.toLocaleString("pt-BR")}`;
}

function changeBadge(val: string | null) {
  if (!val) return <span className="text-gray-400">—</span>;
  const n = parseFloat(val);
  if (isNaN(n)) return <span className="text-gray-400">—</span>;
  const color = n >= 0 ? "text-emerald-600" : "text-red-500";
  return (
    <span className={`font-medium ${color}`}>
      {n >= 0 ? "+" : ""}
      {n.toFixed(2)}%
    </span>
  );
}

type SortCol = keyof AcoesUniverseRow;
type McapTier = "" | "small" | "mid" | "large";

function getSortValue(row: AcoesUniverseRow, col: SortCol): number | string | null {
  const val = row[col];
  if (col === "market_cap") return val as number | null;
  if (val === null || val === undefined) return null;
  if (
    col === "regular_market_price" ||
    col === "variacao_12m_pct" ||
    col === "dy" ||
    col === "pl"
  ) {
    const n = parseFloat(val as string);
    return isNaN(n) ? null : n;
  }
  return val as string;
}

export function AcoesUniverseContent() {
  const { data, isLoading, isError, error } = useAcoesUniverse();

  const [sortCol, setSortCol] = useState<SortCol | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [minDy, setMinDy] = useState("");
  const [maxPl, setMaxPl] = useState("");
  const [sectorFilter, setSectorFilter] = useState("");
  const [mcapTier, setMcapTier] = useState<McapTier>("");
  const [page, setPage] = useState(0);

  const sectors = useMemo(() => {
    if (!data?.results) return [];
    const set = new Set(
      data.results.map((r) => r.sector).filter(Boolean) as string[]
    );
    return Array.from(set).sort();
  }, [data]);

  const filtered = useMemo(() => {
    if (!data?.results) return [];

    let rows = data.results.filter((row) => {
      // DY filter: dy stored as decimal (0.09 = 9%), input is in %
      if (minDy) {
        const minDyVal = parseFloat(minDy);
        if (!isNaN(minDyVal) && row.dy !== null) {
          if (parseFloat(row.dy) * 100 < minDyVal) return false;
        } else if (!isNaN(minDyVal) && row.dy === null) {
          return false;
        }
      }

      // P/L max filter
      if (maxPl) {
        const maxPlVal = parseFloat(maxPl);
        if (!isNaN(maxPlVal) && row.pl !== null) {
          if (parseFloat(row.pl) > maxPlVal) return false;
        } else if (!isNaN(maxPlVal) && row.pl === null) {
          return false;
        }
      }

      // Sector filter
      if (sectorFilter && row.sector !== sectorFilter) return false;

      // Market cap tier filter
      if (mcapTier) {
        const mc = row.market_cap;
        if (mc === null) return false;
        if (mcapTier === "small" && mc >= 2_000_000_000) return false;
        if (mcapTier === "mid" && (mc < 2_000_000_000 || mc >= 10_000_000_000))
          return false;
        if (mcapTier === "large" && mc < 10_000_000_000) return false;
      }

      return true;
    });

    // Sort
    if (sortCol) {
      rows = [...rows].sort((a, b) => {
        const aVal = getSortValue(a, sortCol);
        const bVal = getSortValue(b, sortCol);

        // Nulls always go to end
        if (aVal === null && bVal === null) return 0;
        if (aVal === null) return 1;
        if (bVal === null) return -1;

        let cmp: number;
        if (typeof aVal === "number" && typeof bVal === "number") {
          cmp = aVal - bVal;
        } else {
          cmp = String(aVal).localeCompare(String(bVal));
        }
        return sortDir === "asc" ? cmp : -cmp;
      });
    }

    return rows;
  }, [data, minDy, maxPl, sectorFilter, mcapTier, sortCol, sortDir]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const pageRows = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  function toggleSort(col: SortCol) {
    if (sortCol === col) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortCol(col);
      setSortDir("desc");
    }
    setPage(0);
  }

  function SortIndicator({ col }: { col: SortCol }) {
    if (sortCol !== col) return <span className="ml-1 text-gray-300">↕</span>;
    return (
      <span className="ml-1 text-blue-500">
        {sortDir === "asc" ? "↑" : "↓"}
      </span>
    );
  }

  function ThSortable({
    col,
    children,
  }: {
    col: SortCol;
    children: React.ReactNode;
  }) {
    return (
      <th
        className="text-left py-3 px-4 text-xs font-semibold text-gray-600 cursor-pointer select-none hover:text-gray-900 whitespace-nowrap"
        onClick={() => toggleSort(col)}
      >
        {children}
        <SortIndicator col={col} />
      </th>
    );
  }

  function toggleMcap(tier: McapTier) {
    setMcapTier((prev) => (prev === tier ? "" : tier));
    setPage(0);
  }

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="flex flex-wrap gap-4 items-end">
          {/* DY min */}
          <div className="min-w-[120px]">
            <label className="block text-xs font-medium text-gray-600 mb-1">
              DY min (%)
            </label>
            <input
              type="number"
              step="0.5"
              placeholder="Ex: 5"
              value={minDy}
              onChange={(e) => {
                setMinDy(e.target.value);
                setPage(0);
              }}
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            />
          </div>

          {/* P/L max */}
          <div className="min-w-[120px]">
            <label className="block text-xs font-medium text-gray-600 mb-1">
              P/L max
            </label>
            <input
              type="number"
              step="1"
              placeholder="Ex: 20"
              value={maxPl}
              onChange={(e) => {
                setMaxPl(e.target.value);
                setPage(0);
              }}
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            />
          </div>

          {/* Setor dropdown */}
          <div className="min-w-[180px]">
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Setor
            </label>
            <select
              value={sectorFilter}
              onChange={(e) => {
                setSectorFilter(e.target.value);
                setPage(0);
              }}
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            >
              <option value="">Todos os setores</option>
              {sectors.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          {/* Market Cap tier buttons */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Market Cap
            </label>
            <div className="flex gap-1">
              <button
                onClick={() => toggleMcap("small")}
                title="Menos de R$ 2B"
                className={`px-3 py-2 rounded-md text-xs font-medium border transition-colors ${
                  mcapTier === "small"
                    ? "bg-blue-500 text-white border-blue-500"
                    : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
                }`}
              >
                Small &lt;2B
              </button>
              <button
                onClick={() => toggleMcap("mid")}
                title="Entre R$ 2B e R$ 10B"
                className={`px-3 py-2 rounded-md text-xs font-medium border transition-colors ${
                  mcapTier === "mid"
                    ? "bg-blue-500 text-white border-blue-500"
                    : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
                }`}
              >
                Mid 2B–10B
              </button>
              <button
                onClick={() => toggleMcap("large")}
                title="Mais de R$ 10B"
                className={`px-3 py-2 rounded-md text-xs font-medium border transition-colors ${
                  mcapTier === "large"
                    ? "bg-blue-500 text-white border-blue-500"
                    : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
                }`}
              >
                Large &gt;10B
              </button>
            </div>
          </div>

          {/* Clear button */}
          <div>
            <button
              onClick={() => {
                setMinDy("");
                setMaxPl("");
                setSectorFilter("");
                setMcapTier("");
                setPage(0);
              }}
              className="px-4 py-2 rounded-md text-sm text-gray-600 border border-gray-200 hover:bg-gray-50 transition-colors"
            >
              Limpar
            </button>
          </div>
        </div>
      </div>

      {/* Status bar */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>
          {isLoading
            ? "Carregando..."
            : `${filtered.length} ações encontradas`}
        </span>
        {data?.disclaimer && (
          <span className="text-gray-400 italic truncate max-w-xs">
            {data.disclaimer}
          </span>
        )}
      </div>

      {/* Error */}
      {isError && (
        <div className="rounded-lg bg-red-50 border border-red-100 px-4 py-3 text-sm text-red-600">
          {error instanceof Error ? error.message : "Erro ao carregar dados"}
        </div>
      )}

      {/* Table */}
      {!isError && (
        <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <ThSortable col="ticker">Ticker</ThSortable>
                  <ThSortable col="sector">Setor</ThSortable>
                  <ThSortable col="regular_market_price">Preço</ThSortable>
                  <ThSortable col="variacao_12m_pct">Var. 12m%</ThSortable>
                  <ThSortable col="dy">DY 12m</ThSortable>
                  <ThSortable col="pl">P/L</ThSortable>
                  <ThSortable col="market_cap">Market Cap</ThSortable>
                </tr>
              </thead>
              <tbody>
                {isLoading
                  ? Array.from({ length: 8 }).map((_, i) => (
                      <tr key={i} className="border-b border-gray-100">
                        {Array.from({ length: 7 }).map((_, j) => (
                          <td key={j} className="py-3 px-4">
                            <div className="h-4 bg-gray-100 rounded animate-pulse" />
                          </td>
                        ))}
                      </tr>
                    ))
                  : pageRows.map((row) => (
                      <tr
                        key={row.ticker}
                        className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                      >
                        {/* Ticker */}
                        <td className="py-3 px-4">
                          <Link
                            href={`/stock/${row.ticker}`}
                            className="font-mono font-bold text-sm text-blue-600 hover:underline"
                          >
                            {row.ticker}
                          </Link>
                          {row.short_name && (
                            <div className="text-xs text-gray-500 truncate max-w-[140px]">
                              {row.short_name}
                            </div>
                          )}
                        </td>

                        {/* Setor */}
                        <td className="py-3 px-4 text-xs text-gray-600">
                          {row.sector ?? "—"}
                        </td>

                        {/* Preco */}
                        <td className="py-3 px-4 text-sm font-semibold">
                          {row.regular_market_price
                            ? `R$ ${fmt(row.regular_market_price, 2)}`
                            : "—"}
                        </td>

                        {/* Var. 12m% — dy stored as decimal, multiply by 100 */}
                        <td className="py-3 px-4">
                          {changeBadge(
                            row.variacao_12m_pct
                              ? String(parseFloat(row.variacao_12m_pct) * 100)
                              : null
                          )}
                        </td>

                        {/* DY 12m — stored as decimal, show as % */}
                        <td className="py-3 px-4 text-sm">
                          {row.dy !== null
                            ? fmt(parseFloat(row.dy) * 100, 2, "%")
                            : "—"}
                        </td>

                        {/* P/L */}
                        <td className="py-3 px-4 text-sm">
                          {fmt(row.pl, 1)}
                        </td>

                        {/* Market Cap */}
                        <td className="py-3 px-4 text-sm">
                          {fmtBRL(row.market_cap)}
                        </td>
                      </tr>
                    ))}

                {!isLoading && filtered.length === 0 && (
                  <tr>
                    <td
                      colSpan={7}
                      className="py-12 text-center text-sm text-gray-500"
                    >
                      Nenhum ativo encontrado com os filtros aplicados
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-4 py-3 border-t border-gray-100 flex items-center justify-between">
              <span className="text-xs text-gray-500">
                Página {page + 1} de {totalPages}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="px-3 py-1.5 rounded text-xs border border-gray-200 disabled:opacity-40 hover:bg-gray-50 transition-colors"
                >
                  Anterior
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1}
                  className="px-3 py-1.5 rounded text-xs border border-gray-200 disabled:opacity-40 hover:bg-gray-50 transition-colors"
                >
                  Próxima
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      <p className="text-xs text-gray-400 text-center">
        Dados atualizados diariamente via snapshot B3. Fonte: brapi.dev
      </p>
    </div>
  );
}
