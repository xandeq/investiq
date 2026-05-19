import { useQuery } from "@tanstack/react-query";
import { searchFunds } from "../api";

export function useFundSearch(q: string) {
  return useQuery({
    queryKey: ["fund-search", q],
    queryFn: () => searchFunds(q),
    enabled: q.trim().length >= 2,
    staleTime: 5 * 60 * 1000,
  });
}
