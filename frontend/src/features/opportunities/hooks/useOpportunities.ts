"use client";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { OpportunitiesResponse } from "../types";

const REFETCH_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

export function useOpportunities(limit = 20) {
  return useQuery<OpportunitiesResponse>({
    queryKey: ["opportunities", limit],
    queryFn: () =>
      apiClient<OpportunitiesResponse>(`/opportunities?limit=${limit}`),
    staleTime: REFETCH_INTERVAL_MS,
    refetchInterval: REFETCH_INTERVAL_MS,
    refetchIntervalInBackground: false,
  });
}
