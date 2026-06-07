"use client";
import { useQuery } from "@tanstack/react-query";

export type SignalVerdict = "BUY" | "WAIT" | "SKIP";

export interface SignalCurrentSetup {
  pattern: string;
  direction: string;
  entry: number;
  stop: number;
  target: number;
  rr: number;
}

export interface SignalCurrentData {
  ticker: string;
  verdict: SignalVerdict;
  grade: string;
  score: number;
  passed_gates: number;
  total_gates: number;
  setup: SignalCurrentSetup | null;
}

async function fetchSignalCurrent(ticker: string): Promise<SignalCurrentData> {
  const res = await fetch(
    `/api/signals/current?ticker=${encodeURIComponent(ticker.toUpperCase())}`,
    { credentials: "include" }
  );
  if (!res.ok) throw new Error(`Signal current fetch failed: ${res.status}`);
  return res.json();
}

export function useSignalCurrent(ticker: string, enabled = true) {
  return useQuery<SignalCurrentData>({
    queryKey: ["signal-current", ticker.toUpperCase()],
    queryFn: () => fetchSignalCurrent(ticker),
    staleTime: 10 * 60_000, // 10 min — matches evaluate endpoint cache
    retry: false,
    enabled: enabled && ticker.length > 0,
  });
}
