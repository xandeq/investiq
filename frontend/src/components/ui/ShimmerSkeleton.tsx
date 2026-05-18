import { cn } from "@/lib/utils";

interface ShimmerSkeletonProps {
  className?: string;
}

/**
 * Shimmer skeleton — sliding light reflection over a neutral base.
 * Use in place of bare `animate-pulse` divs for premium loading states.
 *
 * The shimmer is applied via a pseudo-element on a fixed, pointer-events-none
 * wrapper to avoid GPU repaints on scrolling containers (taste-skill Rule §5).
 */
export function ShimmerSkeleton({ className }: ShimmerSkeletonProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-lg bg-zinc-100",
        className
      )}
    >
      <div className="absolute inset-0 -translate-x-full animate-[shimmer_1.6s_ease-in-out_infinite] bg-gradient-to-r from-transparent via-white/60 to-transparent" />
    </div>
  );
}

/**
 * Ready-made NetWorthCard skeleton matching its layout.
 */
export function NetWorthSkeleton() {
  return (
    <div className="rounded-xl bg-zinc-900 p-6 space-y-3">
      <ShimmerSkeleton className="h-3 w-28 bg-zinc-700" />
      <ShimmerSkeleton className="h-10 w-56 bg-zinc-700" />
      <div className="flex gap-6 pt-1">
        <div className="space-y-1.5">
          <ShimmerSkeleton className="h-3 w-20 bg-zinc-700" />
          <ShimmerSkeleton className="h-5 w-32 bg-zinc-700" />
        </div>
        <div className="space-y-1.5">
          <ShimmerSkeleton className="h-3 w-14 bg-zinc-700" />
          <ShimmerSkeleton className="h-5 w-28 bg-zinc-700" />
        </div>
      </div>
    </div>
  );
}
