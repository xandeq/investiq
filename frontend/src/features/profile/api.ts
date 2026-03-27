import { apiClient } from "@/lib/api-client";
import type { InvestorProfile, InvestorProfileUpsert } from "@/features/profile/types";

export async function getProfile(): Promise<InvestorProfile> {
  return apiClient<InvestorProfile>("/profile");
}

export async function upsertProfile(data: InvestorProfileUpsert): Promise<InvestorProfile> {
  return apiClient<InvestorProfile>("/profile", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
