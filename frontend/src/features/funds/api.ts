import { apiClient } from "@/lib/api-client";
import type { FundInfoResponse, FundPosition, FundSearchResult } from "./types";

export async function searchFunds(q: string): Promise<FundSearchResult[]> {
  return apiClient<FundSearchResult[]>(
    `/funds/search?q=${encodeURIComponent(q)}`
  );
}

export async function getFundPositions(): Promise<FundPosition[]> {
  return apiClient<FundPosition[]>("/funds/positions");
}

export async function getFundInfo(cnpj: string): Promise<FundInfoResponse> {
  return apiClient<FundInfoResponse>(`/funds/info/${encodeURIComponent(cnpj)}`);
}
