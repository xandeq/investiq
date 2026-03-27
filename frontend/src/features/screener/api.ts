import { apiClient } from "@/lib/api-client";
import { ScreenerRun } from "./types";

export async function startScreener(
  sector_filter?: string | null,
  custom_notes?: string | null
): Promise<ScreenerRun> {
  return apiClient<ScreenerRun>("/screener/analyze", {
    method: "POST",
    body: JSON.stringify({ sector_filter: sector_filter ?? null, custom_notes: custom_notes ?? null }),
  });
}

export async function getScreenerRun(runId: string): Promise<ScreenerRun> {
  return apiClient<ScreenerRun>(`/screener/jobs/${encodeURIComponent(runId)}`);
}

export async function getScreenerHistory(): Promise<ScreenerRun[]> {
  return apiClient<ScreenerRun[]>("/screener/history");
}
