import { apiClient } from "@/lib/api-client";
import type { DashboardSummary } from "@/features/dashboard/types";

export async function getDashboardSummary(): Promise<DashboardSummary> {
  return apiClient<DashboardSummary>("/dashboard/summary");
}
