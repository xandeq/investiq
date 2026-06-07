"use client";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { CryptoAllocation } from "@/features/dashboard/types";

export function useCryptoAllocation() {
  return useQuery<CryptoAllocation>({
    queryKey: ["dashboard", "crypto-allocation"],
    queryFn: () =>
      apiClient<CryptoAllocation>("/dashboard/portfolio/allocation?filter=crypto"),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 10 * 60 * 1000,
  });
}
