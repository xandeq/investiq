"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { apiClient } from "@/lib/api-client";

interface MeResponse {
  user_id: string;
  tenant_id: string;
  plan: string;
  email?: string;
  is_admin?: boolean;
  is_trial?: boolean;
  days_remaining?: number;
  trial_ends_at?: string;
}

export function useSubscription(options?: { refetchInterval?: number | false }) {
  const [data, setData] = useState<MeResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refetch = useCallback(async () => {
    try {
      const result = await apiClient<MeResponse>("/me");
      setData(result);
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (options?.refetchInterval) {
      intervalRef.current = setInterval(refetch, options.refetchInterval);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [options?.refetchInterval, refetch]);

  return {
    plan: data?.plan ?? "free",
    isPro: data?.plan === "pro",
    isAdmin: data?.is_admin ?? false,
    isTrial: data?.is_trial ?? false,
    daysRemaining: data?.days_remaining ?? 0,
    trialEndsAt: data?.trial_ends_at ?? null,
    isLoading,
    refetch,
  };
}
