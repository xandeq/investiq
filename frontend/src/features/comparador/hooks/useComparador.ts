"use client";
import { useQuery } from "@tanstack/react-query";
import { getComparador } from "../api";
import type { PrazoLabel } from "../types";

export function useComparador(prazo: PrazoLabel, valor?: number) {
  return useQuery({
    queryKey: ["comparador", prazo, valor],
    queryFn: () => getComparador(prazo, valor),
    staleTime: 5 * 60_000,
  });
}
