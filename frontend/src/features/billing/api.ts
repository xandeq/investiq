import { apiClient } from "@/lib/api-client";

export interface CheckoutResponse {
  checkout_url: string;
}

export interface PortalResponse {
  portal_url: string;
}

export interface UsageResponse {
  imports_this_month: number;
  imports_limit: number;
  transactions_total: number;
  transactions_limit: number;
  plan: string;
}

export async function createCheckoutSession(): Promise<CheckoutResponse> {
  return apiClient<CheckoutResponse>("/billing/checkout", { method: "POST" });
}

export async function createPortalSession(): Promise<PortalResponse> {
  return apiClient<PortalResponse>("/billing/portal", { method: "POST" });
}

export async function getUsage(): Promise<UsageResponse> {
  return apiClient<UsageResponse>("/billing/usage");
}
