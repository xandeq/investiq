"use client";
import { useQuery } from "@tanstack/react-query";
import { getDashboardSummary } from "@/features/dashboard/api";

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: getDashboardSummary,
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });
}
