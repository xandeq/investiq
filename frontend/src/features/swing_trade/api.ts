import { apiClient } from "@/lib/api-client";
import type {
  CopilotResponse,
  OperationClosePayload,
  OperationCreatePayload,
  OperationListResponse,
  SwingOperation,
  SwingSignalsResponse,
} from "./types";

// ---------------------------------------------------------------------------
// GET /swing-trade/signals — portfolio + radar signals (Redis-backed)
// ---------------------------------------------------------------------------

export async function fetchSignals(): Promise<SwingSignalsResponse> {
  return apiClient<SwingSignalsResponse>("/swing-trade/signals");
}

// ---------------------------------------------------------------------------
// GET /swing-trade/operations — list tenant operations (enriched read-side)
// ---------------------------------------------------------------------------

export async function fetchOperations(
  statusFilter?: "open" | "closed" | "stopped",
): Promise<OperationListResponse> {
  const qs = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : "";
  return apiClient<OperationListResponse>(`/swing-trade/operations${qs}`);
}

// ---------------------------------------------------------------------------
// POST /swing-trade/operations — create manual operation
// ---------------------------------------------------------------------------

export async function createOperation(
  payload: OperationCreatePayload,
): Promise<SwingOperation> {
  return apiClient<SwingOperation>("/swing-trade/operations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ---------------------------------------------------------------------------
// PATCH /swing-trade/operations/{id}/close — close open operation
// ---------------------------------------------------------------------------

export async function closeOperation(
  id: string,
  payload: OperationClosePayload,
): Promise<SwingOperation> {
  return apiClient<SwingOperation>(`/swing-trade/operations/${id}/close`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

// ---------------------------------------------------------------------------
// DELETE /swing-trade/operations/{id} — soft delete
// ---------------------------------------------------------------------------

export async function deleteOperation(id: string): Promise<void> {
  return apiClient<void>(`/swing-trade/operations/${id}`, {
    method: "DELETE",
  });
}

// ---------------------------------------------------------------------------
// GET /swing-trade/copilot — AI-curated picks ready to execute
// ---------------------------------------------------------------------------

export async function fetchCopilot(force = false): Promise<CopilotResponse> {
  const qs = force ? "?force=true" : "";
  return apiClient<CopilotResponse>(`/swing-trade/copilot${qs}`);
}
