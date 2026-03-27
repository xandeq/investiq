"use client";
import { useQuery } from "@tanstack/react-query";
import { getDividends } from "@/features/portfolio/api";

export function useDividends() {
  return useQuery({
    queryKey: ["portfolio", "dividends"],
    queryFn: getDividends,
    staleTime: 5 * 60 * 1000,
  });
}
