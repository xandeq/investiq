import { useQuery } from "@tanstack/react-query";
import { getOpportunityHistory } from "../api";

export function useOpportunityHistory(filters: {
  asset_type?: string;
  days?: number;
}) {
  return useQuery({
    queryKey: ["opportunity-history", filters],
    queryFn: () => getOpportunityHistory(filters),
    staleTime: 1000 * 60 * 5, // 5 min
  });
}
