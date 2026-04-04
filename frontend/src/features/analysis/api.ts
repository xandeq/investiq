/**
 * Typed fetch wrappers for the /analysis/* endpoints.
 */
import { apiClient } from "@/lib/api-client";
import { AnalysisJobStatus, AnalysisResponse } from "./types";

export async function startDCFAnalysis(ticker: string): Promise<AnalysisJobStatus> {
  return apiClient<AnalysisJobStatus>("/analysis/dcf", {
    method: "POST",
    body: JSON.stringify({ ticker }),
  });
}

export async function startEarningsAnalysis(ticker: string): Promise<AnalysisJobStatus> {
  return apiClient<AnalysisJobStatus>("/analysis/earnings", {
    method: "POST",
    body: JSON.stringify({ ticker }),
  });
}

export async function startDividendAnalysis(ticker: string): Promise<AnalysisJobStatus> {
  return apiClient<AnalysisJobStatus>("/analysis/dividend", {
    method: "POST",
    body: JSON.stringify({ ticker }),
  });
}

export async function startSectorAnalysis(ticker: string): Promise<AnalysisJobStatus> {
  return apiClient<AnalysisJobStatus>("/analysis/sector", {
    method: "POST",
    body: JSON.stringify({ ticker }),
  });
}

export async function getAnalysisJob(jobId: string): Promise<AnalysisResponse> {
  return apiClient<AnalysisResponse>(`/analysis/${encodeURIComponent(jobId)}`);
}
