import { apiClient } from "@/lib/api-client";
import type { FIIScoredResponse } from "./types";

export async function getFIIScreenerRanked(): Promise<FIIScoredResponse> {
  return apiClient<FIIScoredResponse>("/fii-screener/ranked");
}
