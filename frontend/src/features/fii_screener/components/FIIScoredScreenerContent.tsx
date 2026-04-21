"use client";
import { useState, useMemo } from "react";
import Link from "next/link";
import { useFIIScoredScreener } from "../hooks/useFIIScreener";
import type { FIIScoredRow } from "../types";
import { useSortedData } from "@/hooks/useSort";
import { SortableHeader } from "@/components/ui/SortableHeader";

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
  if (!seg) return <span className="text-gray-400">—</span>;
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
    Outros: "bg-gray-100 text-gray-600",
  };
  const cls = colors[seg] ?? "bg-gray-100 text-gray-600";
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>
      {seg}
    </span>
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

  const pvpFmt = fmt(row.pvp);
  const scoreFmt = row.score !== null && row.score !== undefined
    ? parseFloat(row.score).toFixed(1)
    : "—";

  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
      <td className="py-3 px-4 text-sm text-gray-500 tabular-nums">{rank}</td>
      <td className="py-3 px-4">
        <Link
          href={`/fii/${row.ticker}`}
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
      <td className="py-3 px-4">{segmentoBadge(row.segmento)}</td>
      <td className="py-3 px-4 text-sm font-medium">{dyPct}</td>
      <td className="py-3 px-4 text-sm">{pvpFmt}</td>
      <td className="py-3 px-4 text-sm">
        {row.daily_liquidity !== null && row.daily_liquidity !== undefined
          ? `R$ ${row.daily_liquidity.toLocaleString("pt-BR")}`
          : "—"}
      </td>
      <td className="py-3 px-4 text-sm font-semibold">{scoreFmt}</td>
    </tr>
  );
}

const TH = "text-left py-3 px-4 text-xs font-semibold text-gray-600";

export function FIIScoredScreenerContent() {
  const { data, isLoading, error } = useFIIScoredScreener();
  const [segmentoFilter, setSegmentoFilter] = useState<string>("");
  const [minDyFilter, setMinDyFilter] = useState<string>("");

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
    filtered as Record<string, unknown>[],
    "score",
    "desc"
  );

  function clearFilters() {
    setSegmentoFilter("");
    setMinDyFilter("");
  }

  return (
    <div className="space-y-4">
      {/* Score not available notice */}
      {data && data.score_available === false && (
        <div className="rounded-lg bg-yellow-50 border border-yellow-200 px-4 py-3 text-sm text-yellow-800">
          <strong>Scores sendo calculados</strong> — disponíveis amanhã após o processamento noturno dos dados.
        </div>
      )}

      {/* Filter bar */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Segmento
            </label>
            <select
              value={segmentoFilter}
              onChange={(e) => setSegmentoFilter(e.target.value)}
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
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
            <label className="block text-xs font-medium text-gray-600 mb-1">
              DY min (%)
            </label>
            <input
              type="number"
              step="0.1"
              placeholder="Ex: 8"
              value={minDyFilter}
              onChange={(e) => setMinDyFilter(e.target.value)}
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={clearFilters}
              className="px-4 py-2 rounded-md text-sm text-gray-600 border border-gray-200 hover:bg-gray-50 transition-colors w-full sm:w-auto"
            >
              Limpar filtros
            </button>
          </div>
        </div>
      </div>

      {/* Status bar */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>
          {isLoading
            ? "Carregando..."
            : `${filtered.length} FII${filtered.length !== 1 ? "s" : ""}`}
        </span>
        {data?.score_available && data.results.length > 0 && (
          <span className="text-gray-400">Ordenado por score (maior = melhor)</span>
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
                      <tr key={i} className="border-b border-gray-100">
                        {Array.from({ length: 7 }).map((_, j) => (
                          <td key={j} className="py-3 px-4">
                            <div className="h-4 bg-gray-100 rounded animate-pulse" />
                          </td>
                        ))}
                      </tr>
                    ))
                  : sortedFiis.map((row, idx) => (
                      <FIIScoredTableRow key={(row as FIIScoredRow).ticker} row={row as FIIScoredRow} rank={idx + 1} />
                    ))}
                {!isLoading && data && filtered.length === 0 && (
                  <tr>
                    <td
                      colSpan={7}
                      className="py-12 text-center text-sm text-gray-500"
                    >
                      Nenhum FII encontrado com os filtros selecionados
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
        <p className="text-xs text-gray-400 text-center">{data.disclaimer}</p>
      )}
    </div>
  );
}
