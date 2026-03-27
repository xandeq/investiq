"use client";
import { useQuery } from "@tanstack/react-query";
import { getBenchmarks } from "@/features/portfolio/api";

export function useBenchmarks() {
  return useQuery({
    queryKey: ["portfolio", "benchmarks"],
    queryFn: getBenchmarks,
    staleTime: 5 * 60 * 1000,
  });
}
