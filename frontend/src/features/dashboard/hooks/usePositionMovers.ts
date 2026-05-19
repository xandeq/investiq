"use client";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export interface MoverItem {
  ticker: string;
  change_pct: string;
  pnl_impact: string;
  current_price: string;
}

export interface PositionMoversResponse {
  gainers: MoverItem[];
  losers: MoverItem[];
  data_stale: boolean;
}

export function usePositionMovers() {
  return useQuery<PositionMoversResponse>({
    queryKey: ["dashboard", "position-movers"],
    queryFn: () => apiClient<PositionMoversResponse>("/dashboard/position-movers"),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 15 * 60 * 1000,
  });
}
