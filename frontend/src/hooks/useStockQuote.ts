"use client";
import { useQuery } from "@tanstack/react-query";

export interface StockQuote {
  symbol: string;
  price: string;
  change: string;
  change_pct: string;
  fetched_at: string;
  data_stale: boolean;
}

async function fetchStockQuote(ticker: string): Promise<StockQuote> {
  const res = await fetch(`/api/market-data/quote/${encodeURIComponent(ticker.toUpperCase())}`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Quote fetch failed: ${res.status}`);
  return res.json();
}

export function useStockQuote(ticker: string) {
  return useQuery({
    queryKey: ["market-data", "quote", ticker.toUpperCase()],
    queryFn: () => fetchStockQuote(ticker),
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });
}
