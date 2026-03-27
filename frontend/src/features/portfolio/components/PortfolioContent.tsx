"use client";
import { PositionsTable } from "./PositionsTable";
import { PnlTable } from "./PnlTable";
import { DividendHistory } from "./DividendHistory";
import { BenchmarkChart } from "./BenchmarkChart";

export function PortfolioContent() {
  return (
    <div className="space-y-6">
      <PositionsTable />
      <PnlTable />
      <BenchmarkChart />
      <DividendHistory />
    </div>
  );
}
