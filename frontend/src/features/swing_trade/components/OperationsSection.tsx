"use client";
import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Plus } from "@phosphor-icons/react";
import type { OperationListResponse, SwingOperation } from "../types";
import { NewOperationModal } from "./NewOperationModal";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

function fmt(n: number | null | undefined, decimals = 2): string {
  if (n == null) return "—";
  return n.toLocaleString("pt-BR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pt-BR");
}

// ─── Animated progress bar ──────────────────────────────────────────────────

function ProgressBar({ pct }: { pct: number | null }) {
  if (pct == null) return <span className="text-xs text-zinc-400">—</span>;
  const clamped = Math.max(0, Math.min(100, pct));
  const color =
    clamped >= 100 ? "bg-emerald-400" : clamped >= 50 ? "bg-blue-400" : "bg-zinc-300";
  return (
    <div className="w-full">
      <div className="h-1.5 bg-zinc-100 rounded-full overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${clamped}%` }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        />
      </div>
      <div className="text-[10px] text-zinc-400 text-right mt-0.5 tabular-nums">
        {fmt(pct, 0)}%
      </div>
    </div>
  );
}

// ─── Status badge ────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  if (status === "open") {
    return (
      <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
        ABERTA
      </span>
    );
  }
  if (status === "closed") {
    return (
      <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold bg-zinc-100 text-zinc-500 border border-zinc-200">
        FECHADA
      </span>
    );
  }
  return (
    <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold bg-red-50 text-red-600 border border-red-200">
      STOP
    </span>
  );
}

// ─── Operation row ───────────────────────────────────────────────────────────

function OperationRow({
  op,
  index,
  onClose,
  onDelete,
  isClosing,
  isDeleting,
}: {
  op: SwingOperation;
  index: number;
  onClose: (op: SwingOperation) => void;
  onDelete: (op: SwingOperation) => void;
  isClosing: boolean;
  isDeleting: boolean;
}) {
  const pnlPct =
    op.pnl_pct ??
    (op.exit_price != null && op.entry_price
      ? ((op.exit_price - op.entry_price) / op.entry_price) * 100
      : null);
  const pnlBrl =
    op.pnl_brl ??
    (op.exit_price != null
      ? (op.exit_price - op.entry_price) * op.quantity
      : null);
  const currentPrice = op.current_price ?? op.exit_price;

  const pnlColor = (v: number | null) =>
    v == null ? "text-zinc-400" : v >= 0 ? "text-emerald-600" : "text-red-500";

  return (
    <motion.tr
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1], delay: index * 0.04 }}
      className="border-b border-zinc-50 hover:bg-zinc-50/60 transition-colors"
    >
      <td className="py-3 px-3">
        <div className="font-mono font-bold text-sm text-zinc-900">{op.ticker}</div>
        <div className="mt-0.5">
          <StatusBadge status={op.status} />
        </div>
      </td>
      <td className="py-3 px-3 text-right tabular-nums text-sm text-zinc-700">
        {fmt(op.quantity, 0)}
      </td>
      <td className="py-3 px-3 text-right tabular-nums text-sm">
        <div className="text-zinc-900">R$ {fmt(op.entry_price)}</div>
        <div className="text-[10px] text-zinc-400">{fmtDate(op.entry_date)}</div>
      </td>
      <td className="py-3 px-3 text-right tabular-nums text-xs text-zinc-500">
        {op.target_price != null ? `R$ ${fmt(op.target_price)}` : "—"}
      </td>
      <td className="py-3 px-3 text-right tabular-nums text-xs text-zinc-500">
        {op.stop_price != null ? `R$ ${fmt(op.stop_price)}` : "—"}
      </td>
      <td className="py-3 px-3 text-right tabular-nums text-sm text-zinc-700">
        {currentPrice != null ? `R$ ${fmt(currentPrice)}` : "—"}
      </td>
      <td className={`py-3 px-3 text-right tabular-nums text-sm font-semibold ${pnlColor(pnlPct)}`}>
        {pnlPct != null ? `${pnlPct >= 0 ? "+" : ""}${fmt(pnlPct)}%` : "—"}
      </td>
      <td className={`py-3 px-3 text-right tabular-nums text-sm font-semibold ${pnlColor(pnlBrl)}`}>
        {pnlBrl != null ? `R$ ${fmt(pnlBrl)}` : "—"}
      </td>
      <td className="py-3 px-3 text-center text-xs text-zinc-500 tabular-nums">
        {op.days_open != null ? op.days_open : "—"}
      </td>
      <td className="py-3 px-3 w-24">
        <ProgressBar pct={op.target_progress_pct} />
      </td>
      <td className="py-3 px-3 text-center">
        {op.status === "open" ? (
          <div className="flex items-center justify-center gap-1">
            <button
              onClick={() => onClose(op)}
              disabled={isClosing}
              className="text-xs px-2 py-1 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 active:scale-[0.97] transition-all duration-150 disabled:opacity-50"
            >
              Fechar
            </button>
            <button
              onClick={() => onDelete(op)}
              disabled={isDeleting}
              className="flex items-center justify-center h-6 w-6 rounded-md bg-zinc-50 text-zinc-400 border border-zinc-200 hover:bg-red-50 hover:text-red-500 hover:border-red-200 active:scale-[0.97] transition-all duration-150 disabled:opacity-50"
              aria-label="Remover operação"
            >
              <X size={11} weight="bold" />
            </button>
          </div>
        ) : (
          <button
            onClick={() => onDelete(op)}
            disabled={isDeleting}
            className="flex items-center justify-center h-6 w-6 rounded-md bg-zinc-50 text-zinc-400 border border-zinc-200 hover:bg-red-50 hover:text-red-500 hover:border-red-200 active:scale-[0.97] transition-all duration-150 disabled:opacity-50 mx-auto"
            aria-label="Remover operação"
          >
            <X size={11} weight="bold" />
          </button>
        )}
      </td>
    </motion.tr>
  );
}

// ─── Table skeleton ──────────────────────────────────────────────────────────

function TableSkeleton() {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-5 space-y-3">
      <ShimmerSkeleton className="h-4 w-36" />
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <ShimmerSkeleton key={i} className="h-10 rounded-lg" />
        ))}
      </div>
    </div>
  );
}

// ─── Operations table ────────────────────────────────────────────────────────

function OperationsTable({
  title,
  rows,
  emptyMessage,
  onClose,
  onDelete,
  isClosing,
  isDeleting,
}: {
  title: string;
  rows: SwingOperation[];
  emptyMessage: string;
  onClose: (op: SwingOperation) => void;
  onDelete: (op: SwingOperation) => void;
  isClosing: boolean;
  isDeleting: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-xl border border-zinc-200 bg-white shadow-sm overflow-hidden"
    >
      <div className="px-4 py-3 border-b border-zinc-100 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-800">{title}</h3>
        <span className="text-xs text-zinc-400">{rows.length} operação(ões)</span>
      </div>
      {rows.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-10 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-50 border border-zinc-200">
            <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5 text-zinc-400" aria-hidden>
              <path d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <p className="text-sm font-medium text-zinc-700">{emptyMessage.split(".")[0]}.</p>
            <p className="text-xs text-zinc-400 mt-0.5">As operações aparecem aqui quando registradas.</p>
          </div>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-100">
                {["Ticker", "Qtd", "Entrada", "Alvo", "Stop", "Preço Atual", "P&L %", "P&L R$", "Dias", "Progresso", "Ações"].map((h, i) => (
                  <th
                    key={h}
                    className={`py-2.5 px-3 text-[10px] font-semibold uppercase tracking-wider text-zinc-400 ${
                      i === 0 ? "text-left" : i >= 9 ? "text-center" : "text-right"
                    }`}
                    dangerouslySetInnerHTML={{ __html: h }}
                  />
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((op, i) => (
                <OperationRow
                  key={op.id}
                  op={op}
                  index={i}
                  onClose={onClose}
                  onDelete={onDelete}
                  isClosing={isClosing}
                  isDeleting={isDeleting}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </motion.div>
  );
}

// ─── OperationsSection (public export) ───────────────────────────────────────

export function OperationsSection({
  data,
  isLoading,
  onCreate,
  onClose,
  onDelete,
  createPending,
  closePending,
  deletePending,
}: {
  data: OperationListResponse | undefined;
  isLoading: boolean;
  onCreate: (payload: import("../types").OperationCreatePayload) => Promise<unknown>;
  onClose: (id: string, exitPrice: number) => Promise<unknown>;
  onDelete: (id: string) => Promise<unknown>;
  createPending: boolean;
  closePending: boolean;
  deletePending: boolean;
}) {
  const [modalOpen, setModalOpen] = useState(false);
  const [showClosed, setShowClosed] = useState(false);

  const { openOps, closedOps } = useMemo(() => {
    const results = data?.results ?? [];
    return {
      openOps: results.filter((op) => op.status === "open"),
      closedOps: results.filter((op) => op.status !== "open"),
    };
  }, [data]);

  async function handleCloseOp(op: SwingOperation) {
    const input = window.prompt(
      `Informe o preço de saída para ${op.ticker}:`,
      op.current_price != null ? String(op.current_price) : "",
    );
    if (!input) return;
    const exitPrice = Number(input);
    if (!Number.isFinite(exitPrice) || exitPrice <= 0) {
      window.alert("Preço de saída inválido.");
      return;
    }
    try {
      await onClose(op.id, exitPrice);
    } catch (err) {
      window.alert(err instanceof Error ? err.message : "Erro ao fechar operação.");
    }
  }

  async function handleDeleteOp(op: SwingOperation) {
    if (!window.confirm(`Remover a operação ${op.ticker} (${op.status})? Esta ação é reversível apenas manualmente.`)) return;
    try {
      await onDelete(op.id);
    } catch (err) {
      window.alert(err instanceof Error ? err.message : "Erro ao remover operação.");
    }
  }

  if (isLoading) return <TableSkeleton />;

  return (
    <div className="space-y-4">
      {/* Header bar */}
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.28 }}
        className="flex items-center justify-between"
      >
        <div className="text-sm text-zinc-500">
          <span className="font-semibold text-zinc-900">{data?.open_count ?? 0}</span>{" "}
          em aberto ·{" "}
          <span className="font-semibold text-zinc-900">{data?.closed_count ?? 0}</span>{" "}
          fechadas
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold bg-blue-600 text-white hover:bg-blue-700 active:scale-[0.97] transition-all duration-150"
        >
          <Plus size={14} weight="bold" aria-hidden />
          Nova Operação
        </button>
      </motion.div>

      <OperationsTable
        title="Operações em Aberto"
        rows={openOps}
        emptyMessage="Nenhuma operação em aberto. Clique em 'Nova Operação' para registrar a primeira."
        onClose={handleCloseOp}
        onDelete={handleDeleteOp}
        isClosing={closePending}
        isDeleting={deletePending}
      />

      <div>
        <button
          onClick={() => setShowClosed((s) => !s)}
          className="text-xs text-zinc-500 hover:text-zinc-800 underline decoration-zinc-300 hover:decoration-zinc-600 active:scale-[0.97] transition-all duration-150"
        >
          {showClosed ? "Ocultar" : "Mostrar"} operações fechadas ({closedOps.length})
        </button>
      </div>

      <AnimatePresence>
        {showClosed && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          >
            <OperationsTable
              title="Operações Fechadas"
              rows={closedOps}
              emptyMessage="Nenhuma operação fechada ainda."
              onClose={handleCloseOp}
              onDelete={handleDeleteOp}
              isClosing={closePending}
              isDeleting={deletePending}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <NewOperationModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={onCreate}
        isPending={createPending}
      />
    </div>
  );
}
