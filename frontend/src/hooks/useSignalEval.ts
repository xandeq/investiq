"use client";
import { useQuery } from "@tanstack/react-query";

export interface GateResult {
  gate_name: string;
  passed: boolean;
  value: unknown;
  threshold: unknown;
  reason: string;
}

export interface SignalEvalData {
  ticker: string;
  grade: string;
  score: number;
  passed_gates: number;
  total_gates: number;
  is_a_plus: boolean;
  setup: {
    pattern: string;
    direction: string;
    entry: number;
    stop: number;
    target_1: number;
    rr: number;
  } | null;
  gates: GateResult[];
}

async function fetchSignalEval(ticker: string): Promise<SignalEvalData> {
  const res = await fetch(`/api/signals/${encodeURIComponent(ticker.toUpperCase())}/evaluate`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Signal eval failed: ${res.status}`);
  return res.json();
}

export function useSignalEval(ticker: string, enabled = true) {
  return useQuery<SignalEvalData>({
    queryKey: ["signal-eval", ticker.toUpperCase()],
    queryFn: () => fetchSignalEval(ticker),
    staleTime: 10 * 60_000,
    retry: false,
    enabled,
  });
}
