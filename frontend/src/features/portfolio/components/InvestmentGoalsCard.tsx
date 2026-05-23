"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Target, Plus, PencilSimple, Trash, Check, X,
  CalendarBlank, TrendUp, Warning, ArrowClockwise,
} from "@phosphor-icons/react";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import { formatBRL } from "@/lib/formatters";
import { getGoals, createGoal, updateGoal, deleteGoal } from "@/features/portfolio/api";
import type { GoalResponse, GoalCreate, GoalUpdate, GoalStatus } from "@/features/portfolio/types";

// ─── Constants ────────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<GoalStatus, string> = {
  nao_iniciado: "Não iniciada",
  em_andamento: "Em andamento",
  em_risco: "Em risco",
  concluido: "Concluída",
};

// Restrained palette — no neon, max 1 accent per status
const STATUS_CLASSES: Record<GoalStatus, string> = {
  nao_iniciado:  "bg-zinc-100  text-zinc-500  border-zinc-200",
  em_andamento:  "bg-blue-50   text-blue-600  border-blue-100",
  em_risco:      "bg-amber-50  text-amber-700 border-amber-200",
  concluido:     "bg-emerald-50 text-emerald-700 border-emerald-200",
};

const PROGRESS_COLOR: Record<GoalStatus, string> = {
  nao_iniciado: "bg-zinc-300",
  em_andamento: "bg-blue-500",
  em_risco:     "bg-amber-400",
  concluido:    "bg-emerald-500",
};

const BLANK_FORM: GoalCreate = {
  name: "",
  target_amount: "",
  current_amount: "0",
  asset_class: null,
  deadline: null,
  notes: null,
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDeadline(dateStr: string | null): string {
  if (!dateStr) return "Sem prazo";
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("pt-BR", {
    day: "2-digit", month: "short", year: "numeric",
  });
}

function isDateInPast(dateStr: string): boolean {
  const [y, m] = dateStr.split("-").map(Number);
  const today = new Date();
  return y < today.getFullYear() || (y === today.getFullYear() && m < today.getMonth() + 1);
}

// ─── Error Banner ─────────────────────────────────────────────────────────────

function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-center justify-between gap-2 rounded-lg border border-red-100 bg-red-50 px-3 py-2">
      <div className="flex items-center gap-2 min-w-0">
        <Warning size={14} className="text-red-500 shrink-0" />
        <p className="text-xs text-red-600 truncate">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-1 text-xs font-medium text-red-600 hover:text-red-800 shrink-0 active:scale-[0.97] transition-all duration-150"
        >
          <ArrowClockwise size={12} />
          Tentar novamente
        </button>
      )}
    </div>
  );
}

// ─── Goal Form ────────────────────────────────────────────────────────────────

function GoalForm({
  initial,
  onSave,
  onCancel,
  saving,
  serverError,
}: {
  initial: GoalCreate;
  onSave: (data: GoalCreate) => void;
  onCancel: () => void;
  saving: boolean;
  serverError: string;
}) {
  const [form, setForm] = useState<GoalCreate>(initial);
  const [validationError, setValidationError] = useState("");

  function set(k: keyof GoalCreate, v: string | null) {
    setForm((f) => ({ ...f, [k]: v }));
    setValidationError("");
  }

  function handleSave() {
    const amount = parseFloat(form.target_amount || "0");
    if (!form.name.trim()) {
      setValidationError("Nome da meta é obrigatório.");
      return;
    }
    if (!form.target_amount || isNaN(amount) || amount <= 0) {
      setValidationError("Valor alvo deve ser maior que zero.");
      return;
    }
    onSave(form);
  }

  const deadlinePast = form.deadline ? isDateInPast(form.deadline) : false;
  const displayError = validationError || serverError;

  return (
    <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4 space-y-3">
      {/* Name */}
      <div>
        <label className="block text-xs font-semibold text-zinc-500 mb-1">
          Nome da meta <span className="text-red-400">*</span>
        </label>
        <input
          value={form.name}
          onChange={(e) => set("name", e.target.value)}
          placeholder="Ex: Reserva de emergência"
          maxLength={200}
          className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 transition-shadow"
        />
      </div>

      {/* Amounts */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold text-zinc-500 mb-1">
            Valor alvo (R$) <span className="text-red-400">*</span>
          </label>
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={form.target_amount}
            onChange={(e) => set("target_amount", e.target.value)}
            placeholder="50000.00"
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 transition-shadow"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-zinc-500 mb-1">
            Valor atual (R$)
          </label>
          <input
            type="number"
            min="0"
            step="0.01"
            value={form.current_amount}
            onChange={(e) => set("current_amount", e.target.value)}
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 transition-shadow"
          />
        </div>
      </div>

      {/* Deadline + Notes */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold text-zinc-500 mb-1">Prazo</label>
          <input
            type="date"
            value={form.deadline ?? ""}
            onChange={(e) => set("deadline", e.target.value || null)}
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 transition-shadow"
          />
          {deadlinePast && (
            <p className="mt-1 flex items-center gap-1 text-[11px] text-amber-600">
              <Warning size={11} />
              Prazo já vencido — meta em risco.
            </p>
          )}
        </div>
        <div>
          <label className="block text-xs font-semibold text-zinc-500 mb-1">Observações</label>
          <input
            value={form.notes ?? ""}
            onChange={(e) => set("notes", e.target.value || null)}
            placeholder="Opcional"
            maxLength={2000}
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 transition-shadow"
          />
        </div>
      </div>

      {/* Error */}
      {displayError && (
        <p className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
          {displayError}
        </p>
      )}

      {/* Actions */}
      <div className="flex gap-2 justify-end pt-1">
        <button
          onClick={onCancel}
          className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg bg-zinc-200 hover:bg-zinc-300 font-medium transition-colors active:scale-[0.98]"
        >
          <X size={14} />
          Cancelar
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-1 px-4 py-1.5 text-sm rounded-lg bg-blue-500 text-white hover:bg-blue-600 font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-colors active:scale-[0.98]"
        >
          <Check size={14} />
          {saving ? "Salvando…" : "Salvar"}
        </button>
      </div>
    </div>
  );
}

// ─── Goal Row ─────────────────────────────────────────────────────────────────

function GoalRow({
  goal,
  isDeleting,
  onEdit,
  onDelete,
}: {
  goal: GoalResponse;
  isDeleting: boolean;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const pct = parseFloat(goal.progress_pct);
  const cappedPct = Math.min(100, pct);
  const isComplete = goal.status === "concluido";

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: isDeleting ? 0.4 : 1, y: 0 }}
      exit={{ opacity: 0, y: -4, transition: { duration: 0.18 } }}
      transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] as const }}
      className="rounded-xl border border-zinc-100 bg-white p-4 space-y-3"
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-zinc-900 text-sm truncate">{goal.name}</p>
          <div className="flex items-center gap-1.5 mt-1 flex-wrap">
            {/* Status badge */}
            <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold leading-none ${STATUS_CLASSES[goal.status]}`}>
              {STATUS_LABELS[goal.status]}
            </span>
            {/* Deadline pill */}
            {goal.deadline && (
              <span className="flex items-center gap-1 text-[11px] text-zinc-400">
                <CalendarBlank size={11} />
                {formatDeadline(goal.deadline)}
                {goal.months_to_deadline !== null && goal.months_to_deadline > 0 && (
                  <span className="ml-0.5 rounded-full bg-zinc-100 px-1.5 py-0.5 text-zinc-500 font-medium text-[10px]">
                    {goal.months_to_deadline}m
                  </span>
                )}
              </span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-0.5 shrink-0">
          <button
            onClick={onEdit}
            disabled={isDeleting}
            className="p-1.5 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-zinc-700 disabled:opacity-40 active:scale-[0.97] transition-all duration-150"
            title="Editar"
          >
            <PencilSimple size={14} />
          </button>
          <button
            onClick={onDelete}
            disabled={isDeleting}
            className="p-1.5 rounded-lg hover:bg-red-50 text-zinc-400 hover:text-red-600 disabled:opacity-40 active:scale-[0.97] transition-all duration-150"
            title="Excluir"
          >
            {isDeleting
              ? <span className="block h-3.5 w-3.5 rounded-full border-2 border-red-300 border-t-red-600 animate-spin" />
              : <Trash size={14} />
            }
          </button>
        </div>
      </div>

      {/* Progress section */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className={`text-xs font-bold tabular-nums ${isComplete ? "text-emerald-700" : "text-zinc-600"}`}>
            {pct.toFixed(1)}%
          </span>
          <span className="text-[11px] text-zinc-400 tabular-nums">
            {formatBRL(goal.current_amount)} / {formatBRL(goal.target_amount)}
          </span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-zinc-100 overflow-hidden">
          <motion.div
            className={`h-full rounded-full ${PROGRESS_COLOR[goal.status]}`}
            initial={{ width: 0 }}
            animate={{ width: `${cappedPct}%` }}
            transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] as const }}
          />
        </div>

        {/* Status line */}
        <div className="mt-1 h-4 flex items-center">
          {isComplete && (
            <p className="text-[11px] text-emerald-700 font-semibold">Meta atingida.</p>
          )}
          {!isComplete && goal.status === "em_risco" && (
            <p className="flex items-center gap-1 text-[11px] text-amber-700 font-medium">
              <Warning size={11} />
              Prazo vencido — faltam {formatBRL(goal.remaining_amount)}
            </p>
          )}
          {!isComplete && goal.status !== "em_risco" && goal.monthly_contribution_needed && (
            <p className="flex items-center gap-1 text-[11px] text-zinc-500 tabular-nums">
              <TrendUp size={11} className="text-blue-400 shrink-0" />
              Aporte sugerido:{" "}
              <span className="font-semibold text-zinc-700">
                {formatBRL(goal.monthly_contribution_needed)}/mês
              </span>
            </p>
          )}
          {!isComplete && !goal.monthly_contribution_needed && goal.status !== "em_risco" && (
            <p className="text-[11px] text-zinc-400 tabular-nums">
              Faltam {formatBRL(goal.remaining_amount)}
            </p>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ─── Main Component ────────────────────────────────────────────────────────────

export function InvestmentGoalsCard() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [serverError, setServerError] = useState("");

  const {
    data: goals,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["portfolio", "goals"],
    queryFn: getGoals,
    staleTime: 60_000,
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["portfolio", "goals"] });

  const createMut = useMutation({
    mutationFn: createGoal,
    onSuccess: () => {
      setShowForm(false);
      setServerError("");
      invalidate();
    },
    onError: (e: Error) => setServerError(e.message),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: GoalUpdate }) =>
      updateGoal(id, data),
    onSuccess: () => {
      setEditingId(null);
      setServerError("");
      invalidate();
    },
    onError: (e: Error) => setServerError(e.message),
  });

  const deleteMut = useMutation({
    mutationFn: async (id: string) => {
      setDeletingId(id);
      return deleteGoal(id);
    },
    onSuccess: () => {
      setDeletingId(null);
      invalidate();
    },
    onError: (e: Error) => {
      setDeletingId(null);
      setServerError(e.message);
    },
  });

  function openCreate() {
    setShowForm(true);
    setEditingId(null);
    setServerError("");
  }

  function openEdit(id: string) {
    setEditingId(id);
    setShowForm(false);
    setServerError("");
  }

  function handleCreate(data: GoalCreate) {
    createMut.mutate(data);
  }

  function handleUpdate(id: string, data: GoalCreate) {
    updateMut.mutate({ id, data });
  }

  return (
    <div className="rounded-xl border border-zinc-200 bg-white px-5 py-4 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Target size={16} className="text-blue-500" />
          <h2 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
            Metas de Investimento
          </h2>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg bg-blue-50 text-blue-600 hover:bg-blue-100 font-semibold transition-colors active:scale-[0.98]"
        >
          <Plus size={12} weight="bold" />
          Nova meta
        </button>
      </div>

      {/* Query error */}
      {isError && (
        <ErrorBanner
          message="Não foi possível carregar as metas."
          onRetry={() => refetch()}
        />
      )}

      {/* Mutation error (create/update/delete) */}
      {serverError && !isError && (
        <div className="mb-3">
          <ErrorBanner message={serverError} />
        </div>
      )}

      {/* Loading skeletons */}
      {isLoading && (
        <div className="space-y-3">
          {[0, 1].map((i) => (
            <ShimmerSkeleton key={i} className="h-24 w-full rounded-xl" />
          ))}
        </div>
      )}

      {/* Create form */}
      <AnimatePresence>
        {showForm && !editingId && (
          <motion.div
            key="create-form"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] as const }}
            className="mb-3 overflow-hidden"
          >
            <GoalForm
              initial={BLANK_FORM}
              onSave={handleCreate}
              onCancel={() => { setShowForm(false); setServerError(""); }}
              saving={createMut.isPending}
              serverError={serverError}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Empty state */}
      {!isLoading && !isError && goals && goals.length === 0 && !showForm && (
        <div className="py-8 text-center">
          <Target size={28} className="mx-auto text-zinc-200 mb-2" />
          <p className="text-sm text-zinc-400">Nenhuma meta cadastrada.</p>
          <p className="text-xs text-zinc-300 mt-0.5">
            Clique em &quot;Nova meta&quot; para definir objetivos financeiros.
          </p>
        </div>
      )}

      {/* Goal list */}
      {!isLoading && goals && goals.length > 0 && (
        <div className="space-y-3">
          <AnimatePresence>
            {goals.map((goal) =>
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
                    onCancel={() => { setEditingId(null); setServerError(""); }}
                    saving={updateMut.isPending}
                    serverError={serverError}
                  />
                </motion.div>
              ) : (
                <GoalRow
                  key={goal.id}
                  goal={goal}
                  isDeleting={deletingId === goal.id}
                  onEdit={() => openEdit(goal.id)}
                  onDelete={() => deleteMut.mutate(goal.id)}
                />
              )
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
