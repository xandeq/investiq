"use client";
import { useMemo, useState } from "react";
import type { OperationListResponse, SwingOperation } from "../types";
import { NewOperationModal } from "./NewOperationModal";

function fmt(n: number | null | undefined, decimals = 2): string {
  if (n == null) return "—";
  return n.toLocaleString("pt-BR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("pt-BR");
}

function ProgressBar({ pct }: { pct: number | null }) {
  if (pct == null) {
    return <span className="text-xs text-gray-400">—</span>;
  }
  const clamped = Math.max(0, Math.min(100, pct));
  const barColor =
    clamped >= 100
      ? "bg-green-500"
      : clamped >= 50
        ? "bg-blue-500"
        : "bg-gray-400";
  return (
    <div className="w-full">
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full ${barColor} transition-all`}
          style={{ width: `${clamped}%` }}
        />
      </div>
      <div className="text-[10px] text-gray-500 text-right mt-0.5 tabular-nums">
        {fmt(pct, 0)}%
      </div>
    </div>
  );
}

function OperationRow({
  op,
  onClose,
  onDelete,
  isClosing,
  isDeleting,
}: {
  op: SwingOperation;
  onClose: (op: SwingOperation) => void;
  onDelete: (op: SwingOperation) => void;
  isClosing: boolean;
  isDeleting: boolean;
}) {
  // P&L: use backend-enriched when available, else fall back to exit_price
  // for closed rows, else show "—".
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

  const pnlPctClass =
    pnlPct == null
      ? "text-gray-400"
      : pnlPct >= 0
        ? "text-green-600"
        : "text-red-600";
  const pnlBrlClass =
    pnlBrl == null
      ? "text-gray-400"
      : pnlBrl >= 0
        ? "text-green-600"
        : "text-red-600";

  const statusBadge =
    op.status === "open" ? (
      <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-100 text-blue-700">
        ABERTA
      </span>
    ) : op.status === "closed" ? (
      <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold bg-gray-100 text-gray-600">
        FECHADA
      </span>
    ) : (
      <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold bg-red-100 text-red-700">
        STOP
      </span>
    );

  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
      <td className="py-3 px-3">
        <div className="font-mono font-bold text-sm">{op.ticker}</div>
        <div className="mt-0.5">{statusBadge}</div>
      </td>
      <td className="py-3 px-3 text-right tabular-nums text-sm">
        {fmt(op.quantity, 0)}
      </td>
      <td className="py-3 px-3 text-right tabular-nums text-sm">
        <div>R$ {fmt(op.entry_price)}</div>
        <div className="text-[10px] text-gray-400">
          {fmtDate(op.entry_date)}
        </div>
      </td>
      <td className="py-3 px-3 text-right tabular-nums text-xs text-gray-600">
        {op.target_price != null ? `R$ ${fmt(op.target_price)}` : "—"}
      </td>
      <td className="py-3 px-3 text-right tabular-nums text-xs text-gray-600">
        {op.stop_price != null ? `R$ ${fmt(op.stop_price)}` : "—"}
      </td>
      <td className="py-3 px-3 text-right tabular-nums text-sm">
        {currentPrice != null ? `R$ ${fmt(currentPrice)}` : "—"}
      </td>
      <td
        className={`py-3 px-3 text-right tabular-nums text-sm font-semibold ${pnlPctClass}`}
      >
        {pnlPct != null ? `${fmt(pnlPct)}%` : "—"}
      </td>
      <td
        className={`py-3 px-3 text-right tabular-nums text-sm font-semibold ${pnlBrlClass}`}
      >
        {pnlBrl != null ? `R$ ${fmt(pnlBrl)}` : "—"}
      </td>
      <td className="py-3 px-3 text-center text-xs text-gray-600 tabular-nums">
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
              className="text-xs px-2 py-1 rounded-md bg-green-50 text-green-700 border border-green-200 hover:bg-green-100 disabled:opacity-50"
            >
              Fechar
            </button>
            <button
              onClick={() => onDelete(op)}
              disabled={isDeleting}
              className="text-xs px-2 py-1 rounded-md bg-gray-50 text-gray-500 border border-gray-200 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
              aria-label="Remover operação"
              title="Remover operação"
            >
              ✕
            </button>
          </div>
        ) : (
          <button
            onClick={() => onDelete(op)}
            disabled={isDeleting}
            className="text-xs px-2 py-1 rounded-md bg-gray-50 text-gray-500 border border-gray-200 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
            aria-label="Remover operação"
            title="Remover operação"
          >
            ✕
          </button>
        )}
      </td>
    </tr>
  );
}

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
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
        <span className="text-xs text-gray-500">{rows.length} operação(ões)</span>
      </div>
      {rows.length === 0 ? (
        <div className="p-8 text-center text-sm text-gray-500">
          {emptyMessage}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="text-left py-2 px-3 text-xs font-semibold text-gray-600">
                  Ticker
                </th>
                <th className="text-right py-2 px-3 text-xs font-semibold text-gray-600">
                  Qtd
                </th>
                <th className="text-right py-2 px-3 text-xs font-semibold text-gray-600">
                  Entrada
                </th>
                <th className="text-right py-2 px-3 text-xs font-semibold text-gray-600">
                  Alvo
                </th>
                <th className="text-right py-2 px-3 text-xs font-semibold text-gray-600">
                  Stop
                </th>
                <th className="text-right py-2 px-3 text-xs font-semibold text-gray-600">
                  Preço Atual
                </th>
                <th className="text-right py-2 px-3 text-xs font-semibold text-gray-600">
                  P&amp;L %
                </th>
                <th className="text-right py-2 px-3 text-xs font-semibold text-gray-600">
                  P&amp;L R$
                </th>
                <th className="text-center py-2 px-3 text-xs font-semibold text-gray-600">
                  Dias
                </th>
                <th className="text-center py-2 px-3 text-xs font-semibold text-gray-600">
                  Progresso
                </th>
                <th className="text-center py-2 px-3 text-xs font-semibold text-gray-600">
                  Ações
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((op) => (
                <OperationRow
                  key={op.id}
                  op={op}
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
    </div>
  );
}

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
      window.alert(
        err instanceof Error ? err.message : "Erro ao fechar operação.",
      );
    }
  }

  async function handleDeleteOp(op: SwingOperation) {
    if (
      !window.confirm(
        `Remover a operação ${op.ticker} (${op.status})? Esta ação é reversível apenas manualmente.`,
      )
    ) {
      return;
    }
    try {
      await onDelete(op.id);
    } catch (err) {
      window.alert(
        err instanceof Error ? err.message : "Erro ao remover operação.",
      );
    }
  }

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-8 animate-pulse">
        <div className="h-6 bg-gray-100 rounded w-40 mb-4" />
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-8 bg-gray-100 rounded" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-600">
          <span className="font-semibold text-gray-900">
            {data?.open_count ?? 0}
          </span>{" "}
          em aberto ·{" "}
          <span className="font-semibold text-gray-900">
            {data?.closed_count ?? 0}
          </span>{" "}
          fechadas
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="px-4 py-2 rounded-md text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
        >
          + Nova Operação
        </button>
      </div>

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
          className="text-xs text-gray-600 hover:text-gray-900 underline"
        >
          {showClosed ? "Ocultar" : "Mostrar"} operações fechadas (
          {closedOps.length})
        </button>
      </div>

      {showClosed && (
        <OperationsTable
          title="Operações Fechadas"
          rows={closedOps}
          emptyMessage="Nenhuma operação fechada ainda."
          onClose={handleCloseOp}
          onDelete={handleDeleteOp}
          isClosing={closePending}
          isDeleting={deletePending}
        />
      )}

      <NewOperationModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={onCreate}
        isPending={createPending}
      />
    </div>
  );
}
