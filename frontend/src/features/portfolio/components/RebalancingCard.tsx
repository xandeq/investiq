"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Target, Pencil, Check, X } from "lucide-react";

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
};

function fmtBrl(v: string | number) {
  const n = typeof v === "string" ? parseFloat(v) : v;
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(n);
}

function actionColor(action: string) {
  if (action === "comprar") return "text-emerald-600 bg-emerald-50";
  if (action === "vender") return "text-red-600 bg-red-50";
  return "text-gray-500 bg-gray-50";
}

export function RebalancingCard() {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Record<string, string>>({});

  const { data: plan, isLoading } = useQuery({
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
    },
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
  };

  const saveEdit = () => {
    const items: TargetItem[] = Object.entries(draft)
      .filter(([, v]) => v !== "" && parseFloat(v) > 0)
      .map(([ac, pct]) => ({ asset_class: ac, target_pct: pct }));
    saveMutation.mutate(items);
  };

  const sumTargets = Object.values(draft).reduce((s, v) => s + (parseFloat(v) || 0), 0);

  if (isLoading) return <div className="h-40 rounded-xl bg-gray-100 animate-pulse" />;
  if (!plan) return null;

  return (
    <div className="rounded-xl border bg-white p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Target className="h-4 w-4 text-blue-500" />
          <p className="text-xs font-bold uppercase tracking-wider text-gray-500">Rebalanceamento</p>
        </div>
        {!editing ? (
          <button
            onClick={startEdit}
            className="flex items-center gap-1 px-2 py-1 text-xs text-gray-500 hover:text-blue-600 border rounded-md hover:border-blue-300 transition-colors"
          >
            <Pencil className="h-3 w-3" />
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

      {!plan.has_targets && !editing && (
        <p className="text-sm text-muted-foreground">
          Defina a alocação alvo por classe de ativo para ver o plano de rebalanceamento.
        </p>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-[11px] uppercase text-gray-400 font-semibold">
              <th className="text-left py-1.5">Classe</th>
              <th className="text-right py-1.5">Atual</th>
              <th className="text-right py-1.5">Meta %</th>
              {plan.has_targets && <th className="text-right py-1.5">Drift R$</th>}
              {plan.has_targets && <th className="text-right py-1.5">Ação</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {plan.slots.map((s) => {
              const drift = parseFloat(s.drift_brl);
              const driftPct = parseFloat(s.drift_pct);
              return (
                <tr key={s.asset_class} className="hover:bg-gray-50/50">
                  <td className="py-2 font-medium text-gray-800">
                    {CLASS_LABELS[s.asset_class] || s.asset_class}
                  </td>
                  <td className="text-right text-gray-600 py-2">
                    {parseFloat(s.current_pct).toFixed(1)}%
                    <span className="block text-[10px] text-gray-400">{fmtBrl(s.current_value)}</span>
                  </td>
                  <td className="text-right py-2">
                    {editing ? (
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="1"
                        value={draft[s.asset_class] ?? ""}
                        onChange={(e) => setDraft((d) => ({ ...d, [s.asset_class]: e.target.value }))}
                        className="w-16 text-right border rounded px-1 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
                        placeholder="0"
                      />
                    ) : (
                      <span className={plan.has_targets && parseFloat(s.target_pct) > 0 ? "font-semibold" : "text-gray-400"}>
                        {plan.has_targets && parseFloat(s.target_pct) > 0 ? `${parseFloat(s.target_pct).toFixed(0)}%` : "—"}
                      </span>
                    )}
                  </td>
                  {plan.has_targets && (
                    <td className="text-right py-2">
                      <span className={drift > 0 ? "text-red-600" : drift < 0 ? "text-emerald-600" : "text-gray-400"}>
                        {drift === 0 ? "—" : `${drift > 0 ? "+" : ""}${fmtBrl(drift)}`}
                      </span>
                      <span className="block text-[10px] text-gray-400">
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
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {plan.has_targets && parseFloat(plan.max_drift_pct) > 5 && (
        <p className="text-xs text-amber-600 bg-amber-50 rounded px-3 py-1.5">
          ⚠ Drift máximo de {parseFloat(plan.max_drift_pct).toFixed(1)}pp — carteira fora da meta alvo.
        </p>
      )}
    </div>
  );
}
