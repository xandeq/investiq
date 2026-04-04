"use client";
import { useEffect, useRef, useState } from "react";
import { isLimitError } from "@/lib/api-client";
import {
  startDCFAnalysis,
  startEarningsAnalysis,
  startDividendAnalysis,
  startSectorAnalysis,
} from "../api";
import { useAnalysisPolling } from "./useAnalysisPolling";

interface JobIds {
  dcf: string | null;
  earnings: string | null;
  dividend: string | null;
  sector: string | null;
}

/**
 * Orchestrator hook: fires all 4 analysis jobs in parallel on mount and
 * polls each independently. Uses a ref to prevent StrictMode double-fire.
 */
export function useStockAnalysis(ticker: string) {
  const [jobIds, setJobIds] = useState<JobIds>({
    dcf: null,
    earnings: null,
    dividend: null,
    sector: null,
  });
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const startedForTicker = useRef<string | null>(null);

  useEffect(() => {
    if (!ticker || startedForTicker.current === ticker) return;
    startedForTicker.current = ticker;

    setIsStarting(true);
    setStartError(null);
    setJobIds({ dcf: null, earnings: null, dividend: null, sector: null });

    const run = async () => {
      const results = await Promise.allSettled([
        startDCFAnalysis(ticker),
        startEarningsAnalysis(ticker),
        startDividendAnalysis(ticker),
        startSectorAnalysis(ticker),
      ]);

      const [dcfRes, earningsRes, dividendRes, sectorRes] = results;

      setJobIds({
        dcf: dcfRes.status === "fulfilled" ? dcfRes.value.job_id : null,
        earnings: earningsRes.status === "fulfilled" ? earningsRes.value.job_id : null,
        dividend: dividendRes.status === "fulfilled" ? dividendRes.value.job_id : null,
        sector: sectorRes.status === "fulfilled" ? sectorRes.value.job_id : null,
      });

      // Check if any failure was a quota/limit error
      const firstError = results.find((r) => r.status === "rejected") as
        | PromiseRejectedResult
        | undefined;
      if (firstError) {
        const err = firstError.reason;
        if (isLimitError(err)) {
          setStartError(`LIMIT:${err.message}`);
        } else {
          setStartError(err instanceof Error ? err.message : "Erro ao iniciar análise");
        }
      }

      setIsStarting(false);
    };

    run();
  }, [ticker]);

  const dcf = useAnalysisPolling(jobIds.dcf);
  const earnings = useAnalysisPolling(jobIds.earnings);
  const dividend = useAnalysisPolling(jobIds.dividend);
  const sector = useAnalysisPolling(jobIds.sector);

  return { dcf, earnings, dividend, sector, isStarting, startError };
}
