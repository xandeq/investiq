import { useQuery } from "@tanstack/react-query";
import { getPortfolioEntrySignals, getUniverseEntrySignals } from "../api";
import type { EntrySignal } from "../types";

/**
 * On-demand entry signals for user's owned assets.
 * Backend caches 5 minutes, so we refetch every 4 minutes.
 *
 * @param enabled - set to false to skip the query (e.g. when portfolio is empty)
 */
export function usePortfolioEntrySignals(enabled?: boolean) {
  return useQuery<EntrySignal[]>({
    queryKey: ["advisor", "entry-signals", "portfolio"],
    queryFn: getPortfolioEntrySignals,
    enabled: enabled !== false,
    staleTime: 4 * 60_000,          // 4 min — backend cache is 5 min
    refetchInterval: 4 * 60_000,    // active refetch every 4 min
    retry: false,
  });
}

/**
 * Daily batch entry signals for the screener universe.
 * Refreshed nightly by Celery beat (02h BRT). Returns [] if batch hasn't run.
 *
 * @param enabled - set to false to skip the query
 */
export function useUniverseEntrySignals(enabled?: boolean) {
  return useQuery<EntrySignal[]>({
    queryKey: ["advisor", "entry-signals", "universe"],
    queryFn: getUniverseEntrySignals,
    enabled: enabled !== false,
    staleTime: 60 * 60_000,         // 1 hour — batch refreshes daily
    retry: false,
  });
}
