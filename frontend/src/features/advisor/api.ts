import { apiClient } from "@/lib/api-client";
import type { PortfolioHealth } from "./types";

export async function getPortfolioHealth(): Promise<PortfolioHealth> {
  return apiClient<PortfolioHealth>("/advisor/health");
}
