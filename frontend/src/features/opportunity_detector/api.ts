import { apiClient } from "@/lib/api-client";
import type { OpportunityHistoryResponse } from "./types";

export async function getOpportunityHistory(params?: {
  asset_type?: string;
  days?: number;
}): Promise<OpportunityHistoryResponse> {
  const qs = new URLSearchParams();
  if (params?.asset_type) qs.set("asset_type", params.asset_type);
  if (params?.days) qs.set("days", String(params.days));
  const query = qs.toString();
  return apiClient<OpportunityHistoryResponse>(
    `/opportunity-detector/history${query ? `?${query}` : ""}`
  );
}

export async function markAsFollowed(id: string): Promise<{ id: string; followed: boolean }> {
  return apiClient<{ id: string; followed: boolean }>(
    `/opportunity-detector/${id}/follow`,
    { method: "PATCH" }
  );
}

export async function triggerScan(): Promise<{ status: string; tasks: Record<string, string> }> {
  return apiClient<{ status: string; tasks: Record<string, string> }>(
    `/opportunity-detector/scan`,
    { method: "POST" }
  );
}
