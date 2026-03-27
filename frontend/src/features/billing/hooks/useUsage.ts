"use client";
import { useQuery } from "@tanstack/react-query";
import { getUsage, UsageResponse } from "../api";

export function useUsage() {
  const { data, isLoading } = useQuery<UsageResponse>({
    queryKey: ["billing-usage"],
    queryFn: getUsage,
    staleTime: 60_000,
  });

  return { usage: data, isLoading };
}
