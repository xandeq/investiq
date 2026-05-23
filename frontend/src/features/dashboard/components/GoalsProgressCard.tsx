"use client";

import Link from "next/link";
import { Target, CheckCircle, Warning, ArrowRight } from "@phosphor-icons/react";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import { useGoals } from "@/features/portfolio/hooks/useGoals";
import type { GoalResponse, GoalStatus } from "@/features/portfolio/types";

function fmt(val: string, prefix = "R$ "): string {
  const n = parseFloat(val);
  if (isNaN(n)) return "—";
  return prefix + n.toLocaleString("pt-BR", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function statusConfig(status: GoalStatus) {
  switch (status) {
    case "concluido":
      return { label: "Concluído", cls: "text-emerald-700 bg-emerald-50", bar: "bg-emerald-500" };
    case "em_andamento":
      return { label: "Em andamento", cls: "text-blue-700 bg-blue-50", bar: "bg-blue-500" };
    case "em_risco":
      return { label: "Em risco", cls: "text-amber-700 bg-amber-50", bar: "bg-amber-400" };
    default:
      return { label: "Não iniciado", cls: "text-zinc-500 bg-zinc-100", bar: "bg-zinc-300" };
  }
}

function GoalRow({ goal }: { goal: GoalResponse }) {
  const pct = Math.min(100, Math.max(0, parseFloat(goal.progress_pct)));
  const cfg = statusConfig(goal.status);

  return (
    <div className="py-3 first:pt-0 last:pb-0">
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <span className="text-sm font-medium text-zinc-900 truncate">{goal.name}</span>
        <span className={`text-xs px-1.5 py-0.5 rounded font-medium shrink-0 ${cfg.cls}`}>
          {cfg.label}
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full h-1.5 bg-zinc-100 rounded-full overflow-hidden mb-1.5">
        <div
          className={`h-full rounded-full transition-all ${cfg.bar}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="flex items-center justify-between text-xs text-zinc-500">
        <span>
          {fmt(goal.current_amount)} / {fmt(goal.target_amount)} ({pct.toFixed(0)}%)
        </span>
        {goal.months_to_deadline !== null && goal.status !== "concluido" && (
          <span className={goal.months_to_deadline <= 3 ? "text-amber-600" : ""}>
            {goal.months_to_deadline}m restantes
          </span>
        )}
        {goal.status === "concluido" && (
          <CheckCircle className="h-3.5 w-3.5 text-emerald-500" weight="fill" />
        )}
      </div>
    </div>
  );
}

export function GoalsProgressCard() {
  const { data: goals, isLoading, error } = useGoals();

  if (isLoading) {
    return (
      <div className="rounded-xl border border-zinc-200 bg-white p-5">
        <ShimmerSkeleton className="h-4 w-40 mb-4" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="py-3 border-b border-zinc-100 last:border-0 space-y-2">
            <ShimmerSkeleton className="h-3.5 w-32" />
            <ShimmerSkeleton className="h-1.5 w-full rounded-full" />
          </div>
        ))}
      </div>
    );
  }

  if (error || !goals) return null;
  if (goals.length === 0) return null;

  const atRisk = goals.filter((g) => g.status === "em_risco").length;
  const completed = goals.filter((g) => g.status === "concluido").length;

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Target className="h-4 w-4 text-zinc-500" weight="duotone" />
          <h2 className="text-sm font-semibold text-zinc-900">Metas de Investimento</h2>
        </div>
        <div className="flex items-center gap-2">
          {atRisk > 0 && (
            <span className="flex items-center gap-1 text-xs text-amber-600">
              <Warning className="h-3.5 w-3.5" weight="fill" />
              {atRisk} em risco
            </span>
          )}
          {completed > 0 && (
            <span className="flex items-center gap-1 text-xs text-emerald-600">
              <CheckCircle className="h-3.5 w-3.5" weight="fill" />
              {completed} concluída{completed !== 1 ? "s" : ""}
            </span>
          )}
          <Link
            href="/portfolio"
            className="flex items-center gap-0.5 text-xs text-blue-600 hover:text-blue-700"
          >
            Ver todas
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      </div>

      <div className="divide-y divide-zinc-100">
        {goals.slice(0, 5).map((goal) => (
          <GoalRow key={goal.id} goal={goal} />
        ))}
      </div>

      {goals.length > 5 && (
        <div className="mt-3 pt-3 border-t border-zinc-100 text-center">
          <Link href="/portfolio" className="text-xs text-zinc-400 hover:text-zinc-600">
            +{goals.length - 5} metas
          </Link>
        </div>
      )}
    </div>
  );
}
