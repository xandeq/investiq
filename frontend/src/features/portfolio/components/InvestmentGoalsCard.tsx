"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Target, Plus, PencilSimple, Trash, Check, X, CalendarBlank } from "@phosphor-icons/react";
import { apiClient } from "@/lib/api-client";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import { formatBRL } from "@/lib/formatters";

// ─── Types ────────────────────────────────────────────────────────────────────

interface GoalResponse {
  id: string;
  name: string;
  target_amount: string;
  current_amount: string;
  asset_class: string | null;
  deadline: string | null;
  notes: string | null;
  progress_pct: string;
  remaining_amount: string;
  months_to_deadline: number | null;
}

interface GoalCreate {
  name: string;
  target_amount: string;
  current_amount: string;
  asset_class: string | null;
  deadline: string | null;
  notes: string | null;
}

// ─── API helpers ──────────────────────────────────────────────────────────────

async function fetchGoals(): Promise<GoalResponse[]> {
  return apiClient<GoalResponse[]>("/portfolio/goals");
}

async function createGoal(data: GoalCreate): Promise<GoalResponse> {
  return apiClient<GoalResponse>("/portfolio/goals", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

async function updateGoal(id: string, data: Partial<GoalCreate>): Promise<GoalResponse> {
  return apiClient<GoalResponse>(`/portfolio/goals/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

async function deleteGoal(id: string): Promise<void> {
  await apiClient<void>(`/portfolio/goals/${id}`, { method: "DELETE" });
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDeadline(dateStr: string | null): string {
  if (!dateStr) return "Sem prazo";
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function progressColor(pct: number): string {
  if (pct >= 100) return "bg-emerald-500";
  if (pct >= 75) return "bg-blue-500";
  if (pct >= 40) return "bg-amber-400";
  return "bg-zinc-400";
}

const BLANK_FORM: GoalCreate = {
  name: "",
  target_amount: "",
  current_amount: "0",
  asset_class: null,
  deadline: null,
  notes: null,
};

// ─── Goal form ────────────────────────────────────────────────────────────────

function GoalForm({
  initial,
  onSave,
  onCancel,
  saving,
  error,
}: {
  initial: GoalCreate;
  onSave: (data: GoalCreate) => void;
  onCancel: () => void;
  saving: boolean;
  error: string;
}) {
  const [form, setForm] = useState<GoalCreate>(initial);

  function set(k: keyof GoalCreate, v: string | null) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  return (
    <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4 space-y-3">
      <div>
        <label className="block text-xs font-semibold text-zinc-500 mb-1">Nome da meta *</label>
        <input
          value={form.name}
          onChange={(e) => set("name", e.target.value)}
          placeholder="Ex: Reserva de emergência"
          className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold text-zinc-500 mb-1">Valor alvo (R$) *</label>
          <input
            type="number"
            min="0"
            step="0.01"
            value={form.target_amount}
            onChange={(e) => set("target_amount", e.target.value)}
            placeholder="50000.00"
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-zinc-500 mb-1">Valor atual (R$)</label>
          <input
            type="number"
            min="0"
            step="0.01"
            value={form.current_amount}
            onChange={(e) => set("current_amount", e.target.value)}
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold text-zinc-500 mb-1">Prazo</label>
          <input
            type="date"
            value={form.deadline ?? ""}
            onChange={(e) => set("deadline", e.target.value || null)}
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-zinc-500 mb-1">Observações</label>
          <input
            value={form.notes ?? ""}
            onChange={(e) => set("notes", e.target.value || null)}
            placeholder="Opcional"
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
      <div className="flex gap-2 justify-end pt-1">
        <button
          onClick={onCancel}
          className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg bg-zinc-200 hover:bg-zinc-300 font-medium transition-colors"
        >
          <X size={14} />
          Cancelar
        </button>
        <button
          onClick={() => onSave(form)}
          disabled={saving || !form.name || !form.target_amount}
          className="flex items-center gap-1 px-4 py-1.5 text-sm rounded-lg bg-blue-500 text-white hover:bg-blue-600 font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Check size={14} />
          {saving ? "Salvando…" : "Salvar"}
        </button>
      </div>
    </div>
  );
}

// ─── Goal row ─────────────────────────────────────────────────────────────────

function GoalRow({
  goal,
  onEdit,
  onDelete,
}: {
  goal: GoalResponse;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const pct = Math.min(100, parseFloat(goal.progress_pct));
  const barColor = progressColor(pct);
  const isComplete = pct >= 100;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] as const }}
      className="rounded-xl border border-zinc-100 bg-white p-4 space-y-3"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-zinc-900 text-sm truncate">{goal.name}</p>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            {goal.deadline && (
              <span className="flex items-center gap-1 text-[11px] text-zinc-400">
                <CalendarBlank size={12} />
                {formatDeadline(goal.deadline)}
                {goal.months_to_deadline !== null && goal.months_to_deadline > 0 && (
                  <span className="ml-1 rounded-full bg-zinc-100 px-1.5 py-0.5 text-zinc-500 font-medium">
                    {goal.months_to_deadline}m
                  </span>
                )}
                {goal.months_to_deadline === 0 && (
                  <span className="ml-1 rounded-full bg-amber-50 border border-amber-200 px-1.5 py-0.5 text-amber-700 font-medium text-[10px]">
                    Vencendo
                  </span>
                )}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={onEdit}
            className="p-1.5 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-zinc-700 transition-colors"
            title="Editar"
          >
            <PencilSimple size={14} />
          </button>
          <button
            onClick={onDelete}
            className="p-1.5 rounded-lg hover:bg-red-50 text-zinc-400 hover:text-red-600 transition-colors"
            title="Excluir"
          >
            <Trash size={14} />
          </button>
        </div>
      </div>

      {/* Progress bar */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className={`text-xs font-bold tabular-nums ${isComplete ? "text-emerald-600" : "text-zinc-600"}`}>
            {pct.toFixed(1)}%
          </span>
          <span className="text-xs text-zinc-400 tabular-nums">
            {formatBRL(goal.current_amount)} / {formatBRL(goal.target_amount)}
          </span>
        </div>
        <div className="h-2 w-full rounded-full bg-zinc-100 overflow-hidden">
          <motion.div
            className={`h-full rounded-full ${barColor}`}
            initial={{ width: 0 }}
            animate={{ width: `${Math.min(100, pct)}%` }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] as const }}
          />
        </div>
        {!isComplete && (
          <p className="mt-1 text-[11px] text-zinc-400 tabular-nums">
            Faltam {formatBRL(goal.remaining_amount)}
          </p>
        )}
        {isComplete && (
          <p className="mt-1 text-[11px] text-emerald-600 font-semibold">Meta atingida!</p>
        )}
      </div>
    </motion.div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function InvestmentGoalsCard() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [mutError, setMutError] = useState("");

  const { data: goals, isLoading } = useQuery({
    queryKey: ["portfolio", "goals"],
    queryFn: fetchGoals,
    staleTime: 60_000,
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["portfolio", "goals"] });

  const createMut = useMutation({
    mutationFn: createGoal,
    onSuccess: () => { setShowForm(false); setMutError(""); invalidate(); },
    onError: (e: Error) => setMutError(e.message),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<GoalCreate> }) =>
      updateGoal(id, data),
    onSuccess: () => { setEditingId(null); setMutError(""); invalidate(); },
    onError: (e: Error) => setMutError(e.message),
  });

  const deleteMut = useMutation({
    mutationFn: deleteGoal,
    onSuccess: () => invalidate(),
  });

  function handleCreate(data: GoalCreate) {
    if (!data.name.trim() || !data.target_amount) return;
    createMut.mutate(data);
  }

  function handleUpdate(id: string, data: GoalCreate) {
    updateMut.mutate({ id, data });
  }

  return (
    <div className="rounded-xl border border-zinc-200 bg-white px-5 py-4 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Target size={16} className="text-blue-500" />
          <h2 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
            Metas de Investimento
          </h2>
        </div>
        <button
          onClick={() => { setShowForm(true); setEditingId(null); setMutError(""); }}
          className="flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg bg-blue-50 text-blue-600 hover:bg-blue-100 font-semibold transition-colors"
        >
          <Plus size={12} weight="bold" />
          Nova meta
        </button>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[0, 1].map((i) => (
            <ShimmerSkeleton key={i} className="h-24 w-full rounded-xl" />
          ))}
        </div>
      )}

      <AnimatePresence>
        {showForm && !editingId && (
          <motion.div
            key="create-form"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-3 overflow-hidden"
          >
            <GoalForm
              initial={BLANK_FORM}
              onSave={handleCreate}
              onCancel={() => { setShowForm(false); setMutError(""); }}
              saving={createMut.isPending}
              error={mutError}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {!isLoading && goals && goals.length === 0 && !showForm && (
        <div className="py-8 text-center">
          <Target size={32} className="mx-auto text-zinc-200 mb-2" />
          <p className="text-sm text-zinc-400">Nenhuma meta cadastrada.</p>
          <p className="text-xs text-zinc-300 mt-0.5">Clique em "Nova meta" para começar.</p>
        </div>
      )}

      {!isLoading && goals && goals.length > 0 && (
        <div className="space-y-3">
          <AnimatePresence>
            {goals.map((goal) => (
              editingId === goal.id ? (
                <motion.div
                  key={`edit-${goal.id}`}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <GoalForm
                    initial={{
                      name: goal.name,
                      target_amount: goal.target_amount,
                      current_amount: goal.current_amount,
                      asset_class: goal.asset_class,
                      deadline: goal.deadline,
                      notes: goal.notes,
                    }}
                    onSave={(data) => handleUpdate(goal.id, data)}
                    onCancel={() => { setEditingId(null); setMutError(""); }}
                    saving={updateMut.isPending}
                    error={mutError}
                  />
                </motion.div>
              ) : (
                <GoalRow
                  key={goal.id}
                  goal={goal}
                  onEdit={() => { setEditingId(goal.id); setShowForm(false); setMutError(""); }}
                  onDelete={() => deleteMut.mutate(goal.id)}
                />
              )
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
