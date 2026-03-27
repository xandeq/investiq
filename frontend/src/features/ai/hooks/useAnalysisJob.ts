"use client";
import { useQuery } from "@tanstack/react-query";
import { getJob } from "../api";

/**
 * Polls a single AI analysis job every 2 seconds until
 * status becomes "completed" or "failed".
 */
export function useAnalysisJob(jobId: string | null) {
  return useQuery({
    queryKey: ["ai", "job", jobId],
    queryFn: () => getJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 2000;
    },
  });
}
