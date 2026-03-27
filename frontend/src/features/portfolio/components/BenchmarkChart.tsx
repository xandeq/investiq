"use client";
import { useEffect, useRef } from "react";
import { createChart, AreaSeries } from "lightweight-charts";
import { useQuery } from "@tanstack/react-query";
import { getDashboardSummary } from "@/features/dashboard/api";
import { useBenchmarks } from "@/features/portfolio/hooks/useBenchmarks";
import { Skeleton } from "@/components/ui/skeleton";

export function BenchmarkChart() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: getDashboardSummary,
    staleTime: 60 * 1000,
  });
  const { data: benchmarks } = useBenchmarks();

  const timeseries = summary?.portfolio_timeseries ?? [];
  const isLoading = summaryLoading;

  useEffect(() => {
    if (!containerRef.current || timeseries.length === 0) return;

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

    // v5 API: addSeries(AreaSeries, options) — NOT addAreaSeries()
    const portfolioSeries = chart.addSeries(AreaSeries, {
      lineColor: "#2563eb",
      topColor: "rgba(37, 99, 235, 0.2)",
      bottomColor: "rgba(37, 99, 235, 0)",
      lineWidth: 2,
      title: "Carteira",
    });
    portfolioSeries.setData(
      timeseries.map((p) => ({ time: p.date, value: parseFloat(p.value) }))
    );

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
  }, [timeseries]);

  if (isLoading) return <Skeleton className="h-[320px] w-full rounded-xl" />;

  return (
    <div className="rounded-xl border bg-card p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-sm font-medium">Rentabilidade vs Benchmark</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Evolução patrimonial da carteira
          </p>
        </div>
        {benchmarks && !benchmarks.data_stale && (
          <div className="flex gap-4 text-xs">
            <div className="flex items-center gap-1.5">
              <span className="inline-block w-3 h-0.5 bg-blue-600 rounded" />
              <span>Carteira</span>
            </div>
            <div className="text-muted-foreground">
              CDI: {benchmarks.cdi ? `${parseFloat(benchmarks.cdi).toFixed(2)}% a.a.` : "—"}
            </div>
            <div className="text-muted-foreground">
              IBOVESPA: {benchmarks.ibovespa_price ? parseFloat(benchmarks.ibovespa_price).toLocaleString("pt-BR") : "—"}
            </div>
          </div>
        )}
      </div>
      {timeseries.length === 0 ? (
        <div className="flex items-center justify-center h-[280px] text-muted-foreground text-sm">
          Sem dados históricos de carteira
        </div>
      ) : (
        <div ref={containerRef} className="w-full" />
      )}
      {benchmarks && (
        <p className="text-xs text-muted-foreground mt-2">
          Referência: CDI {benchmarks.cdi ? `${parseFloat(benchmarks.cdi).toFixed(2)}% a.a.` : "—"} ·{" "}
          IBOVESPA {benchmarks.ibovespa_price ? parseFloat(benchmarks.ibovespa_price).toLocaleString("pt-BR") : "—"} pts
        </p>
      )}
    </div>
  );
}
