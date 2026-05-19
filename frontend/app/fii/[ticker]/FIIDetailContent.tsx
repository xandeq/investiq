"use client";
import Link from "next/link";
import { Eye, EyeSlash } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useWatchlist, useAddToWatchlist, useRemoveFromWatchlist } from "@/features/watchlist/hooks/useWatchlist";
import { useStockQuote } from "@/hooks/useStockQuote";
import { getFIIScreenerRanked } from "@/features/fii_screener/api";
import { useFIIAnalysis } from "@/features/fii_detail/hooks/useFIIAnalysis";
import { FIIDYChart } from "@/features/fii_detail/components/FIIDYChart";
import { FIIPVPChart } from "@/features/fii_detail/components/FIIPVPChart";
import { FIIPortfolioSection } from "@/features/fii_detail/components/FIIPortfolioSection";
import { FIIAnalysisCard } from "@/features/fii_detail/components/FIIAnalysisCard";
import { StockPriceChart } from "@/app/stock/[ticker]/StockPriceChart";
import type { FIIAnalysisResult, FIIPortfolio } from "@/features/fii_detail/types";

interface Props {
  ticker: string;
}

function LivePriceChip({ ticker }: { ticker: string }) {
  const { data: quote } = useStockQuote(ticker);
  if (!quote || quote.data_stale) return null;
  const price = parseFloat(quote.price);
  const pct = parseFloat(quote.change_pct);
  const positive = pct >= 0;
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="font-semibold tabular-nums">
        {price.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
      </span>
      <span className={`tabular-nums font-medium ${positive ? "text-emerald-600" : "text-red-500"}`}>
        {positive ? "+" : ""}{pct.toFixed(2)}%
      </span>
    </div>
  );
}

function WatchlistToggle({ ticker }: { ticker: string }) {
  const { data: items = [] } = useWatchlist();
  const inWatchlist = items.some((w: { ticker: string }) => w.ticker === ticker);
  const addMut = useAddToWatchlist();
  const removeMut = useRemoveFromWatchlist();
  const pending = addMut.isPending || removeMut.isPending;
  return (
    <button
      disabled={pending}
      onClick={() => inWatchlist ? removeMut.mutate(ticker) : addMut.mutate({ ticker })}
      title={inWatchlist ? "Remover da watchlist" : "Adicionar à watchlist"}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-medium transition-colors disabled:opacity-50 ${
        inWatchlist
          ? "border-blue-200 text-blue-600 bg-blue-50 hover:bg-blue-100"
          : "border-zinc-200 text-zinc-500 hover:border-blue-300 hover:text-blue-500 hover:bg-blue-50"
      }`}
    >
      {inWatchlist ? <Eye size={14} weight="fill" /> : <EyeSlash size={14} />}
      {inWatchlist ? "Watchlist" : "Monitorar"}
    </button>
  );
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
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{ticker}</h1>
          <div className="flex items-center gap-3 mt-1 flex-wrap">
            {fiiRow?.short_name && (
              <p className="text-muted-foreground">{fiiRow.short_name}</p>
            )}
            <LivePriceChip ticker={ticker} />
          </div>
          {fiiRow?.segmento && (
            <span className="inline-block mt-1 px-2 py-0.5 bg-muted rounded text-xs">
              {fiiRow.segmento}
            </span>
          )}
        </div>
        <WatchlistToggle ticker={ticker} />
      </div>

      {/* Price chart — instant from Redis cache */}
      <StockPriceChart ticker={ticker} />

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
