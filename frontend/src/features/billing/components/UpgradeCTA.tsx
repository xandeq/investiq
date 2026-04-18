"use client";
import { useState } from "react";
import { apiClient } from "@/lib/api-client";
import { createCheckoutSession } from "../api";

interface Props {
  label?: string;
  className?: string;
}

export function UpgradeCTA({
  label = "Fazer upgrade para Premium",
  className = "rounded-md bg-primary text-primary-foreground px-5 py-2 text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-60",
}: Props) {
  const [loading, setLoading] = useState(false);

  const handleUpgrade = async () => {
    if (loading) return;
    setLoading(true);
    try {
      // Fetches fresh plan from server before checkout to guard against stale JWT/cache
      const me = await apiClient<{ plan: string }>("/me");
      if (me.plan === "pro") {
        window.location.href = "/planos";
        return;
      }
      const { checkout_url } = await createCheckoutSession();
      window.location.href = checkout_url;
    } catch {
      setLoading(false);
    }
  };

  return (
    <button onClick={handleUpgrade} disabled={loading} className={className}>
      {loading ? "Aguarde..." : label}
    </button>
  );
}
