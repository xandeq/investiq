import { useQuery } from "@tanstack/react-query";
import { fetchOutcomeStats } from "../api";

export function useOutcomeStats() {
  return useQuery({
    queryKey: ["outcome-stats"],
    queryFn: fetchOutcomeStats,
    staleTime: 60_000,
  });
}
