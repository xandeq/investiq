import { apiClient } from "@/lib/api-client";
import type { OpportunityHistoryResponse, RadarReport } from "./types";

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

export async function fetchRadar(force = false): Promise<RadarReport> {
  const qs = force ? "?force=true" : "";
  return apiClient<RadarReport>(`/opportunity-detector/radar${qs}`);
}

export async function triggerRadarRefresh(): Promise<{ status: string; ready_in_seconds: number }> {
  return apiClient<{ status: string; ready_in_seconds: number }>(
    `/opportunity-detector/radar/refresh`,
    { method: "POST" }
  );
}
