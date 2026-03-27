"use client";
import { useQuery } from "@tanstack/react-query";
import { getPositions } from "@/features/portfolio/api";

export function usePositions() {
  return useQuery({
    queryKey: ["portfolio", "positions"],
    queryFn: getPositions,
    staleTime: 60 * 1000,
  });
}
