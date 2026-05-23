"use client";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import Link from "next/link";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import { Lock } from "@phosphor-icons/react";

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
    return <ShimmerSkeleton className="h-48 rounded-xl" />;
  }

  if (data?.plan === "free") {
    return (
      <div className="relative rounded-xl border border-zinc-200 bg-white overflow-hidden">
        <div className="absolute inset-0 bg-white/80 backdrop-blur-sm z-10 flex flex-col items-center justify-center gap-4 p-6">
          <div className="w-10 h-10 rounded-full bg-zinc-100 flex items-center justify-center">
            <Lock className="h-5 w-5 text-zinc-500" weight="bold" />
          </div>
          <div className="text-center space-y-1.5">
            <p className="text-base font-semibold text-zinc-900">
              Recurso exclusivo Premium
            </p>
            <p className="text-sm text-zinc-500 max-w-xs">
              Acesse análises de DCF, valuation e impacto macro com o plano Premium.
            </p>
          </div>
          <Link
            href="/planos"
            className="rounded-md bg-zinc-900 text-white px-5 py-2.5 text-sm font-semibold hover:bg-zinc-800 active:scale-[0.97] transition-all duration-150"
          >
            Fazer upgrade para Premium
          </Link>
        </div>
        <div className="blur-sm pointer-events-none select-none">
          {children}
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
