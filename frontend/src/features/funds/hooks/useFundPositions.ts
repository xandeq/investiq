import { useQuery } from "@tanstack/react-query";
import { getFundPositions } from "../api";

export function useFundPositions() {
  return useQuery({
    queryKey: ["fund-positions"],
    queryFn: getFundPositions,
    staleTime: 60 * 1000,
  });
}
