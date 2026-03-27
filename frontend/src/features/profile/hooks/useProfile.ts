"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getProfile, upsertProfile } from "@/features/profile/api";
import type { InvestorProfileUpsert } from "@/features/profile/types";

export function useProfile() {
  return useQuery({
    queryKey: ["investor-profile"],
    queryFn: getProfile,
    staleTime: 60_000,
    retry: (failureCount, error: unknown) => {
      // Don't retry 404 — profile just doesn't exist yet
      if (error && typeof error === "object" && "status" in error && (error as { status: number }).status === 404) return false;
      return failureCount < 2;
    },
  });
}

export function useUpsertProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: InvestorProfileUpsert) => upsertProfile(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["investor-profile"] });
    },
  });
}
