import { apiClient } from "@/lib/api-client";
import type {
  AcaoScreenerParams,
  AcaoScreenerResponse,
  FIIScreenerParams,
  FIIScreenerResponse,
  FixedIncomeCatalogResponse,
  TesouroRatesResponse,
} from "./types";

function buildQuery(params: Record<string, unknown>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") {
      q.set(k, String(v));
    }
  }
  const s = q.toString();
  return s ? `?${s}` : "";
}

export async function getAcoesScreener(
  params: AcaoScreenerParams = {}
): Promise<AcaoScreenerResponse> {
  return apiClient<AcaoScreenerResponse>(`/screener/acoes${buildQuery(params as unknown as Record<string, unknown>)}`);
}

export async function getFIIScreener(
  params: FIIScreenerParams = {}
): Promise<FIIScreenerResponse> {
  return apiClient<FIIScreenerResponse>(`/screener/fiis${buildQuery(params as unknown as Record<string, unknown>)}`);
}

export async function getFixedIncomeCatalog(): Promise<FixedIncomeCatalogResponse> {
  return apiClient<FixedIncomeCatalogResponse>("/renda-fixa/catalog");
}

export async function getTesouroRates(): Promise<TesouroRatesResponse> {
  return apiClient<TesouroRatesResponse>("/renda-fixa/tesouro");
}
