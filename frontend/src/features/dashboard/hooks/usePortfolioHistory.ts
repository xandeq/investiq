"use client";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export type HistoryRange = "1m" | "3m" | "6m" | "1y" | "all";

export interface HistoryPoint {
  date: string;
  total_value: string;
  total_invested: string;
}

interface PortfolioHistoryResponse {
  range: HistoryRange;
  points: HistoryPoint[];
}

export function usePortfolioHistory(range: HistoryRange = "3m") {
  return useQuery<PortfolioHistoryResponse>({
    queryKey: ["dashboard", "portfolio-history", range],
    queryFn: () => apiClient<PortfolioHistoryResponse>(`/dashboard/portfolio-history?range=${range}`),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 10 * 60 * 1000,
  });
}
