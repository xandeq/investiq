"use client";
import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { createChart, AreaSeries, LineSeries } from "lightweight-charts";
import { apiClient } from "@/lib/api-client";
import type { TimeseriesPoint } from "@/features/dashboard/types";

interface Props {
  data: TimeseriesPoint[];
}

interface MacroCache {
  cdi: string;
}

function buildCdiBenchmark(
  data: TimeseriesPoint[],
  cdiAnnual: number
): { time: string; value: number }[] {
  if (!data.length || cdiAnnual <= 0) return [];

  const startValue = parseFloat(data[0].value);
  if (!startValue || startValue <= 0) return [];

  const startDate = new Date(data[0].date);
  const dailyCdi = Math.pow(1 + cdiAnnual, 1 / 252) - 1;

  return data.map((p) => {
    const date = new Date(p.date);
    const days = Math.round(
      (date.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)
    );
    const factor = Math.pow(1 + dailyCdi, days);
    return { time: p.date, value: Math.round(startValue * factor * 100) / 100 };
  });
}

export function PortfolioChart({ data }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  const { data: macro } = useQuery({
    queryKey: ["market-data", "macro"],
    queryFn: () => apiClient<MacroCache>("/market-data/macro"),
    staleTime: 5 * 60 * 1000,
  });

  const cdiRate = macro ? parseFloat(macro.cdi) : 0;

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 280,
      layout: {
        background: { color: "transparent" },
        textColor: "#a1a1aa",
      },
      grid: {
        vertLines: { color: "#f4f4f5" },
        horzLines: { color: "#f4f4f5" },
      },
    });

    const seen = new Map<string, number>();
    for (const p of data) {
      const v = parseFloat(p.value);
      if (!isNaN(v)) seen.set(p.date, v);
    }
    const cleanData = Array.from(seen.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([time, value]) => ({ time, value }));

    if (cleanData.length === 0) { chart.remove(); return; }

    const portfolioSeries = chart.addSeries(AreaSeries, {
      lineColor: "#2563eb",
      topColor: "rgba(37, 99, 235, 0.15)",
      bottomColor: "rgba(37, 99, 235, 0)",
      lineWidth: 2,
    });
    portfolioSeries.setData(cleanData);

    const dataForCdi = cleanData.map((p) => ({
      date: p.time as string,
      value: String(p.value),
    }));
    if (cdiRate > 0 && cleanData.length > 1) {
      const cdiBenchmark = buildCdiBenchmark(dataForCdi, cdiRate);
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
  }, [data, cdiRate]);

  if (data.length === 0) {
    return (
      <div className="rounded-xl border border-zinc-200 bg-white p-5">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 mb-4">
          Evolução do Patrimônio
        </h3>
        <div className="flex items-center justify-center h-[280px] text-zinc-400 text-sm">
          Sem dados históricos
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-xl border border-zinc-200 bg-white p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
          Evolução do Patrimônio
        </h3>
        {cdiRate > 0 && (
          <div className="flex items-center gap-3 text-xs text-zinc-400">
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-3 h-0.5 bg-blue-600 rounded" aria-hidden />
              Carteira
            </span>
            <span className="flex items-center gap-1.5">
              <span
                className="inline-block w-3 border-t border-dashed border-emerald-500"
                aria-hidden
              />
              CDI ({(cdiRate * 100).toFixed(1)}% a.a.)
            </span>
          </div>
        )}
      </div>
      <div ref={containerRef} className="w-full" />
    </motion.div>
  );
}
