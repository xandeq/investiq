"use client";
import { useMemo } from "react";
import Link from "next/link";
import { useFIIScoredScreener } from "../hooks/useFIIScreener";
import type { FIIScoredRow } from "../types";
import { useSortedData } from "@/hooks/useSort";
import { SortableHeader } from "@/components/ui/SortableHeader";
import { useFilterState } from "@/hooks/useFilterState";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

const FII_FILTER_DEFAULTS = { seg: "", dy: "" } as const;
type FIIFilterKey = keyof typeof FII_FILTER_DEFAULTS;

const SEGMENTOS = [
  "Logistica",
  "Lajes Corporativas",
  "Shopping",
  "Papel",
  "Hibrido",
  "FoF",
  "Residencial",
  "Agro",
  "Hotel",
  "Hospital",
  "Educacional",
  "Outros",
];

function fmt(val: string | null | undefined, decimals = 2, suffix = ""): string {
  if (val === null || val === undefined) return "—";
  const n = parseFloat(val);
  if (isNaN(n)) return "—";
  return n.toFixed(decimals) + suffix;
}

function segmentoBadge(seg: string | null) {
  if (!seg) return <span className="text-zinc-400">—</span>;
  const colors: Record<string, string> = {
    Logistica: "bg-orange-100 text-orange-700",
    "Lajes Corporativas": "bg-sky-100 text-sky-700",
    Shopping: "bg-rose-100 text-rose-700",
    Papel: "bg-blue-100 text-blue-700",
    Hibrido: "bg-purple-100 text-purple-700",
    FoF: "bg-teal-100 text-teal-700",
    Residencial: "bg-indigo-100 text-indigo-700",
    Agro: "bg-green-100 text-green-700",
    Hotel: "bg-yellow-100 text-yellow-700",
    Hospital: "bg-pink-100 text-pink-700",
    Educacional: "bg-cyan-100 text-cyan-700",
    Outros: "bg-zinc-100 text-zinc-600",
  };
  const cls = colors[seg] ?? "bg-zinc-100 text-zinc-600";
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>
      {seg}
    </span>
  );
}

function fmtLiquidity(val: number | null | undefined): string {
  if (val === null || val === undefined) return "—";
  if (val >= 1_000_000_000) return `R$ ${(val / 1_000_000_000).toFixed(1)}B`;
  if (val >= 1_000_000) return `R$ ${(val / 1_000_000).toFixed(1)}M`;
  if (val >= 1_000) return `R$ ${(val / 1_000).toFixed(0)}K`;
  return `R$ ${val.toLocaleString("pt-BR")}`;
}

function ScoreBar({ score }: { score: string | null | undefined }) {
  if (score === null || score === undefined) return <span className="text-zinc-400 text-sm">—</span>;
  const n = parseFloat(score);
  if (isNaN(n)) return <span className="text-zinc-400 text-sm">—</span>;
  const pct = Math.min(100, Math.max(0, n));
  const color =
    pct >= 80 ? "bg-emerald-500" : pct >= 60 ? "bg-blue-500" : pct >= 40 ? "bg-amber-400" : "bg-zinc-300";
  return (
    <div className="flex items-center gap-2 min-w-[80px]">
      <div className="flex-1 h-1.5 rounded-full bg-zinc-100 overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm font-semibold tabular-nums w-8 text-right">{n.toFixed(1)}</span>
    </div>
  );
}

function FIIScoredTableRow({
  row,
  rank,
}: {
  row: FIIScoredRow;
  rank: number;
}) {
  const dyPct =
    row.dy_12m !== null && row.dy_12m !== undefined
      ? (parseFloat(row.dy_12m) * 100).toFixed(2) + "%"
      : "—";

  const dyColor =
    row.dy_12m !== null && row.dy_12m !== undefined
      ? parseFloat(row.dy_12m) * 100 >= 10
        ? "text-emerald-600 font-semibold"
        : "text-zinc-800"
      : "";

  const pvpFmt = fmt(row.pvp);
  const pvpVal = row.pvp ? parseFloat(row.pvp) : null;
  const pvpColor = pvpVal !== null ? (pvpVal < 1 ? "text-emerald-600" : pvpVal > 1.5 ? "text-red-500" : "text-zinc-800") : "";

  return (
    <tr className="border-b border-zinc-100 hover:bg-zinc-50 transition-colors">
      <td className="py-3 px-4 text-xs text-zinc-400 tabular-nums w-8">{rank}</td>
      <td className="py-3 px-4">
        <Link
          href={`/fii/${row.ticker}`}
          className="group"
        >
          <div className="font-mono font-bold text-sm group-hover:text-blue-600 transition-colors">{row.ticker}</div>
          {row.short_name && (
            <div className="text-xs text-zinc-500 truncate max-w-[140px]">
              {row.short_name}
            </div>
          )}
        </Link>
      </td>
      <td className="py-3 px-4">{segmentoBadge(row.segmento)}</td>
      <td className={`py-3 px-4 text-sm tabular-nums ${dyColor}`}>{dyPct}</td>
      <td className={`py-3 px-4 text-sm tabular-nums ${pvpColor}`}>{pvpFmt}</td>
      <td className="py-3 px-4 text-xs text-zinc-600 tabular-nums">{fmtLiquidity(row.daily_liquidity)}</td>
      <td className="py-3 px-4"><ScoreBar score={row.score} /></td>
    </tr>
  );
}

const TH = "text-left py-3 px-4 text-xs font-semibold text-zinc-600";

function FIIEmptyState({
  hasFilters,
  segmento,
  minDy,
  onClear,
}: {
  hasFilters: boolean;
  segmento: string;
  minDy: string;
  onClear: () => void;
}) {
  return (
    <div className="flex flex-col items-center gap-4 py-4 max-w-sm mx-auto text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-zinc-50 border border-zinc-200">
        <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6 text-zinc-400" aria-hidden>
          <path d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5m0 0v-4a1 1 0 011-1h2a1 1 0 011 1v4m-4 0h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
      <div>
        <p className="text-sm font-medium text-zinc-700">Nenhum FII encontrado</p>
        {hasFilters && (
          <p className="text-xs text-zinc-500 mt-1">
            Os filtros aplicados não retornaram resultados.
          </p>
        )}
      </div>

      {hasFilters && (
        <div className="flex flex-wrap justify-center gap-1.5">
          {segmento && (
            <span className="px-2 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-xs text-amber-700 font-medium">
              Segmento: {segmento}
            </span>
          )}
          {minDy && (
            <span className="px-2 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-xs text-amber-700 font-medium">
              DY mín: {minDy}%
            </span>
          )}
        </div>
      )}

      <button
        onClick={onClear}
        className="px-4 py-2 rounded-md text-sm bg-blue-500 text-white hover:bg-blue-600 active:scale-[0.97] transition-all duration-150 font-medium"
      >
        {hasFilters ? "Limpar filtros" : "Recarregar"}
      </button>
    </div>
  );
}

export function FIIScoredScreenerContent() {
  const { data, isLoading, error } = useFIIScoredScreener();

  const filters = useFilterState<FIIFilterKey>({
    defaults: FII_FILTER_DEFAULTS,
    storageKey: "investiq:screener:fii",
  });

  const segmentoFilter = filters.values.seg;
  const minDyFilter = filters.values.dy;

  const filtered = useMemo(() => {
    if (!data?.results) return [];
    return data.results.filter((row) => {
      if (segmentoFilter && row.segmento !== segmentoFilter) return false;
      if (minDyFilter) {
        const minDy = parseFloat(minDyFilter);
        const rowDy = parseFloat(row.dy_12m ?? "0");
        // dy_12m is stored as decimal (0.09 = 9%), convert to % for comparison
        if (!isNaN(minDy) && rowDy * 100 < minDy) return false;
      }
      return true;
    });
  }, [data, segmentoFilter, minDyFilter]);

  const { sorted: sortedFiis, col, dir, toggle } = useSortedData(
    filtered,
    "score",
    "desc"
  );

  return (
    <div className="space-y-4">
      {/* Score not available notice */}
      {data && data.score_available === false && (
        <div className="rounded-lg bg-yellow-50 border border-yellow-200 px-4 py-3 text-sm text-yellow-800">
          <strong>Scores sendo calculados</strong> — disponíveis amanhã após o processamento noturno dos dados.
        </div>
      )}

      {/* Filter bar */}
      <div className="rounded-lg border border-zinc-200 bg-white p-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-medium text-zinc-600 mb-1">
              Segmento
            </label>
            <select
              value={segmentoFilter}
              onChange={(e) => filters.set("seg", e.target.value)}
              className="w-full rounded-md border border-zinc-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            >
              <option value="">Todos os segmentos</option>
              {SEGMENTOS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-600 mb-1">
              DY min (%)
            </label>
            <input
              type="number"
              step="0.1"
              placeholder="Ex: 8"
              value={minDyFilter}
              onChange={(e) => filters.set("dy", e.target.value)}
              className="w-full rounded-md border border-zinc-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={() => filters.clear()}
              className="px-4 py-2 rounded-md text-sm text-zinc-600 border border-zinc-200 hover:bg-zinc-50 active:scale-[0.97] transition-all duration-150 w-full sm:w-auto"
            >
              Limpar filtros
            </button>
          </div>
        </div>
      </div>

      {/* Status bar */}
      <div className="flex items-center justify-between text-xs text-zinc-500">
        <span>
          {isLoading
            ? "Carregando..."
            : `${filtered.length} FII${filtered.length !== 1 ? "s" : ""}`}
        </span>
        {data?.score_available && data.results.length > 0 && (
          <span className="text-zinc-400">Ordenado por score (maior = melhor)</span>
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
                  <th className={TH}>#</th>
                  <SortableHeader col="ticker" label="Ticker" activeCol={col} dir={dir} onSort={toggle} className={TH} />
                  <SortableHeader col="segmento" label="Segmento" activeCol={col} dir={dir} onSort={toggle} className={TH} />
                  <SortableHeader col="dy_12m" label="DY 12m" activeCol={col} dir={dir} onSort={toggle} className={TH} />
                  <SortableHeader col="pvp" label="P/VP" activeCol={col} dir={dir} onSort={toggle} className={TH} />
                  <SortableHeader col="daily_liquidity" label="Liquidez" activeCol={col} dir={dir} onSort={toggle} className={TH} />
                  <SortableHeader col="score" label="Score" activeCol={col} dir={dir} onSort={toggle} className={TH} />
                </tr>
              </thead>
              <tbody>
                {isLoading
                  ? Array.from({ length: 8 }).map((_, i) => (
                      <tr key={i} className="border-b border-zinc-100">
                        <td className="py-3 px-4"><ShimmerSkeleton className="h-3 w-4" /></td>
                        <td className="py-3 px-4 space-y-1.5">
                          <ShimmerSkeleton className="h-3.5 w-16" />
                          <ShimmerSkeleton className="h-3 w-28" />
                        </td>
                        <td className="py-3 px-4"><ShimmerSkeleton className="h-5 w-20 rounded-full" /></td>
                        <td className="py-3 px-4"><ShimmerSkeleton className="h-3.5 w-12" /></td>
                        <td className="py-3 px-4"><ShimmerSkeleton className="h-3.5 w-10" /></td>
                        <td className="py-3 px-4"><ShimmerSkeleton className="h-3.5 w-16" /></td>
                        <td className="py-3 px-4"><ShimmerSkeleton className="h-2 w-24 rounded-full" /></td>
                      </tr>
                    ))
                  : sortedFiis.map((row, idx) => (
                      <FIIScoredTableRow key={row.ticker} row={row} rank={idx + 1} />
                    ))}
                {!isLoading && data && filtered.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-12 px-6">
                      <FIIEmptyState
                        hasFilters={!!(segmentoFilter || minDyFilter)}
                        segmento={segmentoFilter}
                        minDy={minDyFilter}
                        onClear={() => filters.clear()}
                      />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* CVM Disclaimer */}
      {data?.disclaimer && (
        <p className="text-xs text-zinc-400 text-center">{data.disclaimer}</p>
      )}
    </div>
  );
}
