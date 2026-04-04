import { useQuery } from "@tanstack/react-query";
import { getFIIScreenerRanked } from "../api";
import type { FIIScoredResponse } from "../types";

export function useFIIScoredScreener() {
  return useQuery<FIIScoredResponse>({
    queryKey: ["fii-screener-ranked"],
    queryFn: getFIIScreenerRanked,
    staleTime: 1000 * 60 * 60, // 1h — data refreshed nightly
  });
}
