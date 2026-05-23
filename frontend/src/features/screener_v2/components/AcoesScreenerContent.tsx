"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { Eye, EyeSlash, DownloadSimple, Link as LinkIcon, Check } from "@phosphor-icons/react";
import { useAcoesScreener } from "../hooks/useAcoesScreener";
import { exportAcoesScreenerCSV } from "../api";
import type { AcaoRow, AcaoScreenerParams } from "../types";
import { useSortedData } from "@/hooks/useSort";
import { SortableHeader } from "@/components/ui/SortableHeader";
import { useWatchlist, useAddToWatchlist, useRemoveFromWatchlist } from "@/features/watchlist/hooks/useWatchlist";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

const SECTORS = [
  "Financeiro", "Energia", "Tecnologia", "Consumo", "Saúde",
  "Utilidades", "Materiais", "Indústria", "Comunicação", "Imobiliário",
];

const PAGE_SIZE = 50;
const STORAGE_KEY = "investiq:screenerv2:acoes";

const NUM_PARAMS = ["min_dy", "max_pl", "max_pvp", "max_ev_ebitda", "min_market_cap"] as const;
const STR_PARAMS = ["sector"] as const;
type NumParam = (typeof NUM_PARAMS)[number];
type StrParam = (typeof STR_PARAMS)[number];

function parseSearchParams(sp: URLSearchParams): AcaoScreenerParams {
  const out: AcaoScreenerParams = {};
  for (const k of NUM_PARAMS) {
    const v = sp.get(k);
    if (v !== null) (out as Record<string, unknown>)[k] = +v;
  }
  for (const k of STR_PARAMS) {
    const v = sp.get(k);
    if (v) (out as Record<string, unknown>)[k] = v;
  }
  return out;
}

function buildSearchParams(f: AcaoScreenerParams): URLSearchParams {
  const sp = new URLSearchParams();
  for (const k of NUM_PARAMS) {
    const v = (f as Record<string, unknown>)[k];
    if (v !== undefined && v !== null) sp.set(k, String(v));
  }
  for (const k of STR_PARAMS) {
    const v = (f as Record<string, unknown>)[k];
    if (v) sp.set(k, String(v));
  }
  return sp;
}

function countActive(f: AcaoScreenerParams): number {
  return (
    (NUM_PARAMS as readonly string[]).concat(STR_PARAMS).filter(
      (k) => (f as Record<string, unknown>)[k] !== undefined && (f as Record<string, unknown>)[k] !== null && (f as Record<string, unknown>)[k] !== ""
    ).length
  );
}

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

function valColor(val: string | null, low: number, high: number, invert = false): string {
  if (!val) return "text-zinc-500";
  const n = parseFloat(val);
  if (isNaN(n)) return "text-zinc-500";
  const good = invert ? n < low : n >= low;
  const mid = invert ? n < high : n < high;
  if (good && mid) return "text-emerald-600 font-medium";
  if (mid) return "text-amber-600";
  return invert ? "text-red-500" : "text-zinc-700";
}

function AcaoTableRow({ row, watchlistTickers }: { row: AcaoRow; watchlistTickers: Set<string> }) {
  const inWatchlist = watchlistTickers.has(row.ticker);
  const dyClass = row.dy
    ? parseFloat(row.dy) >= 5 ? "text-emerald-600 font-medium" : parseFloat(row.dy) >= 3 ? "text-zinc-700" : "text-zinc-500"
    : "text-zinc-400";
  const plClass = valColor(row.pl, 0, 25, true);
  const pvpClass = row.pvp
    ? parseFloat(row.pvp) < 1 ? "text-emerald-600 font-medium" : parseFloat(row.pvp) > 2.5 ? "text-red-500" : "text-zinc-700"
    : "text-zinc-500";

  return (
    <tr className="border-b border-zinc-100 hover:bg-zinc-50 transition-colors">
      <td className="py-3 px-4">
        <Link href={`/stock/${row.ticker}`} className="group">
          <div className="font-mono font-bold text-sm group-hover:text-blue-600 transition-colors">{row.ticker}</div>
          <div className="text-xs text-zinc-500 truncate max-w-[140px]">{row.short_name ?? "—"}</div>
        </Link>
      </td>
      <td className="py-3 px-4 text-xs text-zinc-600">{row.sector ?? "—"}</td>
      <td className="py-3 px-4 text-sm font-semibold tabular-nums">
        {row.price ? `R$ ${parseFloat(row.price).toFixed(2)}` : "—"}
      </td>
      <td className="py-3 px-4">{changeBadge(row.change_pct)}</td>
      <td className={`py-3 px-4 text-sm tabular-nums ${dyClass}`}>{fmt(row.dy, 2, "%")}</td>
      <td className={`py-3 px-4 text-sm tabular-nums ${plClass}`}>{fmt(row.pl)}</td>
      <td className={`py-3 px-4 text-sm tabular-nums ${pvpClass}`}>{fmt(row.pvp)}</td>
      <td className="py-3 px-4 text-sm tabular-nums text-zinc-700">{fmt(row.ev_ebitda)}</td>
      <td className="py-3 px-4 text-xs text-zinc-500 tabular-nums">{fmtBRL(row.market_cap)}</td>
      <td className="py-3 px-2">
        <WatchlistButton ticker={row.ticker} inWatchlist={inWatchlist} />
      </td>
    </tr>
  );
}

const FILTER_LABELS: Record<string, string> = {
  min_dy: "DY mínimo",
  max_pl: "P/L máximo",
  max_pvp: "P/VP máximo",
  max_ev_ebitda: "EV/EBITDA máximo",
  min_market_cap: "Market cap mínimo",
  sector: "Setor",
};

function AcoesEmptyState({
  applied,
  activeCount,
  onClear,
  onPreset,
  presets,
}: {
  applied: AcaoScreenerParams;
  activeCount: number;
  onClear: () => void;
  onPreset: (p: AcaoScreenerParams) => void;
  presets: { label: string; filters: AcaoScreenerParams }[];
}) {
  const activeFilters = (Object.keys(applied) as (keyof AcaoScreenerParams)[]).filter(
    (k) => applied[k] !== undefined && applied[k] !== null && applied[k] !== ""
  );

  return (
    <div className="flex flex-col items-center gap-4 py-4 max-w-sm mx-auto text-center">
      <div className="text-3xl select-none">🔍</div>
      <div>
        <p className="text-sm font-medium text-zinc-700">Nenhuma ação encontrada</p>
        {activeCount > 0 && (
          <p className="text-xs text-zinc-500 mt-1">
            {activeCount === 1
              ? "1 filtro ativo está"
              : `${activeCount} filtros ativos estão`}{" "}
            restringindo os resultados.
          </p>
        )}
      </div>

      {activeFilters.length > 0 && (
        <div className="flex flex-wrap justify-center gap-1.5">
          {activeFilters.map((k) => (
            <span
              key={k}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-xs text-amber-700"
            >
              {FILTER_LABELS[k] ?? k}:{" "}
              <span className="font-medium">
                {k === "min_market_cap"
                  ? fmtBRL(Number(applied[k]))
                  : String(applied[k])}
              </span>
            </span>
          ))}
        </div>
      )}

      <div className="flex flex-col gap-2 w-full">
        <button
          onClick={onClear}
          className="w-full px-4 py-2 rounded-md text-sm bg-blue-500 text-white hover:bg-blue-600 active:scale-[0.97] transition-all duration-150 font-medium"
        >
          Limpar filtros
        </button>
        {presets.length > 0 && (
          <div className="flex flex-col gap-1">
            <span className="text-xs text-zinc-400">Ou tente um preset:</span>
            <div className="flex flex-wrap justify-center gap-1.5">
              {presets.map((p) => (
                <button
                  key={p.label}
                  onClick={() => onPreset(p.filters)}
                  className="px-3 py-1 text-xs rounded-full border border-zinc-200 text-zinc-600 hover:border-blue-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function AcoesScreenerContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [filters, setFilters] = useState<AcaoScreenerParams>({});
  const [applied, setApplied] = useState<AcaoScreenerParams>({});
  const [offset, setOffset] = useState(0);
  const [excludePortfolio, setExcludePortfolio] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [copied, setCopied] = useState(false);

  // Track whether we wrote the URL ourselves to skip the URL→state sync on our own writes
  const selfNavRef = useRef(false);
  const isFirstMount = useRef(true);

  // Seed filters from URL (on mount) or localStorage (URL empty on mount)
  useEffect(() => {
    const urlFilters = parseSearchParams(searchParams);
    const hasUrlFilters = Object.keys(urlFilters).length > 0;

    if (isFirstMount.current) {
      isFirstMount.current = false;
      if (hasUrlFilters) {
        setFilters(urlFilters);
        setApplied(urlFilters);
      } else {
        try {
          const raw = localStorage.getItem(STORAGE_KEY);
          if (raw) {
            const saved = JSON.parse(raw) as AcaoScreenerParams;
            setFilters(saved);
            setApplied(saved);
          }
        } catch { /* ignore */ }
      }
      return;
    }

    // Subsequent URL changes = browser back/forward — sync applied from URL
    if (selfNavRef.current) {
      selfNavRef.current = false;
      return;
    }
    setFilters(urlFilters);
    setApplied(urlFilters);
    setOffset(0);
  }, [searchParams]); // eslint-disable-line react-hooks/exhaustive-deps

  const params: AcaoScreenerParams = { ...applied, limit: PAGE_SIZE, offset, exclude_portfolio: excludePortfolio };
  const { data, isLoading, isFetching, error } = useAcoesScreener(params);
  const { sorted: sortedAcoes, col, dir, toggle } = useSortedData(data?.results ?? []);
  const { data: watchlistItems = [] } = useWatchlist();
  const watchlistTickers = new Set(watchlistItems.map((w: { ticker: string }) => w.ticker));

  const applyFilters = useCallback(() => {
    setOffset(0);
    setApplied({ ...filters });
    // Commit to URL (shareable deep-link)
    const sp = buildSearchParams(filters);
    const qs = sp.toString();
    selfNavRef.current = true;
    router.replace(`${pathname}${qs ? `?${qs}` : ""}`, { scroll: false });
    // Persist to localStorage as fallback for URL-less visits
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(filters)); } catch { /* ignore */ }
  }, [filters, router, pathname]);

  const clearFilters = useCallback(() => {
    setFilters({});
    setApplied({});
    setOffset(0);
    selfNavRef.current = true;
    router.replace(pathname, { scroll: false });
    try { localStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
  }, [router, pathname]);

  function applyPreset(preset: AcaoScreenerParams) {
    setFilters(preset);
    setApplied(preset);
    setOffset(0);
    const sp = buildSearchParams(preset);
    const qs = sp.toString();
    selfNavRef.current = true;
    router.replace(`${pathname}${qs ? `?${qs}` : ""}`, { scroll: false });
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(preset)); } catch { /* ignore */ }
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
      // silent — export failure must not break the UI
    } finally {
      setExporting(false);
    }
  }

  function handleCopyLink() {
    try {
      navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* ignore — clipboard may be unavailable */ }
  }

  const PRESETS: { label: string; filters: AcaoScreenerParams }[] = [
    { label: "Dividendos", filters: { min_dy: 8, max_pl: 20 } },
    { label: "Value", filters: { max_pvp: 2, max_pl: 15 } },
    { label: "Growth", filters: { max_ev_ebitda: 10, max_pl: 25 } },
  ];

  const total = data?.total ?? 0;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const activeCount = countActive(applied);

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
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={clearFilters}
              className="px-4 py-2 rounded-md text-sm text-zinc-600 border border-zinc-200 hover:bg-zinc-50 transition-colors"
            >
              Limpar
            </button>
            {activeCount > 0 && (
              <button
                onClick={handleCopyLink}
                title="Copiar link com os filtros atuais"
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md text-sm border border-zinc-200 text-zinc-600 hover:bg-zinc-50 transition-colors"
              >
                {copied ? <Check size={14} weight="bold" className="text-emerald-500" /> : <LinkIcon size={14} />}
                {copied ? "Copiado!" : "Copiar link"}
              </button>
            )}
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
              className="inline-flex items-center gap-2 px-4 py-2 rounded-md text-sm bg-blue-500 text-white hover:bg-blue-600 active:scale-[0.97] transition-all duration-150 font-medium"
            >
              Filtrar
              {activeCount > 0 && (
                <span className="bg-white/20 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center leading-none">
                  {activeCount}
                </span>
              )}
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
                        <td className="py-3 px-4 space-y-1.5">
                          <ShimmerSkeleton className="h-3.5 w-16" />
                          <ShimmerSkeleton className="h-3 w-28" />
                        </td>
                        <td className="py-3 px-4"><ShimmerSkeleton className="h-3.5 w-20" /></td>
                        <td className="py-3 px-4"><ShimmerSkeleton className="h-3.5 w-14" /></td>
                        <td className="py-3 px-4"><ShimmerSkeleton className="h-3.5 w-12" /></td>
                        <td className="py-3 px-4"><ShimmerSkeleton className="h-3.5 w-10" /></td>
                        <td className="py-3 px-4"><ShimmerSkeleton className="h-3.5 w-10" /></td>
                        <td className="py-3 px-4"><ShimmerSkeleton className="h-3.5 w-10" /></td>
                        <td className="py-3 px-4"><ShimmerSkeleton className="h-3.5 w-14" /></td>
                        <td className="py-3 px-4"><ShimmerSkeleton className="h-3.5 w-16" /></td>
                        <td className="py-3 px-2"><ShimmerSkeleton className="h-6 w-6 rounded-md" /></td>
                      </tr>
                    ))
                  : sortedAcoes.map((row) => (
                      <AcaoTableRow key={`${row.ticker}-${row.snapshot_date}`} row={row} watchlistTickers={watchlistTickers} />
                    ))}
                {!isLoading && data?.results.length === 0 && (
                  <tr>
                    <td colSpan={10} className="py-12 px-6">
                      <AcoesEmptyState applied={applied} activeCount={activeCount} onClear={clearFilters} onPreset={applyPreset} presets={PRESETS} />
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
                  className="px-3 py-1.5 rounded text-xs border border-zinc-200 disabled:opacity-40 hover:bg-zinc-50 active:scale-[0.97] transition-all duration-150"
                >
                  Anterior
                </button>
                <button
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                  disabled={currentPage >= totalPages}
                  className="px-3 py-1.5 rounded text-xs border border-zinc-200 disabled:opacity-40 hover:bg-zinc-50 active:scale-[0.97] transition-all duration-150"
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
