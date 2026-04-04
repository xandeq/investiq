"use client";
import { useQuery } from "@tanstack/react-query";
import { getAnalysisJob } from "../api";

/**
 * Polls a single analysis job every 3 seconds until status becomes
 * "completed" or "failed". Longer interval than the wizard (2s) because
 * analysis jobs run for 15-60 seconds.
 */
export function useAnalysisPolling(jobId: string | null) {
  return useQuery({
    queryKey: ["analysis", "job", jobId],
    queryFn: () => getAnalysisJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 3000;
    },
  });
}
