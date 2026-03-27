"use client";
import { useDashboardSummary } from "@/features/dashboard/hooks/useDashboardSummary";
import { NetWorthCard } from "./NetWorthCard";
import { AllocationChart } from "./AllocationChart";
import { PortfolioChart } from "./PortfolioChart";
import { MacroIndicators } from "./MacroIndicators";
import { RecentTransactions } from "./RecentTransactions";
import { Skeleton } from "@/components/ui/skeleton";
import { OnboardingBanner } from "@/features/onboarding/OnboardingBanner";

export function DashboardContent() {
  const { data, isLoading, error } = useDashboardSummary();

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-600">
        <p className="font-medium">Erro ao carregar carteira</p>
        <p className="text-sm mt-1">{error.message}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <OnboardingBanner />
      {/* Row 1: Net Worth */}
      {isLoading ? (
        <Skeleton className="h-32 w-full rounded-xl" />
      ) : data ? (
        <NetWorthCard
          netWorth={data.net_worth}
          totalReturn={data.total_return}
          totalReturnPct={data.total_return_pct}
          dailyPnl={data.daily_pnl}
          dailyPnlPct={data.daily_pnl_pct}
          dataStale={data.data_stale}
          isLoading={false}
        />
      ) : null}

      {/* Row 2: Macro Indicators */}
      <MacroIndicators />

      {/* Row 3: Charts — side by side on lg, stacked on mobile */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {isLoading ? (
          <>
            <Skeleton className="h-80 rounded-xl" />
            <Skeleton className="h-80 rounded-xl" />
          </>
        ) : data ? (
          <>
            <AllocationChart allocation={data.asset_allocation} />
            <PortfolioChart data={data.portfolio_timeseries} />
          </>
        ) : null}
      </div>

      {/* Row 4: Recent Transactions */}
      {isLoading ? (
        <Skeleton className="h-48 w-full rounded-xl" />
      ) : data ? (
        <RecentTransactions transactions={data.recent_transactions} />
      ) : null}
    </div>
  );
}
