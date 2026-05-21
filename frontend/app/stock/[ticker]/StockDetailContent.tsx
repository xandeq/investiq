"use client";
import Link from "next/link";
import { Eye, EyeSlash } from "@phosphor-icons/react";
import { useStockAnalysis } from "@/features/analysis/hooks/useStockAnalysis";
import { AnalysisDisclaimer } from "@/features/analysis/components/AnalysisDisclaimer";
import { DCFSection } from "@/features/analysis/components/DCFSection";
import { EarningsSection } from "@/features/analysis/components/EarningsSection";
import { DividendSection } from "@/features/analysis/components/DividendSection";
import { SectorSection } from "@/features/analysis/components/SectorSection";
import { NarrativeSection } from "@/features/analysis/components/NarrativeSection";
import { PremiumGate } from "@/features/ai/components/PremiumGate";
import { useWatchlist, useAddToWatchlist, useRemoveFromWatchlist } from "@/features/watchlist/hooks/useWatchlist";
import { useStockQuote } from "@/hooks/useStockQuote";
import { useFundamentals } from "@/hooks/useFundamentals";
import { StockPriceChart } from "./StockPriceChart";
import { SentimentChip } from "@/features/analysis/components/SentimentChip";
import { SignalEvalCard } from "@/features/analysis/components/SignalEvalCard";
import { CopilotPickCard } from "@/features/analysis/components/CopilotPickCard";

interface Props {
  ticker: string;
}

function extractNarrative(
  result: Record<string, unknown> | null | undefined,
  type: string
): { type: string; text: string } | null {
  if (!result) return null;
  const text = result.narrative;
  if (typeof text !== "string" || !text) return null;
  return { type, text };
}

function earliestTimestamp(timestamps: (string | undefined)[]): string | undefined {
  const valid = timestamps.filter(Boolean) as string[];
  if (valid.length === 0) return undefined;
  return valid.sort()[0];
}

function FundamentalsRow({ ticker }: { ticker: string }) {
  const { data: f } = useFundamentals(ticker);
  if (!f || f.data_stale) return null;

  const items = [
    { label: "P/L", value: f.pl ? parseFloat(f.pl).toFixed(1) : null },
    { label: "P/VP", value: f.pvp ? parseFloat(f.pvp).toFixed(2) : null },
    { label: "DY", value: f.dy ? `${parseFloat(f.dy).toFixed(1)}%` : null },
    { label: "EV/EBITDA", value: f.ev_ebitda ? parseFloat(f.ev_ebitda).toFixed(1) : null },
  ].filter((item) => item.value !== null);

  if (items.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 mt-3">
      {items.map((item) => (
        <div
          key={item.label}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-zinc-50 border border-zinc-200 text-xs"
        >
          <span className="text-zinc-400 font-medium">{item.label}</span>
          <span className="font-semibold text-zinc-800 tabular-nums">{item.value}</span>
        </div>
      ))}
    </div>
  );
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

export function StockDetailContent({ ticker }: Props) {
  const { dcf, earnings, dividend, sector, isStarting, startError } =
    useStockAnalysis(ticker);

  const isQuotaError = startError?.startsWith("LIMIT:");

  // Collect narratives from completed results
  const narratives = [
    extractNarrative(dcf.data?.result, "dcf"),
    extractNarrative(earnings.data?.result, "earnings"),
    extractNarrative(dividend.data?.result, "dividend"),
    extractNarrative(sector.data?.result, "sector"),
  ].filter(Boolean) as { type: string; text: string }[];

  // Use earliest data_timestamp from any completed result
  const dataTimestamp = earliestTimestamp([
    dcf.data?.data_metadata?.data_timestamp,
    earnings.data?.data_metadata?.data_timestamp,
    dividend.data?.data_metadata?.data_timestamp,
    sector.data?.data_metadata?.data_timestamp,
  ]);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href="/"
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          ← Voltar
        </Link>
      </div>

      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{ticker}</h1>
          <div className="flex items-center gap-3 mt-1 flex-wrap">
            <p className="text-muted-foreground">Análise Fundamentalista</p>
            <LivePriceChip ticker={ticker} />
            <SentimentChip ticker={ticker} />
          </div>
          <FundamentalsRow ticker={ticker} />
        </div>
        <WatchlistToggle ticker={ticker} />
      </div>

      {/* CVM Disclaimer — always first */}
      <AnalysisDisclaimer dataTimestamp={dataTimestamp} />

      {/* Price chart — instant from Redis cache */}
      <StockPriceChart ticker={ticker} />

      {/* Signal evaluation — 10-gate technical analysis */}
      <SignalEvalCard ticker={ticker} />

      {/* Copilot synthesis — composes signal eval + sentiment */}
      <CopilotPickCard ticker={ticker} />

      {/* Quota / start error */}
      {isQuotaError && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          Limite de análises atingido.{" "}
          <Link href="/planos" className="font-medium underline">
            Faça upgrade para continuar.
          </Link>
        </div>
      )}

      {isStarting && (
        <p className="text-sm text-muted-foreground animate-pulse">
          Iniciando análises...
        </p>
      )}

      {/* Analysis sections wrapped in PremiumGate */}
      <PremiumGate>
        <div className="space-y-4">
          <DCFSection data={dcf.data} isLoading={dcf.isLoading} />
          <EarningsSection data={earnings.data} isLoading={earnings.isLoading} />
          <DividendSection data={dividend.data} isLoading={dividend.isLoading} />
          <SectorSection data={sector.data} isLoading={sector.isLoading} />

          {narratives.length > 0 && <NarrativeSection narratives={narratives} />}
        </div>
      </PremiumGate>
    </div>
  );
}
