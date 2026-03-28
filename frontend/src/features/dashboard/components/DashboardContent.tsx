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
  const { data, isLoading, error, refetch } = useDashboardSummary();

  if (error) {
    // Plan C: user-friendly error with retry — log details to console for developers
    console.error("[InvestIQ] Falha ao carregar /dashboard/summary:", error);
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-6">
        <div className="flex items-start gap-3">
          <span className="text-2xl" aria-hidden>⚠️</span>
          <div className="flex-1">
            <p className="font-semibold text-amber-900">Dados temporariamente indisponíveis</p>
            <p className="text-sm text-amber-700 mt-1">
              Não foi possível carregar sua carteira agora. Isso pode ser um problema temporário — tente novamente em alguns instantes.
            </p>
            <button
              onClick={() => refetch()}
              className="mt-3 px-4 py-1.5 text-sm font-medium bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors"
            >
              Tentar novamente
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Plan B result: data returned but data_stale=true — show banner warning
  const showStaleBanner = data?.data_stale && !isLoading;

  return (
    <div className="space-y-6">
      <OnboardingBanner />
      {showStaleBanner && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 flex items-center gap-2 text-sm text-amber-800">
          <span aria-hidden>⚠️</span>
          <span>Cotações desatualizadas — os valores exibidos podem não refletir o mercado atual.</span>
          <button onClick={() => refetch()} className="ml-auto underline hover:no-underline font-medium">Atualizar</button>
        </div>
      )}
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
