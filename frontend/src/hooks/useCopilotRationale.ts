"use client";
import { useQuery } from "@tanstack/react-query";

export interface CopilotRationaleData {
  ticker: string;
  rationale: string;
  confidence: "alta" | "média" | "baixa";
  cached: boolean;
}

async function fetchCopilotRationale(ticker: string): Promise<CopilotRationaleData> {
  const res = await fetch(`/api/signals/${encodeURIComponent(ticker.toUpperCase())}/rationale`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Rationale fetch failed: ${res.status}`);
  return res.json();
}

export function useCopilotRationale(ticker: string, enabled = true) {
  return useQuery<CopilotRationaleData>({
    queryKey: ["copilot-rationale", ticker.toUpperCase()],
    queryFn: () => fetchCopilotRationale(ticker),
    staleTime: 6 * 60 * 60_000, // 6h — matches backend cache TTL
    retry: false,
    enabled,
  });
}
