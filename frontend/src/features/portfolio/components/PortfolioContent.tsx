"use client";
import { PositionsTable } from "./PositionsTable";
import { PnlTable } from "./PnlTable";
import { DividendHistory } from "./DividendHistory";
import { PortfolioSummary } from "./PortfolioSummary";
import { PortfolioHistoryChart } from "./PortfolioHistoryChart";
import { RebalancingCard } from "./RebalancingCard";
import { FundPositionsCard } from "./FundPositionsCard";
import { InvestmentGoalsCard } from "./InvestmentGoalsCard";

export function PortfolioContent() {
  return (
    <div className="space-y-6">
      <PortfolioSummary />
      <PortfolioHistoryChart />
      <InvestmentGoalsCard />
      <RebalancingCard />
      <FundPositionsCard />
      <PositionsTable />
      <PnlTable />
      <DividendHistory />
    </div>
  );
}
