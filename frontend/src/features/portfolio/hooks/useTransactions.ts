"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getTransactions,
  createTransaction,
  updateTransaction,
  deleteTransaction,
  bulkDeleteTransactions,
  type TransactionFilters,
} from "@/features/portfolio/api";
import type { TransactionCreate, TransactionUpdate } from "@/features/portfolio/types";

export function useTransactions(filters?: TransactionFilters) {
  return useQuery({
    queryKey: ["transactions", filters],
    queryFn: () => getTransactions(filters),
    staleTime: 30_000,
  });
}

function invalidatePortfolioQueries(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["transactions"] });
  qc.invalidateQueries({ queryKey: ["dashboard"] });
  // prefix match covers ["portfolio","positions"], ["portfolio","pnl"], ["portfolio","dividends"], etc.
  qc.invalidateQueries({ queryKey: ["portfolio"] });
  // explicit keys for hooks that don't nest under "portfolio"
  qc.invalidateQueries({ queryKey: ["dividend-income"] });
  qc.invalidateQueries({ queryKey: ["dividend-calendar"] });
}

export function useCreateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TransactionCreate) => createTransaction(data),
    onSuccess: () => invalidatePortfolioQueries(qc),
  });
}

export function useUpdateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: TransactionUpdate }) =>
      updateTransaction(id, data),
    onSuccess: () => invalidatePortfolioQueries(qc),
  });
}

export function useDeleteTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteTransaction(id),
    onSuccess: () => invalidatePortfolioQueries(qc),
  });
}

export function useBulkDeleteTransactions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ids: string[]) => bulkDeleteTransactions(ids),
    onSuccess: () => invalidatePortfolioQueries(qc),
  });
}
