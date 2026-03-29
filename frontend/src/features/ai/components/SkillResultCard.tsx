"use client";
import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
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
      <div className="rounded-xl border bg-card p-5 space-y-3">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  return (
    <div className="rounded-xl border bg-card overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-muted/50 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          {open ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
          )}
          <span className="font-semibold text-base">{title}</span>
        </div>
        <span className="text-xs bg-gray-100 text-gray-600 rounded px-2 py-0.5 shrink-0">
          {result.methodology}
        </span>
      </button>

      {open && (
        <div className="px-5 pb-5 pt-1 border-t">
          <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">
            {result.analysis}
          </p>
          <DisclaimerBadge />
        </div>
      )}
    </div>
  );
}
