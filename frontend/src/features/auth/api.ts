/**
 * Typed fetch wrappers for all /auth endpoints.
 * Uses the shared apiClient with credentials: "include" for cookie-based auth.
 */
import { apiClient } from "@/lib/api-client";

export interface RegisterResponse {
  message: string;
  user_id: string;
}

export interface MessageResponse {
  message: string;
}

export async function register(
  email: string,
  password: string
): Promise<RegisterResponse> {
  return apiClient<RegisterResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function login(
  email: string,
  password: string
): Promise<MessageResponse> {
  return apiClient<MessageResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function logout(): Promise<MessageResponse> {
  return apiClient<MessageResponse>("/auth/logout", {
    method: "POST",
  });
}

export async function verifyEmail(token: string): Promise<MessageResponse> {
  return apiClient<MessageResponse>(`/auth/verify-email?token=${encodeURIComponent(token)}`);
}

export async function forgotPassword(email: string): Promise<MessageResponse> {
  return apiClient<MessageResponse>("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function resetPassword(
  token: string,
  newPassword: string
): Promise<MessageResponse> {
  return apiClient<MessageResponse>("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}
