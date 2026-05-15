"use client";
import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { createChart, AreaSeries, LineSeries } from "lightweight-charts";
import { apiClient } from "@/lib/api-client";
import type { TimeseriesPoint } from "@/features/dashboard/types";

interface Props {
  data: TimeseriesPoint[];
}

interface MacroCache {
  cdi: string;
}

/** Compute CDI benchmark series aligned to portfolio dates.
 *
 * Uses compound daily CDI starting from portfolio's first snapshot.
 * Formula: V(t) = V0 × (1 + cdi_annual)^(t/252)
 */
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
        textColor: "#64748b",
      },
      grid: {
        vertLines: { color: "#f1f5f9" },
        horzLines: { color: "#f1f5f9" },
      },
    });

    // Portfolio value series
    const portfolioSeries = chart.addSeries(AreaSeries, {
      lineColor: "#2563eb",
      topColor: "rgba(37, 99, 235, 0.20)",
      bottomColor: "rgba(37, 99, 235, 0)",
      lineWidth: 2,
    });
    portfolioSeries.setData(
      data.map((p) => ({ time: p.date, value: parseFloat(p.value) }))
    );

    // CDI benchmark line (only if rate available and > 1 data point)
    if (cdiRate > 0 && data.length > 1) {
      const cdiBenchmark = buildCdiBenchmark(data, cdiRate);
      const cdiSeries = chart.addSeries(LineSeries, {
        color: "#10b981",
        lineWidth: 1,
        lineStyle: 2, // dashed
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
      <div className="rounded-xl border bg-card p-6">
        <h3 className="text-sm font-medium mb-4">Evolução do Patrimônio</h3>
        <div className="flex items-center justify-center h-[280px] text-muted-foreground text-sm">
          Sem dados históricos
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border bg-card p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium">Evolução do Patrimônio</h3>
        {cdiRate > 0 && (
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="inline-block w-3 h-0.5 bg-blue-600 rounded" />
              Carteira
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block w-3 border-t border-dashed border-emerald-500" />
              CDI ({(cdiRate * 100).toFixed(1)}% a.a.)
            </span>
          </div>
        )}
      </div>
      <div ref={containerRef} className="w-full" />
    </div>
  );
}
