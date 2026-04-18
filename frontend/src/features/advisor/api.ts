import { apiClient } from "@/lib/api-client";
import type {
  AdvisorJobResponse,
  AdvisorStartResponse,
  ComplementaryAsset,
  PortfolioHealth,
} from "./types";

export async function getPortfolioHealth(): Promise<PortfolioHealth> {
  return apiClient<PortfolioHealth>("/advisor/health");
}

export async function refreshPortfolioHealth(): Promise<PortfolioHealth> {
  return apiClient<PortfolioHealth>("/advisor/health/refresh", { method: "POST" });
}

export async function startAdvisorAnalysis(): Promise<AdvisorStartResponse> {
  return apiClient<AdvisorStartResponse>("/advisor/analyze", { method: "POST" });
}

export async function getAdvisorJob(jobId: string): Promise<AdvisorJobResponse> {
  return apiClient<AdvisorJobResponse>(`/advisor/${encodeURIComponent(jobId)}`);
}

export async function getSmartScreener(limit = 100): Promise<ComplementaryAsset[]> {
  return apiClient<ComplementaryAsset[]>(`/advisor/screener?limit=${limit}`);
}
