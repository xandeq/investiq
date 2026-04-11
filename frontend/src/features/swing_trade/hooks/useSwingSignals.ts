import { useQuery } from "@tanstack/react-query";
import { fetchSignals } from "../api";

/**
 * React Query hook for GET /swing-trade/signals.
 *
 * Uses a 2-minute staleTime because the underlying Redis cache is refreshed
 * by the market data Celery beat every few minutes. A shorter stale window
 * avoids hammering the backend on tab switches.
 */
export function useSwingSignals() {
  return useQuery({
    queryKey: ["swing-trade-signals"],
    queryFn: () => fetchSignals(),
    staleTime: 1000 * 60 * 2, // 2 min
    retry: 1,
  });
}
