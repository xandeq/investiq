"use client";
import { useState } from "react";
import Link from "next/link";
import { Eye, EyeSlash, DownloadSimple } from "@phosphor-icons/react";
import { useAcoesScreener } from "../hooks/useAcoesScreener";
import { exportAcoesScreenerCSV } from "../api";
import type { AcaoRow, AcaoScreenerParams } from "../types";
import { useSortedData } from "@/hooks/useSort";
import { SortableHeader } from "@/components/ui/SortableHeader";
import { useWatchlist, useAddToWatchlist, useRemoveFromWatchlist } from "@/features/watchlist/hooks/useWatchlist";

const SECTORS = [
  "Financeiro", "Energia", "Tecnologia", "Consumo", "Saúde",
  "Utilidades", "Materiais", "Indústria", "Comunicação", "Imobiliário",
];

const PAGE_SIZE = 50;

function fmt(val: string | null, decimals = 2, suffix = ""): string {
  if (val === null || val === undefined) return "—";
  const n = parseFloat(val);
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
  if (!val) return <span className="text-zinc-400">—</span>;
  const n = parseFloat(val);
  if (isNaN(n)) return <span className="text-zinc-400">—</span>;
  const color = n >= 0 ? "text-emerald-600" : "text-red-500";
  return <span className={`font-medium ${color}`}>{n >= 0 ? "+" : ""}{n.toFixed(2)}%</span>;
}

function WatchlistButton({ ticker, inWatchlist }: { ticker: string; inWatchlist: boolean }) {
  const addMut = useAddToWatchlist();
  const removeMut = useRemoveFromWatchlist();
  const pending = addMut.isPending || removeMut.isPending;

  return (
    <button
      disabled={pending}
      onClick={(e) => {
        e.stopPropagation();
        if (inWatchlist) removeMut.mutate(ticker);
        else addMut.mutate({ ticker });
      }}
      title={inWatchlist ? "Remover da watchlist" : "Adicionar à watchlist"}
      className={`p-1.5 rounded-md transition-colors disabled:opacity-50 ${
        inWatchlist
          ? "text-blue-500 hover:bg-blue-50"
          : "text-zinc-300 hover:text-blue-400 hover:bg-blue-50"
      }`}
    >
      {inWatchlist ? <Eye size={14} weight="fill" /> : <EyeSlash size={14} />}
    </button>
  );
}

function AcaoTableRow({ row, watchlistTickers }: { row: AcaoRow; watchlistTickers: Set<string> }) {
  const inWatchlist = watchlistTickers.has(row.ticker);
  return (
    <tr className="border-b border-zinc-100 hover:bg-zinc-50 transition-colors">
      <td className="py-3 px-4">
        <Link href={`/stock/${row.ticker}`} className="group">
          <div className="font-mono font-bold text-sm group-hover:text-blue-600 transition-colors">{row.ticker}</div>
          <div className="text-xs text-zinc-500 truncate max-w-[140px]">{row.short_name ?? "—"}</div>
        </Link>
      </td>
      <td className="py-3 px-4 text-xs text-zinc-600">{row.sector ?? "—"}</td>
      <td className="py-3 px-4 text-sm font-semibold">
        {row.price ? `R$ ${parseFloat(row.price).toFixed(2)}` : "—"}
      </td>
      <td className="py-3 px-4">{changeBadge(row.change_pct)}</td>
      <td className="py-3 px-4 text-sm">{fmt(row.dy, 2, "%")}</td>
      <td className="py-3 px-4 text-sm">{fmt(row.pl)}</td>
      <td className="py-3 px-4 text-sm">{fmt(row.pvp)}</td>
      <td className="py-3 px-4 text-sm">{fmt(row.ev_ebitda)}</td>
      <td className="py-3 px-4 text-xs text-zinc-500">{fmtBRL(row.market_cap)}</td>
      <td className="py-3 px-2">
        <WatchlistButton ticker={row.ticker} inWatchlist={inWatchlist} />
      </td>
    </tr>
  );
}

export function AcoesScreenerContent() {
  const [filters, setFilters] = useState<AcaoScreenerParams>({});
  const [applied, setApplied] = useState<AcaoScreenerParams>({});
  const [offset, setOffset] = useState(0);
  const [excludePortfolio, setExcludePortfolio] = useState(false);
  const [exporting, setExporting] = useState(false);

  const params: AcaoScreenerParams = { ...applied, limit: PAGE_SIZE, offset, exclude_portfolio: excludePortfolio };
  const { data, isLoading, isFetching, error } = useAcoesScreener(params);
  const { sorted: sortedAcoes, col, dir, toggle } = useSortedData(
    data?.results ?? [],
  );
  const { data: watchlistItems = [] } = useWatchlist();
  const watchlistTickers = new Set(watchlistItems.map((w: { ticker: string }) => w.ticker));

  function applyFilters() {
    setOffset(0);
    setApplied({ ...filters });
  }

  function clearFilters() {
    setFilters({});
    setApplied({});
    setOffset(0);
  }

  async function handleExport() {
    setExporting(true);
    try {
      const blob = await exportAcoesScreenerCSV({ ...applied, exclude_portfolio: excludePortfolio });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `acoes-screener-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // silent — don't break the UI for a failed export
    } finally {
      setExporting(false);
    }
  }

  function applyPreset(preset: AcaoScreenerParams) {
    setFilters(preset);
    setApplied(preset);
    setOffset(0);
  }

  const PRESETS: { label: string; filters: AcaoScreenerParams }[] = [
    { label: "Dividendos", filters: { min_dy: 8, max_pl: 20 } },
    { label: "Value", filters: { max_pvp: 2, max_pl: 15 } },
    { label: "Growth", filters: { max_ev_ebitda: 10, max_pl: 25 } },
  ];

  const total = data?.total ?? 0;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="rounded-lg border border-zinc-200 bg-white p-4">
        {/* Preset chips */}
        <div className="flex gap-2 flex-wrap mb-3">
          <span className="text-xs text-zinc-400 self-center">Filtros rápidos:</span>
          {PRESETS.map((p) => (
            <button
              key={p.label}
              onClick={() => applyPreset(p.filters)}
              className="px-2.5 py-1 text-xs rounded-full border border-zinc-200 text-zinc-600 hover:border-blue-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs font-medium text-zinc-600 mb-1">DY mín (%)</label>
            <input
              type="number"
              step="0.1"
              placeholder="Ex: 5"
              value={filters.min_dy ?? ""}
              onChange={(e) => setFilters((f) => ({ ...f, min_dy: e.target.value ? +e.target.value : undefined }))}
              className="w-full rounded-md border border-zinc-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-600 mb-1">P/L máx</label>
            <input
              type="number"
              step="0.1"
              placeholder="Ex: 15"
              value={filters.max_pl ?? ""}
              onChange={(e) => setFilters((f) => ({ ...f, max_pl: e.target.value ? +e.target.value : undefined }))}
              className="w-full rounded-md border border-zinc-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-600 mb-1">P/VP máx</label>
            <input
              type="number"
              step="0.1"
              placeholder="Ex: 2"
              value={filters.max_pvp ?? ""}
              onChange={(e) => setFilters((f) => ({ ...f, max_pvp: e.target.value ? +e.target.value : undefined }))}
              className="w-full rounded-md border border-zinc-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-600 mb-1">EV/EBITDA máx</label>
            <input
              type="number"
              step="0.1"
              placeholder="Ex: 10"
              value={filters.max_ev_ebitda ?? ""}
              onChange={(e) => setFilters((f) => ({ ...f, max_ev_ebitda: e.target.value ? +e.target.value : undefined }))}
              className="w-full rounded-md border border-zinc-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-600 mb-1">Setor</label>
            <select
              value={filters.sector ?? ""}
              onChange={(e) => setFilters((f) => ({ ...f, sector: e.target.value || undefined }))}
              className="w-full rounded-md border border-zinc-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            >
              <option value="">Todos</option>
              {SECTORS.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-600 mb-1">Market cap mín (R$)</label>
            <input
              type="number"
              placeholder="Ex: 1000000000"
              value={filters.min_market_cap ?? ""}
              onChange={(e) => setFilters((f) => ({ ...f, min_market_cap: e.target.value ? +e.target.value : undefined }))}
              className="w-full rounded-md border border-zinc-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
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
            <span className="text-zinc-700">Apenas ativos que não tenho na carteira</span>
          </label>
          <div className="flex gap-2">
            <button
              onClick={clearFilters}
              className="px-4 py-2 rounded-md text-sm text-zinc-600 border border-zinc-200 hover:bg-zinc-50 transition-colors"
            >
              Limpar
            </button>
            <button
              onClick={handleExport}
              disabled={exporting || isLoading}
              title="Exportar resultados filtrados como CSV"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md text-sm text-zinc-600 border border-zinc-200 hover:bg-zinc-50 transition-colors disabled:opacity-50"
            >
              <DownloadSimple size={14} weight="bold" aria-hidden />
              {exporting ? "Exportando..." : "Exportar CSV"}
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

      {/* Status bar */}
      <div className="flex items-center justify-between text-xs text-zinc-500">
        <span>
          {isLoading ? "Carregando..." : `${total.toLocaleString("pt-BR")} ações encontradas`}
          {isFetching && !isLoading && " · atualizando..."}
        </span>
        {data?.disclaimer && (
          <span className="text-zinc-400 italic">{data.disclaimer}</span>
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
        <div className="rounded-lg border border-zinc-200 bg-white overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-zinc-50 border-b border-zinc-200">
                  <SortableHeader col="ticker" label="Ativo" activeCol={col} dir={dir} onSort={toggle} className="text-left py-3 px-4 text-xs font-semibold text-zinc-600" />
                  <SortableHeader col="sector" label="Setor" activeCol={col} dir={dir} onSort={toggle} className="text-left py-3 px-4 text-xs font-semibold text-zinc-600" />
                  <SortableHeader col="price" label="Preço" activeCol={col} dir={dir} onSort={toggle} className="text-left py-3 px-4 text-xs font-semibold text-zinc-600" />
                  <SortableHeader col="change_pct" label="Var." activeCol={col} dir={dir} onSort={toggle} className="text-left py-3 px-4 text-xs font-semibold text-zinc-600" />
                  <SortableHeader col="dy" label="DY" activeCol={col} dir={dir} onSort={toggle} className="text-left py-3 px-4 text-xs font-semibold text-zinc-600" />
                  <SortableHeader col="pl" label="P/L" activeCol={col} dir={dir} onSort={toggle} className="text-left py-3 px-4 text-xs font-semibold text-zinc-600" />
                  <SortableHeader col="pvp" label="P/VP" activeCol={col} dir={dir} onSort={toggle} className="text-left py-3 px-4 text-xs font-semibold text-zinc-600" />
                  <SortableHeader col="ev_ebitda" label="EV/EBITDA" activeCol={col} dir={dir} onSort={toggle} className="text-left py-3 px-4 text-xs font-semibold text-zinc-600" />
                  <SortableHeader col="market_cap" label="Market Cap" activeCol={col} dir={dir} onSort={toggle} className="text-left py-3 px-4 text-xs font-semibold text-zinc-600" />
                  <th className="py-3 px-2 text-xs font-semibold text-zinc-600" />
                </tr>
              </thead>
              <tbody>
                {isLoading
                  ? Array.from({ length: 8 }).map((_, i) => (
                      <tr key={i} className="border-b border-zinc-100">
                        {Array.from({ length: 10 }).map((_, j) => (
                          <td key={j} className="py-3 px-4">
                            <div className="h-4 bg-zinc-100 rounded" />
                          </td>
                        ))}
                      </tr>
                    ))
                  : sortedAcoes.map((row) => (
                      <AcaoTableRow key={`${row.ticker}-${row.snapshot_date}`} row={row} watchlistTickers={watchlistTickers} />
                    ))}
                {!isLoading && data?.results.length === 0 && (
                  <tr>
                    <td colSpan={10} className="py-12 text-center text-sm text-zinc-500">
                      Nenhuma ação encontrada com os filtros aplicados
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-4 py-3 border-t border-zinc-100 flex items-center justify-between">
              <span className="text-xs text-zinc-500">
                Página {currentPage} de {totalPages}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                  disabled={offset === 0}
                  className="px-3 py-1.5 rounded text-xs border border-zinc-200 disabled:opacity-40 hover:bg-zinc-50 transition-colors"
                >
                  Anterior
                </button>
                <button
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                  disabled={currentPage >= totalPages}
                  className="px-3 py-1.5 rounded text-xs border border-zinc-200 disabled:opacity-40 hover:bg-zinc-50 transition-colors"
                >
                  Próxima
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      <p className="text-xs text-zinc-400 text-center">
        Dados atualizados diariamente via snapshot B3. Fonte: brapi.dev
      </p>
    </div>
  );
}
