"use client";
import { useDashboardSummary } from "@/features/dashboard/hooks/useDashboardSummary";
import { NetWorthCard } from "./NetWorthCard";
import { AllocationChart } from "./AllocationChart";
import { PortfolioChart } from "./PortfolioChart";
import { MacroIndicators } from "./MacroIndicators";
import { RecentTransactions } from "./RecentTransactions";
import { ActionInbox } from "./ActionInbox";
import { Skeleton } from "@/components/ui/skeleton";
import Link from "next/link";
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

  // Empty portfolio: data loaded, net_worth = 0, no recent transactions
  const isEmpty =
    !isLoading &&
    data &&
    parseFloat(data.net_worth) === 0 &&
    data.recent_transactions.length === 0;

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
      {/* Empty portfolio — show 3-step CTA instead of zero cards */}
      {isEmpty && (
        <div className="rounded-xl border border-dashed border-gray-200 bg-white p-10 text-center">
          <p className="text-4xl mb-3">🚀</p>
          <h2 className="text-lg font-bold text-gray-900">Sua carteira está vazia</h2>
          <p className="text-sm text-muted-foreground mt-1 mb-6 max-w-sm mx-auto">
            Comece registrando suas posições para ver P&L, alocação e análise de desempenho.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              href="/imports"
              className="px-5 py-2.5 text-sm font-semibold bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              Importar extrato da B3
            </Link>
            <Link
              href="/portfolio/transactions"
              className="px-5 py-2.5 text-sm font-semibold border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Adicionar manualmente
            </Link>
          </div>
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

      {/* Row 5: Action Inbox (5 sources aggregated, ranked, no AI) */}
      <ActionInbox />
    </div>
  );
}
