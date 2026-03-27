"use client";
import { useQuery } from "@tanstack/react-query";
import { getImportJob } from "../api";

/**
 * Polls a single import job every 2 seconds until status becomes
 * "completed", "failed", "confirmed", or "cancelled".
 * Mirrors the useAnalysisJob pattern from features/ai/hooks/useAnalysisJob.ts.
 */
export function useImportJob(jobId: string | null) {
  return useQuery({
    queryKey: ["imports", "job", jobId],
    queryFn: () => getImportJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (
        status === "completed" ||
        status === "failed" ||
        status === "confirmed" ||
        status === "cancelled"
      ) {
        return false;
      }
      return 2000;
    },
  });
}
