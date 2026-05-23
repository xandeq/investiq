"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Crosshair, PencilSimple, Check, X, Warning, ArrowClockwise } from "@phosphor-icons/react";
import { apiClient } from "@/lib/api-client";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

interface TargetItem { asset_class: string; target_pct: string }

interface RebalancingSlot {
  asset_class: string;
  current_value: string;
  current_pct: string;
  target_pct: string;
  drift_brl: string;
  drift_pct: string;
  action: string;
}

interface RebalancingPlan {
  total_portfolio: string;
  slots: RebalancingSlot[];
  has_targets: boolean;
  max_drift_pct: string;
  targets_sum_pct: string;
}

const CLASS_LABELS: Record<string, string> = {
  acao: "Ações",
  fii: "FIIs",
  renda_fixa: "Renda Fixa",
  tesouro_direto: "Tesouro Direto",
  etf: "ETFs",
  bdr: "BDRs",
  crypto: "Cripto",
  fundo: "Fundos",
};

function fmtBrl(v: string | number) {
  const n = typeof v === "string" ? parseFloat(v) : v;
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(n);
}

function actionColor(action: string) {
  if (action === "comprar") return "text-emerald-600 bg-emerald-50";
  if (action === "vender") return "text-red-600 bg-red-50";
  return "text-zinc-500 bg-zinc-50";
}

export function RebalancingCard() {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [saveError, setSaveError] = useState("");

  const { data: plan, isLoading, isError, refetch } = useQuery({
    queryKey: ["portfolio", "rebalancing-plan"],
    queryFn: () => apiClient<RebalancingPlan>("/portfolio/rebalancing-plan"),
    staleTime: 5 * 60 * 1000,
  });

  const { data: targets } = useQuery({
    queryKey: ["portfolio", "targets"],
    queryFn: () => apiClient<TargetItem[]>("/portfolio/targets"),
    staleTime: 10 * 60 * 1000,
  });

  const saveMutation = useMutation({
    mutationFn: (items: TargetItem[]) =>
      apiClient<TargetItem[]>("/portfolio/targets", { method: "PUT", body: JSON.stringify(items) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["portfolio", "rebalancing-plan"] });
      qc.invalidateQueries({ queryKey: ["portfolio", "targets"] });
      setEditing(false);
      setSaveError("");
    },
    onError: (e: Error) => setSaveError(e.message),
  });

  const startEdit = () => {
    const initial: Record<string, string> = {};
    if (plan?.slots) {
      for (const s of plan.slots) {
        initial[s.asset_class] = s.target_pct !== "0" ? s.target_pct : "";
      }
    }
    if (targets) {
      for (const t of targets) {
        initial[t.asset_class] = t.target_pct;
      }
    }
    setDraft(initial);
    setEditing(true);
    setSaveError("");
  };

  const saveEdit = () => {
    const items: TargetItem[] = Object.entries(draft)
      .filter(([, v]) => v !== "" && parseFloat(v) > 0)
      .map(([ac, pct]) => ({ asset_class: ac, target_pct: pct }));
    saveMutation.mutate(items);
  };

  const sumTargets = Object.values(draft).reduce((s, v) => s + (parseFloat(v) || 0), 0);

  if (isLoading) return <ShimmerSkeleton className="h-40 rounded-xl" />;

  if (isError) {
    return (
      <div className="rounded-xl border border-zinc-200 bg-white p-4 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Warning className="h-4 w-4 text-amber-500 shrink-0" />
          <p className="text-sm text-zinc-500">Erro ao carregar plano de rebalanceamento.</p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-1 text-xs text-zinc-500 hover:text-blue-600 border border-zinc-200 rounded-md px-2 py-1 hover:border-blue-300 active:scale-[0.97] transition-all duration-150"
        >
          <ArrowClockwise className="h-3 w-3" />
          Tentar novamente
        </button>
      </div>
    );
  }

  if (!plan) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-xl border border-zinc-200 bg-white p-4 space-y-4"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Crosshair className="h-4 w-4 text-blue-500" weight="fill" />
          <p className="text-[11px] font-bold uppercase tracking-wider text-zinc-400">Rebalanceamento</p>
        </div>
        {!editing ? (
          <button
            onClick={startEdit}
            className="flex items-center gap-1 px-2 py-1 text-xs text-zinc-500 hover:text-blue-600 border border-zinc-200 rounded-md hover:border-blue-300 active:scale-[0.97] transition-all duration-150"
          >
            <PencilSimple className="h-3 w-3" />
            {plan.has_targets ? "Editar metas" : "Definir metas"}
          </button>
        ) : (
          <div className="flex items-center gap-2">
            <span className={`text-xs font-medium ${Math.abs(sumTargets - 100) > 1 ? "text-amber-600" : "text-emerald-600"}`}>
              Σ {sumTargets.toFixed(0)}%
            </span>
            <button onClick={saveEdit} className="p-1 rounded text-emerald-600 hover:bg-emerald-50">
              <Check className="h-3.5 w-3.5" />
            </button>
            <button onClick={() => setEditing(false)} className="p-1 rounded text-red-500 hover:bg-red-50">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        )}
      </div>

      {saveError && (
        <p className="flex items-center gap-1.5 text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
          <Warning className="h-3.5 w-3.5 shrink-0" />
          {saveError}
        </p>
      )}

      {!plan.has_targets && !editing && (
        <p className="text-sm text-zinc-400">
          Defina a alocação alvo por classe de ativo para ver o plano de rebalanceamento.
        </p>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-100 text-[11px] uppercase text-zinc-400 font-semibold">
              <th className="text-left py-1.5">Classe</th>
              <th className="text-right py-1.5">Atual</th>
              <th className="text-right py-1.5">Meta %</th>
              {plan.has_targets && <th className="text-right py-1.5">Drift R$</th>}
              {plan.has_targets && <th className="text-right py-1.5">Ação</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-50">
            {plan.slots.map((s, i) => {
              const drift = parseFloat(s.drift_brl);
              const driftPct = parseFloat(s.drift_pct);
              return (
                <motion.tr
                  key={s.asset_class}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1], delay: i * 0.04 }}
                  className="hover:bg-zinc-50/60"
                >
                  <td className="py-2 font-medium text-zinc-800">
                    {CLASS_LABELS[s.asset_class] || s.asset_class}
                  </td>
                  <td className="text-right tabular-nums text-zinc-500 py-2">
                    {parseFloat(s.current_pct).toFixed(1)}%
                    <span className="block text-[10px] text-zinc-400">{fmtBrl(s.current_value)}</span>
                  </td>
                  <td className="text-right tabular-nums py-2">
                    {editing ? (
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="1"
                        value={draft[s.asset_class] ?? ""}
                        onChange={(e) => setDraft((d) => ({ ...d, [s.asset_class]: e.target.value }))}
                        className="w-16 text-right border border-zinc-200 rounded px-1 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
                        placeholder="0"
                      />
                    ) : (
                      <span className={plan.has_targets && parseFloat(s.target_pct) > 0 ? "font-semibold" : "text-zinc-400"}>
                        {plan.has_targets && parseFloat(s.target_pct) > 0 ? `${parseFloat(s.target_pct).toFixed(0)}%` : "—"}
                      </span>
                    )}
                  </td>
                  {plan.has_targets && (
                    <td className="text-right tabular-nums py-2">
                      <span className={drift > 0 ? "text-red-600" : drift < 0 ? "text-emerald-600" : "text-zinc-400"}>
                        {drift === 0 ? "—" : `${drift > 0 ? "+" : ""}${fmtBrl(drift)}`}
                      </span>
                      <span className="block text-[10px] text-zinc-400">
                        {driftPct === 0 ? "" : `${driftPct > 0 ? "+" : ""}${driftPct.toFixed(1)}pp`}
                      </span>
                    </td>
                  )}
                  {plan.has_targets && (
                    <td className="text-right py-2">
                      <span className={`text-xs font-semibold px-1.5 py-0.5 rounded ${actionColor(s.action)}`}>
                        {s.action}
                      </span>
                    </td>
                  )}
                </motion.tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {plan.has_targets && parseFloat(plan.max_drift_pct) > 5 && (
        <div className="flex items-center gap-2 text-xs text-amber-700 bg-amber-50 rounded-lg px-3 py-2">
          <Warning size={14} weight="fill" className="text-amber-500 shrink-0" aria-hidden />
          Drift máximo de {parseFloat(plan.max_drift_pct).toFixed(1)}pp — carteira fora da meta alvo.
        </div>
      )}
    </motion.div>
  );
}
