import { apiClient } from "@/lib/api-client";
import type { InboxResponse, PortfolioHealth } from "./types";

export async function getPortfolioHealth(): Promise<PortfolioHealth> {
  return apiClient<PortfolioHealth>("/advisor/health");
}

export async function getInbox(): Promise<InboxResponse> {
  return apiClient<InboxResponse>("/advisor/inbox");
}
