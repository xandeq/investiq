"use client";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import Link from "next/link";

interface MeResponse {
  user_id: string;
  tenant_id: string;
  plan: string;
}

function useUserPlan() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => apiClient<MeResponse>("/me"),
    staleTime: 60_000,
  });
}

interface Props {
  children: React.ReactNode;
}

export function PremiumGate({ children }: Props) {
  const { data, isLoading } = useUserPlan();

  if (isLoading) {
    return (
      <div className="h-48 rounded-xl border bg-card animate-pulse" />
    );
  }

  if (data?.plan === "free") {
    return (
      <div className="relative rounded-xl border bg-card overflow-hidden">
        {/* Blurred preview overlay */}
        <div className="absolute inset-0 bg-white/80 backdrop-blur-sm z-10 flex flex-col items-center justify-center gap-4 p-6">
          <div className="text-center space-y-2">
            <p className="text-lg font-semibold text-foreground">
              Recurso exclusivo Premium
            </p>
            <p className="text-sm text-muted-foreground max-w-xs">
              Acesse análises de DCF, valuation e impacto macro com o plano Premium.
            </p>
          </div>
          <Link
            href="/planos"
            className="rounded-md bg-primary text-primary-foreground px-5 py-2 text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            Fazer upgrade para Premium
          </Link>
        </div>
        {/* Blurred children as preview */}
        <div className="blur-sm pointer-events-none select-none">
          {children}
        </div>
      </div>
    );
  }

  // Pro or enterprise: render children normally
  return <>{children}</>;
}
