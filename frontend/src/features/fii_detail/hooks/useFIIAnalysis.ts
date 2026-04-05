"use client";
import { useState } from "react";
import { startFIIAnalysis } from "../api";
import { useAnalysisPolling } from "@/features/analysis/hooks/useAnalysisPolling";

export function useFIIAnalysis(ticker: string) {
  const [jobId, setJobId] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  const triggerAnalysis = async () => {
    setIsStarting(true);
    setStartError(null);
    try {
      const { job_id } = await startFIIAnalysis(ticker);
      setJobId(job_id);
    } catch (err) {
      setStartError(err instanceof Error ? err.message : "Erro ao iniciar analise");
    } finally {
      setIsStarting(false);
    }
  };

  const polling = useAnalysisPolling(jobId);

  return { triggerAnalysis, isStarting, startError, polling, jobId };
}
