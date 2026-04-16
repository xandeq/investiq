"use client";
import { PositionsTable } from "./PositionsTable";
import { PnlTable } from "./PnlTable";
import { DividendHistory } from "./DividendHistory";
import { BenchmarkChart } from "./BenchmarkChart";
import { PortfolioSummary } from "./PortfolioSummary";

export function PortfolioContent() {
  return (
    <div className="space-y-6">
      <PortfolioSummary />
      <PositionsTable />
      <PnlTable />
      <BenchmarkChart />
      <DividendHistory />
    </div>
  );
}
