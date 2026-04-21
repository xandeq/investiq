import { useQuery } from "@tanstack/react-query";
import { getSmartScreener } from "../api";
import type { ComplementaryAsset } from "../types";

export type { ComplementaryAsset };

/**
 * Fetch complementary assets from GET /advisor/screener.
 *
 * Returns tickers whose sectors are NOT in the user's portfolio —
 * ranked by relevance to identified health gaps (DY-weighted, entry price).
 *
 * @param enabled - Set to false to skip the query (e.g. user has no portfolio yet).
 */
export function useSmartScreener(enabled = true) {
  return useQuery<ComplementaryAsset[]>({
    queryKey: ["advisor", "smart-screener"],
    queryFn: () => getSmartScreener(100),
    enabled,
    staleTime: 10 * 60_000, // 10 minutes — data is pre-calculated nightly
    retry: false,
  });
}
