"use client";
import { useQuery } from "@tanstack/react-query";
import { getFixedIncomeCatalog, getTesouroRates, getMacroRates } from "../api";

export function useFixedIncomeCatalog() {
  return useQuery({
    queryKey: ["renda-fixa", "catalog"],
    queryFn: getFixedIncomeCatalog,
    staleTime: 5 * 60_000,
  });
}

export function useTesouroRates() {
  return useQuery({
    queryKey: ["renda-fixa", "tesouro"],
    queryFn: getTesouroRates,
    staleTime: 5 * 60_000,
  });
}

export function useMacroRates() {
  return useQuery({
    queryKey: ["renda-fixa", "macro-rates"],
    queryFn: getMacroRates,
    staleTime: 60 * 60_000,  // 1h — macro rates rarely change (per D-10)
  });
}
