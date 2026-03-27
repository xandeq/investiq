"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getWatchlist, getWatchlistQuotes, addToWatchlist, removeFromWatchlist, updateWatchlistItem } from "../api";
import type { WatchlistItemCreate, WatchlistItemUpdate } from "../types";

export const useWatchlist = () => useQuery({ queryKey: ["watchlist"], queryFn: getWatchlist, staleTime: 30_000 });
export const useWatchlistQuotes = () => useQuery({ queryKey: ["watchlist", "quotes"], queryFn: getWatchlistQuotes, staleTime: 30_000 });

export function useAddToWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: WatchlistItemCreate) => addToWatchlist(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["watchlist"] }); },
  });
}

export function useRemoveFromWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ticker: string) => removeFromWatchlist(ticker),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["watchlist"] }); },
  });
}

export function useUpdateWatchlistItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ ticker, data }: { ticker: string; data: WatchlistItemUpdate }) =>
      updateWatchlistItem(ticker, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["watchlist"] }); },
  });
}
