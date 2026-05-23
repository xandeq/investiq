"use client";
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { createChart, AreaSeries, LineSeries } from "lightweight-charts";
import { apiClient } from "@/lib/api-client";
import { usePortfolioHistory, type HistoryRange } from "@/features/dashboard/hooks/usePortfolioHistory";
import { formatBRL } from "@/lib/formatters";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

interface MacroCache {
  cdi: string;
}

const RANGES: { label: string; value: HistoryRange }[] = [
  { label: "1M", value: "1m" },
  { label: "3M", value: "3m" },
  { label: "6M", value: "6m" },
  { label: "1A", value: "1y" },
  { label: "Tudo", value: "all" },
];

function buildCdiBenchmark(
  dates: string[],
  startValue: number,
  cdiAnnual: number
): { time: string; value: number }[] {
  if (!dates.length || cdiAnnual <= 0 || startValue <= 0) return [];

  const startDate = new Date(dates[0]);
  const dailyCdi = Math.pow(1 + cdiAnnual, 1 / 252) - 1;

  return dates.map((date) => {
    const d = new Date(date);
    const days = Math.round((d.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));
    const factor = Math.pow(1 + dailyCdi, days);
    return { time: date, value: Math.round(startValue * factor * 100) / 100 };
  });
}

function calcReturn(first: number, last: number): { abs: number; pct: number } {
  if (first <= 0) return { abs: 0, pct: 0 };
  return { abs: last - first, pct: ((last - first) / first) * 100 };
}

export function PortfolioHistoryCard() {
  const [range, setRange] = useState<HistoryRange>("3m");
  const containerRef = useRef<HTMLDivElement>(null);

  const { data, isLoading } = usePortfolioHistory(range);

  const { data: macro } = useQuery({
    queryKey: ["market-data", "macro"],
    queryFn: () => apiClient<MacroCache>("/market-data/macro"),
    staleTime: 5 * 60 * 1000,
  });

  const cdiRate = macro ? parseFloat(macro.cdi) : 0;

  const points = data?.points ?? [];
  const hasData = points.length >= 2;

  // Compute period return
  const firstValue = hasData ? parseFloat(points[0].total_value) : 0;
  const lastValue = hasData ? parseFloat(points[points.length - 1].total_value) : 0;
  const { abs: returnAbs, pct: returnPct } = calcReturn(firstValue, lastValue);
  const isPositive = returnAbs >= 0;

  useEffect(() => {
    if (!containerRef.current || !hasData) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 240,
      layout: {
        background: { color: "transparent" },
        textColor: "#a1a1aa",
      },
      grid: {
        vertLines: { color: "rgba(244,244,245,0.6)" },
        horzLines: { color: "rgba(244,244,245,0.6)" },
      },
      rightPriceScale: { borderColor: "transparent" },
      timeScale: { borderColor: "transparent", fixLeftEdge: true, fixRightEdge: true },
    });

    const cleanData = points
      .map((p) => ({ time: p.date, value: parseFloat(p.total_value) }))
      .filter((p) => !isNaN(p.value));

    const portfolioSeries = chart.addSeries(AreaSeries, {
      lineColor: "#2563eb",
      topColor: "rgba(37, 99, 235, 0.12)",
      bottomColor: "rgba(37, 99, 235, 0)",
      lineWidth: 2,
    });
    portfolioSeries.setData(cleanData);

    // Invested line
    const investedData = points
      .map((p) => ({ time: p.date, value: parseFloat(p.total_invested) }))
      .filter((p) => !isNaN(p.value));
    if (investedData.length > 0) {
      const investedSeries = chart.addSeries(LineSeries, {
        color: "#a1a1aa",
        lineWidth: 1,
        lineStyle: 2,
      });
      investedSeries.setData(investedData);
    }

    // CDI benchmark
    if (cdiRate > 0 && cleanData.length > 1) {
      const cdiBenchmark = buildCdiBenchmark(
        cleanData.map((p) => p.time as string),
        cleanData[0].value,
        cdiRate
      );
      const cdiSeries = chart.addSeries(LineSeries, {
        color: "#10b981",
        lineWidth: 1,
        lineStyle: 2,
      });
      cdiSeries.setData(cdiBenchmark);
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [points, cdiRate, hasData]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-xl border border-zinc-200 bg-white p-5"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
          Evolução do Patrimônio
        </h3>
        {/* Range selector */}
        <div className="flex items-center gap-1">
          {RANGES.map(({ label, value }) => (
            <button
              key={value}
              onClick={() => setRange(value)}
              className={`px-2 py-0.5 rounded text-xs font-medium active:scale-[0.97] transition-all duration-150 ${
                range === value
                  ? "bg-blue-500 text-white"
                  : "text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Period return summary */}
      {hasData && (
        <div className="flex items-baseline gap-3 mb-3">
          <span className="text-lg font-bold text-zinc-900 tabular-nums">{formatBRL(lastValue)}</span>
          <span className={`text-sm font-semibold tabular-nums ${isPositive ? "text-emerald-600" : "text-red-500"}`}>
            {isPositive ? "+" : ""}
            {returnPct.toFixed(2)}%
          </span>
          <span className={`text-xs tabular-nums ${isPositive ? "text-emerald-500" : "text-red-400"}`}>
            {isPositive ? "+" : ""}
            {formatBRL(returnAbs)} no período
          </span>
        </div>
      )}

      {/* Chart */}
      {isLoading ? (
        <ShimmerSkeleton className="h-[240px] w-full rounded-lg" />
      ) : !hasData ? (
        <div className="h-[240px] flex flex-col items-center justify-center gap-3 text-center bg-zinc-50 rounded-lg">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white border border-zinc-200">
            <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden>
              <path d="M3 17l5-5 4 4 5-6 4 4" stroke="#a1a1aa" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-medium text-zinc-700">Sem dados históricos</p>
            <p className="text-xs text-zinc-400 mt-0.5">Dados disponíveis após o fechamento do mercado.</p>
          </div>
        </div>
      ) : (
        <div ref={containerRef} className="w-full" />
      )}

      {/* Legend */}
      {hasData && (
        <div className="flex items-center gap-4 mt-2 text-xs text-zinc-400">
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-0.5 bg-blue-600 rounded" />
            Patrimônio
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 border-t border-dashed border-zinc-400" />
            Investido
          </span>
          {cdiRate > 0 && (
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-3 border-t border-dashed border-emerald-500" />
              CDI (<span className="tabular-nums">{(cdiRate * 100).toFixed(1)}% a.a.</span>)
            </span>
          )}
        </div>
      )}
    </motion.div>
  );
}
