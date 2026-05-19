"use client";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export interface MonthlyPoint {
  year: number;
  month: number;
  return_pct: number;
  start_value: string;
  end_value: string;
}

interface MonthlyPerformanceResponse {
  months: MonthlyPoint[];
}

export function useMonthlyPerformance(years = 3) {
  return useQuery<MonthlyPerformanceResponse>({
    queryKey: ["dashboard", "monthly-performance", years],
    queryFn: () =>
      apiClient<MonthlyPerformanceResponse>(
        `/dashboard/monthly-performance?years=${years}`
      ),
    staleTime: 10 * 60 * 1000,
    refetchInterval: 30 * 60 * 1000,
  });
}
