"use client";
import { useQuery } from "@tanstack/react-query";

export interface HistoricalPoint {
  date: number; // Unix epoch (seconds)
  open: string;
  high: string;
  low: string;
  close: string;
  volume: number;
}

export interface Historical {
  ticker: string;
  points: HistoricalPoint[];
  fetched_at: string;
  data_stale: boolean;
}

async function fetchHistorical(ticker: string): Promise<Historical> {
  const res = await fetch(
    `/api/market-data/historical/${encodeURIComponent(ticker.toUpperCase())}`,
    { credentials: "include" },
  );
  if (!res.ok) throw new Error(`Historical fetch failed: ${res.status}`);
  return res.json();
}

export function useHistorical(ticker: string) {
  return useQuery({
    queryKey: ["market-data", "historical", ticker.toUpperCase()],
    queryFn: () => fetchHistorical(ticker),
    staleTime: 60 * 60 * 1000,
  });
}
