import { useQuery } from "@tanstack/react-query";
import { getCashParking } from "../api";

export function useCashParking() {
  return useQuery({
    queryKey: ["advisor", "cash-parking"],
    queryFn: getCashParking,
    staleTime: 5 * 60_000,
    retry: false,
  });
}
