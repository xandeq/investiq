"use client";
import { useQuery } from "@tanstack/react-query";
import { listImports } from "../api";

/**
 * Fetches import history for the current user.
 * No polling — history is refreshed on mount and after mutations
 * via queryClient.invalidateQueries(["imports", "history"]).
 */
export function useImportHistory() {
  return useQuery({
    queryKey: ["imports", "history"],
    queryFn: listImports,
  });
}
