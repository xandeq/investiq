import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  closeOperation,
  createOperation,
  deleteOperation,
  fetchOperations,
} from "../api";
import type {
  OperationClosePayload,
  OperationCreatePayload,
} from "../types";

const OPERATIONS_QUERY_KEY = ["swing-trade-operations"] as const;

/**
 * React Query hook wrapping GET /swing-trade/operations plus the three
 * mutations (create / close / delete). Mutations automatically invalidate
 * the list query so the UI refetches after each change.
 *
 * Also invalidates the signals query on close/create since closing a
 * position may change the portfolio composition the radar considers.
 */
export function useSwingOperations(
  statusFilter?: "open" | "closed" | "stopped",
) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: [...OPERATIONS_QUERY_KEY, statusFilter ?? "all"],
    queryFn: () => fetchOperations(statusFilter),
    staleTime: 1000 * 60 * 2, // 2 min
    retry: 1,
  });

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: OPERATIONS_QUERY_KEY });
    queryClient.invalidateQueries({ queryKey: ["swing-trade-signals"] });
  };

  const createMutation = useMutation({
    mutationFn: (payload: OperationCreatePayload) => createOperation(payload),
    onSuccess: invalidateAll,
  });

  const closeMutation = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: OperationClosePayload;
    }) => closeOperation(id, payload),
    onSuccess: invalidateAll,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteOperation(id),
    onSuccess: invalidateAll,
  });

  return {
    operations: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    createOp: createMutation.mutateAsync,
    createOpPending: createMutation.isPending,
    createOpError: createMutation.error,
    closeOp: closeMutation.mutateAsync,
    closeOpPending: closeMutation.isPending,
    deleteOp: deleteMutation.mutateAsync,
    deleteOpPending: deleteMutation.isPending,
  };
}
