import { apiClient } from "@/lib/api-client";
import type { WatchlistItem, WatchlistQuote, WatchlistItemCreate, WatchlistItemUpdate } from "./types";

export const getWatchlist = () => apiClient<WatchlistItem[]>("/watchlist");
export const getWatchlistQuotes = () => apiClient<WatchlistQuote[]>("/watchlist/quotes");
export const addToWatchlist = (data: WatchlistItemCreate) =>
  apiClient<WatchlistItem>("/watchlist", { method: "POST", body: JSON.stringify(data) });
export const removeFromWatchlist = (ticker: string) =>
  apiClient<void>(`/watchlist/${encodeURIComponent(ticker)}`, { method: "DELETE" });
export const updateWatchlistItem = (ticker: string, data: WatchlistItemUpdate) =>
  apiClient<WatchlistItem>(`/watchlist/${encodeURIComponent(ticker)}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
