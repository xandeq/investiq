"use client";
import { useState } from "react";
import { CaretDown, CaretRight } from "@phosphor-icons/react";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import { DisclaimerBadge } from "./DisclaimerBadge";
import { SkillResult } from "../types";

interface Props {
  result: SkillResult | null | undefined;
  title: string;
  defaultOpen?: boolean;
}

export function SkillResultCard({ result, title, defaultOpen = false }: Props) {
  const [open, setOpen] = useState(defaultOpen);

  if (!result) {
    return (
      <div className="rounded-xl border border-zinc-200 bg-white p-5 space-y-3">
        <ShimmerSkeleton className="h-5 w-32 rounded" />
        <ShimmerSkeleton className="h-4 w-24 rounded" />
        <ShimmerSkeleton className="h-24 w-full rounded" />
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-zinc-200 bg-white overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-zinc-50 active:scale-[0.97] transition-all duration-150 text-left"
      >
        <div className="flex items-center gap-3">
          {open ? (
            <CaretDown className="h-4 w-4 text-zinc-400 shrink-0" />
          ) : (
            <CaretRight className="h-4 w-4 text-zinc-400 shrink-0" />
          )}
          <span className="font-semibold text-base text-zinc-900">{title}</span>
        </div>
        <span className="text-xs bg-zinc-100 text-zinc-600 rounded px-2 py-0.5 shrink-0">
          {result.methodology}
        </span>
      </button>

      {open && (
        <div className="px-5 pb-5 pt-1 border-t border-zinc-100">
          <p className="text-sm text-zinc-500 whitespace-pre-wrap leading-relaxed">
            {result.analysis}
          </p>
          <DisclaimerBadge />
        </div>
      )}
    </div>
  );
}
