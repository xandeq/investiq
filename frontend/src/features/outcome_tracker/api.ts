import { apiClient } from "@/lib/api-client";
import type {
  ExpectancyResponse,
  OutcomeClosePayload,
  OutcomeCreatePayload,
  OutcomeListResponse,
  OutcomeStats,
  SignalOutcome,
} from "./types";

export async function fetchOutcomes(
  status?: "open" | "closed" | "stopped",
): Promise<OutcomeListResponse> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiClient<OutcomeListResponse>(`/outcomes${qs}`);
}

export async function createOutcome(
  payload: OutcomeCreatePayload,
): Promise<SignalOutcome> {
  return apiClient<SignalOutcome>("/outcomes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function closeOutcome(
  id: string,
  payload: OutcomeClosePayload,
): Promise<SignalOutcome> {
  return apiClient<SignalOutcome>(`/outcomes/${id}/close`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function fetchOutcomeStats(): Promise<OutcomeStats> {
  return apiClient<OutcomeStats>("/outcomes/stats");
}

export async function fetchExpectancy(): Promise<ExpectancyResponse> {
  return apiClient<ExpectancyResponse>("/outcomes/expectancy");
}
