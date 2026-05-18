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

// Telegram notification preferences
export interface TelegramPrefsData {
  telegram_chat_id: string | null;
}

export async function getTelegramPrefs(): Promise<TelegramPrefsData> {
  return apiClient<TelegramPrefsData>("/profile/telegram");
}

export async function updateTelegramPrefs(
  telegram_chat_id: string | null
): Promise<TelegramPrefsData> {
  return apiClient<TelegramPrefsData>("/profile/telegram", {
    method: "PATCH",
    body: JSON.stringify({ telegram_chat_id }),
  });
}
