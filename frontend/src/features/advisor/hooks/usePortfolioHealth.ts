import { useQuery } from "@tanstack/react-query";
import { getPortfolioHealth } from "../api";

export function usePortfolioHealth() {
  return useQuery({
    queryKey: ["advisor", "health"],
    queryFn: getPortfolioHealth,
    staleTime: 5 * 60_000,  // 5 min — health is computed on-demand, no real-time needed
    retry: false,
  });
}
