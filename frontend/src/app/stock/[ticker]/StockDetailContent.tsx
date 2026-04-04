"use client";
import Link from "next/link";
import { useStockAnalysis } from "@/features/analysis/hooks/useStockAnalysis";
import { AnalysisDisclaimer } from "@/features/analysis/components/AnalysisDisclaimer";
import { DCFSection } from "@/features/analysis/components/DCFSection";
import { EarningsSection } from "@/features/analysis/components/EarningsSection";
import { DividendSection } from "@/features/analysis/components/DividendSection";
import { SectorSection } from "@/features/analysis/components/SectorSection";
import { NarrativeSection } from "@/features/analysis/components/NarrativeSection";
import { PremiumGate } from "@/features/ai/components/PremiumGate";

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

      <div>
        <h1 className="text-2xl font-bold">{ticker}</h1>
        <p className="text-muted-foreground">Análise Fundamentalista</p>
      </div>

      {/* CVM Disclaimer — always first */}
      <AnalysisDisclaimer dataTimestamp={dataTimestamp} />

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
