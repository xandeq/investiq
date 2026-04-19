import { useQuery } from "@tanstack/react-query";
import { getInbox } from "../api";

/**
 * Action Inbox v1 — ranked decision cards aggregated from 5 existing sources.
 *
 * staleTime: 5min. Auto-refresh every 15min so the dashboard stays close to
 * the celery-beat cadence of the underlying sources (insights/watchlist).
 */
export function useInbox() {
  return useQuery({
    queryKey: ["advisor", "inbox"],
    queryFn: getInbox,
    staleTime: 5 * 60_000,
    refetchInterval: 15 * 60_000,
    retry: false,
  });
}
