import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export type HistoryRange = "1m" | "3m" | "6m" | "1y" | "all";

export interface HistoryPoint {
  date: string;
  total_value: string;
  total_invested: string;
}

export interface PortfolioHistoryResponse {
  range: HistoryRange;
  points: HistoryPoint[];
}

export function usePortfolioHistory(range: HistoryRange = "3m") {
  return useQuery<PortfolioHistoryResponse>({
    queryKey: ["portfolio", "history", range],
    queryFn: () => apiClient(`/dashboard/portfolio-history?range=${range}`),
    staleTime: 15 * 60_000, // 15 min — updated nightly by Celery, no need to refetch often
    retry: false,
  });
}
