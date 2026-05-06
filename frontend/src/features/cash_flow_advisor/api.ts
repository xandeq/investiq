import { apiClient } from "@/lib/api-client";
import type { CashParkingResponse } from "./types";

export async function getCashParking(): Promise<CashParkingResponse> {
  return apiClient<CashParkingResponse>("/advisor/cash-parking");
}
