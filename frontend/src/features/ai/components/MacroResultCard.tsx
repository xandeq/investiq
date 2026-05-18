"use client";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import { DisclaimerBadge } from "./DisclaimerBadge";
import { MacroResult } from "../types";

interface Props {
  result: MacroResult | null | undefined;
}

export function MacroResultCard({ result }: Props) {
  if (!result) {
    return (
      <div className="rounded-xl border border-zinc-200 bg-white p-5 space-y-3">
        <ShimmerSkeleton className="h-5 w-48 rounded" />
        <ShimmerSkeleton className="h-4 w-32 rounded" />
        <ShimmerSkeleton className="h-24 w-full rounded" />
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-5">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-base text-zinc-900">Impacto Macro no Portfólio</h3>
        <span className="text-xs bg-zinc-100 text-zinc-600 rounded px-2 py-0.5">
          {result.methodology}
        </span>
      </div>
      <p className="text-sm text-zinc-500 whitespace-pre-wrap leading-relaxed">
        {result.analysis}
      </p>
      <DisclaimerBadge />
    </div>
  );
}
