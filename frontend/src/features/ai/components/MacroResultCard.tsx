"use client";
import { Skeleton } from "@/components/ui/skeleton";
import { DisclaimerBadge } from "./DisclaimerBadge";
import { MacroResult } from "../types";

interface Props {
  result: MacroResult | null | undefined;
}

export function MacroResultCard({ result }: Props) {
  if (!result) {
    return (
      <div className="rounded-xl border bg-card p-5 space-y-3">
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  return (
    <div className="rounded-xl border bg-card p-5">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-base">Impacto Macro no Portfólio</h3>
        <span className="text-xs bg-gray-100 text-gray-600 rounded px-2 py-0.5">
          {result.methodology}
        </span>
      </div>
      <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">
        {result.analysis}
      </p>
      <DisclaimerBadge />
    </div>
  );
}
