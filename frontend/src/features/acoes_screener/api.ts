import { apiClient } from "@/lib/api-client";
import type { AcoesUniverseResponse } from "./types";

export async function getAcoesUniverse(): Promise<AcoesUniverseResponse> {
  return apiClient<AcoesUniverseResponse>("/screener/universe");
}
