/**
 * Typed fetch wrappers for all /ai endpoints.
 * Uses the shared apiClient with credentials: "include" for cookie-based auth.
 */
import { apiClient } from "@/lib/api-client";
import { AnalysisJob } from "./types";

export async function requestAssetAnalysis(ticker: string): Promise<AnalysisJob> {
  return apiClient<AnalysisJob>(`/ai/analyze/${encodeURIComponent(ticker.toUpperCase())}`, {
    method: "POST",
  });
}

export async function requestMacroAnalysis(): Promise<AnalysisJob> {
  return apiClient<AnalysisJob>("/ai/analyze/macro", {
    method: "POST",
  });
}

export async function requestPortfolioAnalysis(): Promise<AnalysisJob> {
  return apiClient<AnalysisJob>("/ai/analyze/portfolio", {
    method: "POST",
  });
}

export async function getJob(jobId: string): Promise<AnalysisJob> {
  return apiClient<AnalysisJob>(`/ai/jobs/${encodeURIComponent(jobId)}`);
}

export async function listJobs(): Promise<AnalysisJob[]> {
  return apiClient<AnalysisJob[]>("/ai/jobs");
}
