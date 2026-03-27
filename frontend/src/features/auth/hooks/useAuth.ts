"use client";

/**
 * useAuth — React hook for client-side auth state.
 *
 * Reads the access_token cookie on the client side for UI state.
 * Note: This is for UI rendering only (show/hide nav items, etc.).
 * Actual auth enforcement is done by the FastAPI backend on every API call
 * and by Next.js middleware for page-level redirects.
 *
 * JWT contents decoded client-side (no verification — frontend trusts the
 * backend to have issued a valid token; the backend verifies on each request).
 */
import { useCallback, useEffect, useState } from "react";
import { logout as apiLogout } from "@/features/auth/api";

interface AuthUser {
  userId: string;
  tenantId: string;
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop()?.split(";").shift() ?? null;
  }
  return null;
}

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = getCookie("access_token");
    if (token) {
      const payload = decodeJwtPayload(token);
      if (payload && payload.sub && payload.tenant_id) {
        setUser({
          userId: payload.sub as string,
          tenantId: payload.tenant_id as string,
        });
      }
    }
    setIsLoading(false);
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
    window.location.href = "/login";
  }, []);

  return {
    user,
    isLoading,
    isAuthenticated: user !== null,
    logout,
  };
}
