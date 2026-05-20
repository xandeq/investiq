"use client";
import { useQuery } from "@tanstack/react-query";

export interface SentimentData {
  ticker: string;
  score: number | null;
  mention_count: number;
  sources: { source: string; score: number; mention_count: number }[];
}

async function fetchSentiment(ticker: string): Promise<SentimentData> {
  const res = await fetch(`/api/briefing/sentiment?ticker=${encodeURIComponent(ticker.toUpperCase())}`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Sentiment fetch failed: ${res.status}`);
  return res.json();
}

export function useSentiment(ticker: string) {
  return useQuery<SentimentData>({
    queryKey: ["sentiment", ticker.toUpperCase()],
    queryFn: () => fetchSentiment(ticker),
    staleTime: 15 * 60_000,
    retry: false,
  });
}
