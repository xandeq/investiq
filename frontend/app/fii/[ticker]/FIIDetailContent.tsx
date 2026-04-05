"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getFIIScreenerRanked } from "@/features/fii_screener/api";
import { useFIIAnalysis } from "@/features/fii_detail/hooks/useFIIAnalysis";
import { FIIDYChart } from "@/features/fii_detail/components/FIIDYChart";
import { FIIPVPChart } from "@/features/fii_detail/components/FIIPVPChart";
import { FIIPortfolioSection } from "@/features/fii_detail/components/FIIPortfolioSection";
import { FIIAnalysisCard } from "@/features/fii_detail/components/FIIAnalysisCard";
import type { FIIAnalysisResult, FIIPortfolio } from "@/features/fii_detail/types";

interface Props {
  ticker: string;
}

export function FIIDetailContent({ ticker }: Props) {
  // Fetch basic FII data from screener (pre-calculated, cached)
  const screenerQuery = useQuery({
    queryKey: ["fii-screener-ranked"],
    queryFn: getFIIScreenerRanked,
    staleTime: 3_600_000,
  });

  const fiiRow = screenerQuery.data?.results?.find(
    (r) => r.ticker === ticker.toUpperCase()
  );

  // IA analysis hook (user-triggered via onClick — NOT auto-start)
  const { triggerAnalysis, isStarting, startError, polling } = useFIIAnalysis(ticker);

  // Extract analysis result — flat result dict from run_fii_analysis
  const analysisResult = polling.data?.result as FIIAnalysisResult | null | undefined;
  const dividendsMonthly = analysisResult?.dividends_monthly ?? [];
  const portfolio: FIIPortfolio | null = analysisResult?.portfolio ?? null;
  const narrative: string | null = analysisResult?.narrative ?? null;

  // KPI values: prefer analysis result (richer), fallback to screener row
  const dy12m =
    analysisResult?.dy_12m ??
    (fiiRow?.dy_12m ? parseFloat(fiiRow.dy_12m) : null);
  const pvp =
    analysisResult?.pvp ??
    (fiiRow?.pvp ? parseFloat(fiiRow.pvp) : null);
  const liquidity =
    analysisResult?.daily_liquidity ??
    (fiiRow?.daily_liquidity != null ? fiiRow.daily_liquidity : null);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-4">
        <Link
          href="/fii/screener"
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          ← Voltar ao Screener
        </Link>
      </div>

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">{ticker}</h1>
        {fiiRow?.short_name && (
          <p className="text-muted-foreground">{fiiRow.short_name}</p>
        )}
        {fiiRow?.segmento && (
          <span className="inline-block mt-1 px-2 py-0.5 bg-muted rounded text-xs">
            {fiiRow.segmento}
          </span>
        )}
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <KPICard label="P/VP" value={pvp != null ? pvp.toFixed(2) : "—"} />
        <KPICard
          label="DY 12m"
          value={dy12m != null ? `${(dy12m * 100).toFixed(1)}%` : "—"}
        />
        <KPICard
          label="Ultimo Dividendo"
          value={
            analysisResult?.last_dividend != null
              ? `R$${analysisResult.last_dividend.toFixed(2)}`
              : "—"
          }
        />
        <KPICard
          label="Liquidez Diaria"
          value={
            liquidity != null
              ? `R$${(liquidity / 1000).toFixed(0)}k`
              : "—"
          }
        />
      </div>

      {/* Charts — populated after analysis completes */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <FIIDYChart data={dividendsMonthly} />
        <FIIPVPChart pvp={pvp} bookValue={analysisResult?.book_value ?? null} />
      </div>

      {/* Portfolio Section — shown when analysis result has portfolio data */}
      {portfolio && <FIIPortfolioSection portfolio={portfolio} />}

      {/* IA Analysis Card */}
      <FIIAnalysisCard
        onTrigger={triggerAnalysis}
        isStarting={isStarting}
        startError={startError}
        status={polling.data?.status}
        narrative={narrative}
        disclaimer={polling.data?.disclaimer}
      />

      {/* Screener loading state */}
      {screenerQuery.isLoading && (
        <div className="text-center text-muted-foreground py-4">
          Carregando dados do FII...
        </div>
      )}
    </div>
  );
}

function KPICard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-muted/50 rounded-lg p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-xl font-bold">{value}</p>
    </div>
  );
}
