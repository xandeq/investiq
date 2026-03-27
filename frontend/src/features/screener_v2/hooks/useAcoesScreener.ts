"use client";
import { useQuery } from "@tanstack/react-query";
import { getAcoesScreener } from "../api";
import type { AcaoScreenerParams } from "../types";

export function useAcoesScreener(params: AcaoScreenerParams) {
  return useQuery({
    queryKey: ["screener-v2", "acoes", params],
    queryFn: () => getAcoesScreener(params),
    staleTime: 60_000,
    placeholderData: (prev) => prev,
  });
}
