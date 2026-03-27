import { apiClient } from "@/lib/api-client";
import type {
  PositionResponse,
  PnLResponse,
  DividendResponse,
  BenchmarkResponse,
  TransactionResponse,
  TransactionCreate,
  TransactionUpdate,
} from "@/features/portfolio/types";

export async function getPositions(): Promise<PositionResponse[]> {
  return apiClient<PositionResponse[]>("/portfolio/positions");
}

export async function getPnl(): Promise<PnLResponse> {
  return apiClient<PnLResponse>("/portfolio/pnl");
}

export async function getDividends(): Promise<DividendResponse[]> {
  return apiClient<DividendResponse[]>("/portfolio/dividends");
}

export async function getBenchmarks(): Promise<BenchmarkResponse> {
  return apiClient<BenchmarkResponse>("/portfolio/benchmarks");
}

export interface TransactionFilters {
  ticker?: string;
  asset_class?: string;
  transaction_type?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

export async function getTransactions(filters?: TransactionFilters): Promise<TransactionResponse[]> {
  const params = new URLSearchParams();
  if (filters?.ticker) params.set("ticker", filters.ticker);
  if (filters?.asset_class) params.set("asset_class", filters.asset_class);
  if (filters?.transaction_type) params.set("transaction_type", filters.transaction_type);
  if (filters?.date_from) params.set("date_from", filters.date_from);
  if (filters?.date_to) params.set("date_to", filters.date_to);
  if (filters?.limit) params.set("limit", String(filters.limit));
  if (filters?.offset) params.set("offset", String(filters.offset));
  const qs = params.toString();
  return apiClient<TransactionResponse[]>(`/portfolio/transactions${qs ? `?${qs}` : ""}`);
}

export async function createTransaction(data: TransactionCreate): Promise<TransactionResponse> {
  return apiClient<TransactionResponse>("/portfolio/transactions", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateTransaction(id: string, data: TransactionUpdate): Promise<TransactionResponse> {
  return apiClient<TransactionResponse>(`/portfolio/transactions/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteTransaction(id: string): Promise<void> {
  return apiClient<void>(`/portfolio/transactions/${id}`, { method: "DELETE" });
}

export async function bulkDeleteTransactions(ids: string[]): Promise<{ deleted: number }> {
  return apiClient<{ deleted: number }>("/portfolio/transactions/bulk", {
    method: "DELETE",
    body: JSON.stringify({ ids }),
  });
}
