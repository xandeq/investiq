"use client";
import { useEffect, useRef } from "react";
import { createChart, AreaSeries } from "lightweight-charts";
import type { TimeseriesPoint } from "@/features/dashboard/types";

interface Props {
  data: TimeseriesPoint[];
}

export function PortfolioChart({ data }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

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

    // v5 API: addSeries(AreaSeries, options) — NOT addAreaSeries()
    const series = chart.addSeries(AreaSeries, {
      lineColor: "#2563eb",
      topColor: "rgba(37, 99, 235, 0.25)",
      bottomColor: "rgba(37, 99, 235, 0)",
      lineWidth: 2,
    });

    series.setData(
      data.map((p) => ({ time: p.date, value: parseFloat(p.value) }))
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
  }, [data]);

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
      <h3 className="text-sm font-medium mb-4">Evolução do Patrimônio</h3>
      <div ref={containerRef} className="w-full" />
    </div>
  );
}
