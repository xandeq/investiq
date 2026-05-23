"use client";
import { motion } from "framer-motion";
import { UploadSimple, PlusCircle, Warning } from "@phosphor-icons/react";
import { useDashboardSummary } from "@/features/dashboard/hooks/useDashboardSummary";
import { NetWorthCard } from "./NetWorthCard";
import { AllocationChart } from "./AllocationChart";
import { PortfolioHistoryCard } from "./PortfolioHistoryCard";
import { MacroIndicators } from "./MacroIndicators";
import { RecentTransactions } from "./RecentTransactions";
import { ActionInbox } from "./ActionInbox";
import { RiskMetricsCard } from "./RiskMetricsCard";
import { SectorAllocationChart } from "./SectorAllocationChart";
import { DividendCalendarCard } from "./DividendCalendarCard";
import { DividendRankingCard } from "./DividendRankingCard";
import { DividendIncomeCard } from "./DividendIncomeCard";
import { MonthlyReturnHeatmap } from "./MonthlyReturnHeatmap";
import { GoalsProgressCard } from "./GoalsProgressCard";
import { PositionMoversCard } from "./PositionMoversCard";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
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
          <Warning size={22} weight="fill" className="text-amber-500 shrink-0 mt-0.5" aria-hidden />
          <div className="flex-1">
            <p className="font-semibold text-amber-900">Dados temporariamente indisponíveis</p>
            <p className="text-sm text-amber-700 mt-1">
              Não foi possível carregar sua carteira agora. Isso pode ser um problema temporário — tente novamente em alguns instantes.
            </p>
            <button
              onClick={() => refetch()}
              className="mt-3 px-4 py-1.5 text-sm font-medium bg-amber-600 text-white rounded-lg hover:bg-amber-700 active:scale-[0.97] transition-all duration-150"
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
          <Warning size={16} weight="fill" className="text-amber-500 shrink-0" aria-hidden />
          <span>Cotações desatualizadas — os valores exibidos podem não refletir o mercado atual.</span>
          <button onClick={() => refetch()} className="ml-auto underline hover:no-underline font-medium">Atualizar</button>
        </div>
      )}
      {/* Empty portfolio — premium empty state */}
      {isEmpty && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="rounded-xl border border-dashed border-zinc-200 bg-white p-12 text-center"
        >
          {/* SVG illustration — no emojis */}
          <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-blue-50">
            <svg
              viewBox="0 0 64 64"
              fill="none"
              className="h-9 w-9"
              aria-hidden
            >
              <rect x="8" y="20" width="48" height="32" rx="4" fill="#EFF6FF" stroke="#BFDBFE" strokeWidth="2" />
              <path d="M20 36 L28 28 L36 33 L44 24" stroke="#3B82F6" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx="44" cy="24" r="3" fill="#3B82F6" />
              <path d="M24 16 L32 8 L40 16" stroke="#93C5FD" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx="32" cy="8" r="2.5" fill="#60A5FA" />
            </svg>
          </div>

          <h2 className="text-lg font-bold text-zinc-900 tracking-tight">Sua carteira está vazia</h2>
          <p className="text-sm text-zinc-500 mt-1.5 mb-7 max-w-sm mx-auto leading-relaxed">
            Registre suas posições para visualizar P&amp;L, alocação por classe e análise de desempenho.
          </p>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              href="/imports"
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-semibold bg-blue-500 text-white rounded-lg hover:bg-blue-600 active:scale-[0.98] transition-all duration-150"
            >
              <UploadSimple size={16} weight="bold" aria-hidden />
              Importar extrato da B3
            </Link>
            <Link
              href="/portfolio/transactions"
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-semibold border border-zinc-200 rounded-lg hover:bg-zinc-50 active:scale-[0.98] transition-all duration-150"
            >
              <PlusCircle size={16} weight="regular" aria-hidden />
              Adicionar manualmente
            </Link>
          </div>
        </motion.div>
      )}

      {/* Row 1: Net Worth */}
      {isLoading ? (
        <ShimmerSkeleton className="h-32 w-full rounded-xl" />
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

      {/* Row 2b: Position Movers — today's top gainers/losers from portfolio */}
      <PositionMoversCard />

      {/* Row 3: Charts — side by side on lg, stacked on mobile */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {isLoading ? (
          <>
            <ShimmerSkeleton className="h-80 rounded-xl" />
            <ShimmerSkeleton className="h-80 rounded-xl" />
          </>
        ) : data ? (
          <>
            <AllocationChart allocation={data.asset_allocation} />
            <PortfolioHistoryCard />
          </>
        ) : null}
      </div>

      {/* Row 3b: Risk Metrics */}
      <RiskMetricsCard />

      {/* Row 3c: Sector Allocation */}
      <SectorAllocationChart />

      {/* Row 3d: Dividend Calendar */}
      <DividendCalendarCard />

      {/* Row 3e: Dividend Ranking */}
      <DividendRankingCard />

      {/* Row 3f: Dividend Income History */}
      <DividendIncomeCard />

      {/* Row 3g: Monthly Return Heatmap */}
      <MonthlyReturnHeatmap />

      {/* Row 3h: Investment Goals Progress */}
      <GoalsProgressCard />

      {/* Row 4: Recent Transactions */}
      {isLoading ? (
        <ShimmerSkeleton className="h-48 w-full rounded-xl" />
      ) : data ? (
        <RecentTransactions transactions={data.recent_transactions} />
      ) : null}

      {/* Row 5: Action Inbox (5 sources aggregated, ranked, no AI) */}
      <ActionInbox />
    </div>
  );
}
