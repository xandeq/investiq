import { apiClient } from "@/lib/api-client";
import type { AnalysisJobStatus } from "@/features/analysis/types";

export async function startFIIAnalysis(ticker: string): Promise<AnalysisJobStatus> {
  return apiClient<AnalysisJobStatus>(
    `/analysis/fii/${encodeURIComponent(ticker.toUpperCase())}`,
    { method: "POST" }
  );
}
