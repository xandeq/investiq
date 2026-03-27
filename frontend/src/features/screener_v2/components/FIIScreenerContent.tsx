"use client";
import { useState } from "react";
import { useFIIScreener } from "../hooks/useFIIScreener";
import type { FIIRow, FIIScreenerParams } from "../types";

const SEGMENTOS = ["Tijolo", "Papel", "Híbrido", "FoF", "Agro"];
const PAGE_SIZE = 50;

function fmt(val: string | null, decimals = 2, suffix = ""): string {
  if (val === null || val === undefined) return "—";
  const n = parseFloat(val);
  if (isNaN(n)) return "—";
  return n.toFixed(decimals) + suffix;
}

function segmentoBadge(seg: string | null) {
  if (!seg) return <span className="text-gray-400">—</span>;
  const colors: Record<string, string> = {
    Tijolo: "bg-orange-100 text-orange-700",
    Papel: "bg-blue-100 text-blue-700",
    Híbrido: "bg-purple-100 text-purple-700",
    FoF: "bg-teal-100 text-teal-700",
    Agro: "bg-green-100 text-green-700",
  };
  const cls = colors[seg] ?? "bg-gray-100 text-gray-600";
  return <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>{seg}</span>;
}

function changeBadge(val: string | null) {
  if (!val) return <span className="text-gray-400">—</span>;
  const n = parseFloat(val);
  if (isNaN(n)) return <span className="text-gray-400">—</span>;
  const color = n >= 0 ? "text-emerald-600" : "text-red-500";
  return <span className={`font-medium ${color}`}>{n >= 0 ? "+" : ""}{n.toFixed(2)}%</span>;
}

function FIITableRow({ row }: { row: FIIRow }) {
  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
      <td className="py-3 px-4">
        <div className="font-mono font-bold text-sm">{row.ticker}</div>
        <div className="text-xs text-gray-500 truncate max-w-[140px]">{row.short_name ?? "—"}</div>
      </td>
      <td className="py-3 px-4">{segmentoBadge(row.segmento)}</td>
      <td className="py-3 px-4 text-sm font-semibold">
        {row.price ? `R$ ${parseFloat(row.price).toFixed(2)}` : "—"}
      </td>
      <td className="py-3 px-4">{changeBadge(row.change_pct)}</td>
      <td className="py-3 px-4 text-sm">{fmt(row.dy, 2, "%")}</td>
      <td className="py-3 px-4 text-sm">{fmt(row.pvp)}</td>
      <td className="py-3 px-4 text-sm">
        {row.vacancia_financeira ? `${fmt(row.vacancia_financeira)}%` : "—"}
      </td>
      <td className="py-3 px-4 text-sm">
        {row.num_cotistas ? row.num_cotistas.toLocaleString("pt-BR") : "—"}
      </td>
    </tr>
  );
}

export function FIIScreenerContent() {
  const [filters, setFilters] = useState<FIIScreenerParams>({});
  const [applied, setApplied] = useState<FIIScreenerParams>({});
  const [offset, setOffset] = useState(0);
  const [excludePortfolio, setExcludePortfolio] = useState(false);

  const params: FIIScreenerParams = { ...applied, limit: PAGE_SIZE, offset, exclude_portfolio: excludePortfolio };
  const { data, isLoading, isFetching, error } = useFIIScreener(params);

  function applyFilters() {
    setOffset(0);
    setApplied({ ...filters });
  }

  function clearFilters() {
    setFilters({});
    setApplied({});
    setOffset(0);
  }

  const total = data?.total ?? 0;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">DY mín (%)</label>
            <input
              type="number"
              step="0.1"
              placeholder="Ex: 7"
              value={filters.min_dy ?? ""}
              onChange={(e) => setFilters((f) => ({ ...f, min_dy: e.target.value ? +e.target.value : undefined }))}
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">P/VP máx</label>
            <input
              type="number"
              step="0.01"
              placeholder="Ex: 1.1"
              value={filters.max_pvp ?? ""}
              onChange={(e) => setFilters((f) => ({ ...f, max_pvp: e.target.value ? +e.target.value : undefined }))}
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Segmento</label>
            <select
              value={filters.segmento ?? ""}
              onChange={(e) => setFilters((f) => ({ ...f, segmento: e.target.value || undefined }))}
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            >
              <option value="">Todos</option>
              {SEGMENTOS.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Vacância máx (%)</label>
            <input
              type="number"
              step="0.1"
              placeholder="Ex: 10"
              value={filters.max_vacancia ?? ""}
              onChange={(e) => setFilters((f) => ({ ...f, max_vacancia: e.target.value ? +e.target.value : undefined }))}
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Cotistas mín</label>
            <input
              type="number"
              placeholder="Ex: 50000"
              value={filters.min_cotistas ?? ""}
              onChange={(e) => setFilters((f) => ({ ...f, min_cotistas: e.target.value ? +e.target.value : undefined }))}
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            />
          </div>
        </div>

        <div className="mt-3 flex items-center justify-between flex-wrap gap-3">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={excludePortfolio}
              onChange={(e) => { setExcludePortfolio(e.target.checked); setOffset(0); }}
              className="rounded"
            />
            <span className="text-gray-700">Apenas FIIs que não tenho na carteira</span>
          </label>
          <div className="flex gap-2">
            <button
              onClick={clearFilters}
              className="px-4 py-2 rounded-md text-sm text-gray-600 border border-gray-200 hover:bg-gray-50 transition-colors"
            >
              Limpar
            </button>
            <button
              onClick={applyFilters}
              className="px-4 py-2 rounded-md text-sm bg-blue-500 text-white hover:bg-blue-600 transition-colors font-medium"
            >
              Filtrar
            </button>
          </div>
        </div>
      </div>

      {/* Context about P/VP by segment */}
      <div className="rounded-md bg-blue-50 border border-blue-100 px-4 py-2 text-xs text-blue-700">
        <strong>Contexto P/VP por segmento:</strong> Tijolo (ref. ~1.0), Papel (ref. ~0.95–1.05), FoF (ref. ~0.90–1.0), Agro (ref. ~1.0–1.1)
      </div>

      {/* Status bar */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>
          {isLoading ? "Carregando..." : `${total.toLocaleString("pt-BR")} FIIs encontrados`}
          {isFetching && !isLoading && " · atualizando..."}
        </span>
        {data?.disclaimer && (
          <span className="text-gray-400 italic">{data.disclaimer}</span>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-100 px-4 py-3 text-sm text-red-600">
          {error instanceof Error ? error.message : "Erro ao carregar dados"}
        </div>
      )}

      {/* Table */}
      {!error && (
        <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">FII</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">Segmento</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">Preço</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">Var.</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">DY</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">P/VP</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">Vacância</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">Cotistas</th>
                </tr>
              </thead>
              <tbody>
                {isLoading
                  ? Array.from({ length: 8 }).map((_, i) => (
                      <tr key={i} className="border-b border-gray-100">
                        {Array.from({ length: 8 }).map((_, j) => (
                          <td key={j} className="py-3 px-4">
                            <div className="h-4 bg-gray-100 rounded animate-pulse" />
                          </td>
                        ))}
                      </tr>
                    ))
                  : data?.results.map((row) => (
                      <FIITableRow key={`${row.ticker}`} row={row} />
                    ))}
                {!isLoading && data?.results.length === 0 && (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-sm text-gray-500">
                      Nenhum FII encontrado com os filtros aplicados
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
                Página {currentPage} de {totalPages}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                  disabled={offset === 0}
                  className="px-3 py-1.5 rounded text-xs border border-gray-200 disabled:opacity-40 hover:bg-gray-50 transition-colors"
                >
                  Anterior
                </button>
                <button
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                  disabled={currentPage >= totalPages}
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
        Dados atualizados via snapshot diário (brapi.dev) + metadados CVM (semanal)
      </p>
    </div>
  );
}
