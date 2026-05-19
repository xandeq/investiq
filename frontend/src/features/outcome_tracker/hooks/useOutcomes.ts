import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  closeOutcome,
  createOutcome,
  fetchOutcomes,
} from "../api";
import type {
  OutcomeClosePayload,
  OutcomeCreatePayload,
} from "../types";

const OUTCOMES_KEY = ["outcomes"] as const;

export function useOutcomes(status?: "open" | "closed" | "stopped") {
  return useQuery({
    queryKey: [...OUTCOMES_KEY, status ?? "all"],
    queryFn: () => fetchOutcomes(status),
    staleTime: 30_000,
  });
}

export function useCreateOutcome() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: OutcomeCreatePayload) => createOutcome(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: OUTCOMES_KEY });
      qc.invalidateQueries({ queryKey: ["outcome-stats"] });
      qc.invalidateQueries({ queryKey: ["outcome-expectancy"] });
    },
  });
}

export function useCloseOutcome() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: OutcomeClosePayload }) =>
      closeOutcome(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: OUTCOMES_KEY });
      qc.invalidateQueries({ queryKey: ["outcome-stats"] });
      qc.invalidateQueries({ queryKey: ["outcome-expectancy"] });
    },
  });
}
