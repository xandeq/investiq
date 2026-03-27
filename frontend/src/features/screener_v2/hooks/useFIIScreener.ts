"use client";
import { useQuery } from "@tanstack/react-query";
import { getFIIScreener } from "../api";
import type { FIIScreenerParams } from "../types";

export function useFIIScreener(params: FIIScreenerParams) {
  return useQuery({
    queryKey: ["screener-v2", "fiis", params],
    queryFn: () => getFIIScreener(params),
    staleTime: 60_000,
    placeholderData: (prev) => prev,
  });
}
