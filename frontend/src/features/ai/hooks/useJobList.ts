"use client";
import { useQuery } from "@tanstack/react-query";
import { listJobs } from "../api";

/**
 * Fetches the last 10 AI analysis jobs for the current tenant.
 * Cached for 30 seconds — no live polling needed for history.
 */
export function useJobList() {
  return useQuery({
    queryKey: ["ai", "jobs"],
    queryFn: listJobs,
    staleTime: 30_000,
  });
}
