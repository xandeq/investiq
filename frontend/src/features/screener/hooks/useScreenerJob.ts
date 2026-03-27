"use client";
import { useQuery } from "@tanstack/react-query";
import { getScreenerRun, getScreenerHistory } from "../api";

export function useScreenerJob(runId: string | null) {
  return useQuery({
    queryKey: ["screener", "job", runId],
    queryFn: () => getScreenerRun(runId!),
    enabled: !!runId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 2000;
    },
  });
}

export function useScreenerHistory() {
  return useQuery({
    queryKey: ["screener", "history"],
    queryFn: getScreenerHistory,
    staleTime: 30_000,
  });
}
