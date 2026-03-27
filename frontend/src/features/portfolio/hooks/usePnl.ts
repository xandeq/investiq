"use client";
import { useQuery } from "@tanstack/react-query";
import { getPnl } from "@/features/portfolio/api";

export function usePnl() {
  return useQuery({
    queryKey: ["portfolio", "pnl"],
    queryFn: getPnl,
    staleTime: 60 * 1000,
  });
}
