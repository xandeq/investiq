"use client";
import { useQuery } from "@tanstack/react-query";

export interface Fundamentals {
  ticker: string;
  pl: string | null;
  pvp: string | null;
  dy: string | null;
  ev_ebitda: string | null;
  fetched_at: string;
  data_stale: boolean;
}

async function fetchFundamentals(ticker: string): Promise<Fundamentals> {
  const res = await fetch(
    `/api/market-data/fundamentals/${encodeURIComponent(ticker.toUpperCase())}`,
    { credentials: "include" },
  );
  if (!res.ok) throw new Error(`Fundamentals fetch failed: ${res.status}`);
  return res.json();
}

export function useFundamentals(ticker: string) {
  return useQuery({
    queryKey: ["market-data", "fundamentals", ticker.toUpperCase()],
    queryFn: () => fetchFundamentals(ticker),
    staleTime: 30 * 60 * 1000,
  });
}
