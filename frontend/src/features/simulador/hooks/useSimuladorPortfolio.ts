"use client";
import { useMemo } from "react";
import { usePortfolioHealth } from "@/features/advisor/hooks/usePortfolioHealth";
import { usePnl } from "@/features/portfolio/hooks/usePnl";

export interface CurrentAllocationBRL {
  rf_brl: number;
  acoes_brl: number;
  fiis_brl: number;
}

export interface UseSimuladorPortfolioResult {
  /** True only when the user is authenticated AND getPortfolioHealth.has_portfolio is true AND pnl returned a positive total. */
  hasPortfolio: boolean;
  /** True while either underlying query is loading or fetching for the first time. */
  isLoading: boolean;
  /** True when either underlying query failed (network, 401, etc). */
  hasError: boolean;
  /** Sum of current_price × quantity across all positions (from getPnl.total_portfolio_value). 0 when hasPortfolio=false. */
  portfolioTotalBRL: number;
  /** Per-bucket current allocation in BRL. Zeros when hasPortfolio=false. */
  currentAllocation: CurrentAllocationBRL;
}

/**
 * Phase 28 — Bridges advisor/health (for has_portfolio gate) and portfolio/pnl
 * (for per-class allocation in BRL). The shipped PortfolioHealth schema does NOT
 * include allocation_by_class, so we source allocation from getPnl().allocation[].
 *
 * AssetClass mapping (LOCKED by Plan 02 class_mapping_rule):
 *   renda_fixa     → rf
 *   acao, bdr, etf → acoes
 *   fii            → fiis
 */
export function useSimuladorPortfolio(): UseSimuladorPortfolioResult {
  const healthQuery = usePortfolioHealth();
  const pnlQuery = usePnl();

  return useMemo(() => {
    const isLoading = healthQuery.isLoading || pnlQuery.isLoading;
    const hasError = healthQuery.isError || pnlQuery.isError;

    const hasPortfolio =
      !isLoading &&
      !hasError &&
      healthQuery.data?.has_portfolio === true &&
      !!pnlQuery.data &&
      parseFloat(pnlQuery.data.total_portfolio_value || "0") > 0;

    if (!hasPortfolio) {
      return {
        hasPortfolio: false,
        isLoading,
        hasError,
        portfolioTotalBRL: 0,
        currentAllocation: { rf_brl: 0, acoes_brl: 0, fiis_brl: 0 },
      };
    }

    const pnl = pnlQuery.data!;
    const portfolioTotalBRL = parseFloat(pnl.total_portfolio_value);

    let rf_brl = 0;
    let acoes_brl = 0;
    let fiis_brl = 0;
    for (const item of pnl.allocation) {
      const val = parseFloat(item.total_value || "0");
      if (!Number.isFinite(val)) continue;
      switch (item.asset_class) {
        case "renda_fixa":
          rf_brl += val;
          break;
        case "acao":
        case "bdr":
        case "etf":
          acoes_brl += val;
          break;
        case "fii":
          fiis_brl += val;
          break;
        default:
          // Defensive — log and drop unknown asset_class; should not occur with current enum
          // eslint-disable-next-line no-console
          console.warn("[useSimuladorPortfolio] unknown asset_class:", item.asset_class);
      }
    }

    return {
      hasPortfolio: true,
      isLoading: false,
      hasError: false,
      portfolioTotalBRL,
      currentAllocation: { rf_brl, acoes_brl, fiis_brl },
    };
  }, [healthQuery.data, healthQuery.isLoading, healthQuery.isError, pnlQuery.data, pnlQuery.isLoading, pnlQuery.isError]);
}
