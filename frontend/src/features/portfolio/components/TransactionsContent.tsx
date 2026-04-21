"use client";
import { useState } from "react";
import { useSortedData } from "@/hooks/useSort";
import { SortableHeader } from "@/components/ui/SortableHeader";
import {
  useTransactions,
  useCreateTransaction,
  useUpdateTransaction,
  useDeleteTransaction,
  useBulkDeleteTransactions,
} from "@/features/portfolio/hooks/useTransactions";
import type { TransactionResponse, TransactionCreate, TransactionUpdate } from "@/features/portfolio/types";

const ASSET_CLASSES = ["acao", "FII", "renda_fixa", "BDR", "ETF"];
const TX_TYPES = ["buy", "sell", "dividend", "jscp", "amortization"];

const TX_TYPE_LABEL: Record<string, string> = {
  buy: "Compra", sell: "Venda", dividend: "Dividendo", jscp: "JSCP", amortization: "Amortização",
};

const ASSET_LABEL: Record<string, string> = {
  acao: "Ação", FII: "FII", renda_fixa: "Renda Fixa", BDR: "BDR", ETF: "ETF",
};

const TX_BADGE: Record<string, string> = {
  buy: "bg-emerald-100 text-emerald-700",
  sell: "bg-red-100 text-red-600",
  dividend: "bg-blue-100 text-blue-700",
  jscp: "bg-blue-100 text-blue-700",
  amortization: "bg-gray-100 text-gray-600",
};

function fmtDate(d: string) {
  const [y, m, day] = d.split("-");
  return `${day}/${m}/${y}`;
}

function exportToCsv(transactions: TransactionResponse[]) {
  const headers = ["Data", "Ticker", "Tipo", "Classe", "Quantidade", "Preço Unit.", "Total", "Corretagem", "IRRF", "Observações"];
  const rows = transactions.map((tx) => [
    tx.transaction_date,
    tx.ticker,
    TX_TYPE_LABEL[tx.transaction_type] ?? tx.transaction_type,
    ASSET_LABEL[tx.asset_class] ?? tx.asset_class,
    tx.quantity,
    tx.unit_price,
    tx.total_value ?? "",
    tx.brokerage_fee ?? "",
    tx.irrf_withheld ?? "",
    (tx.notes ?? "").replace(/,/g, " "),
  ]);
  const csv = [headers, ...rows].map((r) => r.join(",")).join("\n");
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `transacoes_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function fmtBRL(v: string | null) {
  if (!v) return "—";
  return Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

const INPUT_CLS = "w-full rounded-md bg-gray-100 px-3 py-2 text-sm border-2 border-transparent focus:outline-none focus:bg-white focus:border-blue-500 transition-all duration-200 disabled:opacity-50";
const SELECT_CLS = "w-full rounded-md bg-gray-100 px-3 py-2 text-sm border-2 border-transparent focus:outline-none focus:bg-white focus:border-blue-500 transition-all duration-200";

interface ModalProps {
  initial?: TransactionResponse;
  onClose: () => void;
  onSave: (data: TransactionCreate | TransactionUpdate) => void;
  loading: boolean;
  error?: string;
}

function TransactionModal({ initial, onClose, onSave, loading, error }: ModalProps) {
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({
    ticker: initial?.ticker ?? "",
    asset_class: initial?.asset_class ?? "acao",
    transaction_type: initial?.transaction_type ?? "buy",
    transaction_date: initial?.transaction_date ?? today,
    quantity: initial?.quantity ?? "",
    unit_price: initial?.unit_price ?? "",
    brokerage_fee: initial?.brokerage_fee ?? "",
    notes: initial?.notes ?? "",
    is_exempt: initial?.is_exempt ?? false,
  });

  const set = (k: string, v: string | boolean) => setForm((f) => ({ ...f, [k]: v }));
  const isEdit = !!initial;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      ticker: form.ticker.toUpperCase(),
      asset_class: form.asset_class,
      transaction_type: form.transaction_type,
      transaction_date: form.transaction_date,
      quantity: form.quantity,
      unit_price: form.unit_price,
      brokerage_fee: form.brokerage_fee || null,
      notes: form.notes || null,
      is_exempt: form.is_exempt,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-lg border-2 border-gray-200 w-full max-w-lg">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-base font-bold tracking-tight">
            {isEdit ? "Editar transação" : "Nova transação"}
          </h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground text-xl leading-none transition-colors">×</button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 flex flex-col gap-4">
          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">{error}</p>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Ticker *</label>
              <input required disabled={isEdit} value={form.ticker} onChange={(e) => set("ticker", e.target.value)} placeholder="VALE3" className={INPUT_CLS} />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Data *</label>
              <input required type="date" value={form.transaction_date} onChange={(e) => set("transaction_date", e.target.value)} className={INPUT_CLS} />
            </div>
          </div>

          {!isEdit && (
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Classe *</label>
                <select value={form.asset_class} onChange={(e) => set("asset_class", e.target.value)} className={SELECT_CLS}>
                  {ASSET_CLASSES.map((ac) => <option key={ac} value={ac}>{ASSET_LABEL[ac] ?? ac}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Tipo *</label>
                <select value={form.transaction_type} onChange={(e) => set("transaction_type", e.target.value)} className={SELECT_CLS}>
                  {TX_TYPES.map((t) => <option key={t} value={t}>{TX_TYPE_LABEL[t] ?? t}</option>)}
                </select>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Quantidade *</label>
              <input required type="number" step="any" min="0" value={form.quantity} onChange={(e) => set("quantity", e.target.value)} className={INPUT_CLS} />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Preço unitário (R$) *</label>
              <input required type="number" step="any" min="0" value={form.unit_price} onChange={(e) => set("unit_price", e.target.value)} className={INPUT_CLS} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Corretagem (R$)</label>
              <input type="number" step="any" min="0" value={form.brokerage_fee} onChange={(e) => set("brokerage_fee", e.target.value)} className={INPUT_CLS} />
            </div>
            {form.asset_class === "FII" && (
              <div className="flex items-center gap-2 pt-5">
                <input type="checkbox" id="is_exempt" checked={form.is_exempt} onChange={(e) => set("is_exempt", e.target.checked)} className="rounded" />
                <label htmlFor="is_exempt" className="text-sm text-muted-foreground">Isento de IR (FII)</label>
              </div>
            )}
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Observações</label>
            <input value={form.notes} onChange={(e) => set("notes", e.target.value)} maxLength={500} className={INPUT_CLS} />
          </div>

          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm rounded-md bg-gray-100 hover:bg-gray-200 font-medium transition-all duration-200">
              Cancelar
            </button>
            <button type="submit" disabled={loading} className="px-4 py-2 text-sm rounded-md bg-blue-500 text-white hover:bg-blue-600 font-semibold disabled:opacity-60 transition-all duration-200 hover:scale-[1.02]">
              {loading ? "Salvando..." : isEdit ? "Salvar alterações" : "Adicionar transação"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function DeleteConfirm({ tx, onConfirm, onCancel, loading }: {
  tx: TransactionResponse; onConfirm: () => void; onCancel: () => void; loading: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-lg border-2 border-gray-200 w-full max-w-sm p-6 flex flex-col gap-4">
        <h3 className="text-base font-bold tracking-tight">Excluir transação?</h3>
        <p className="text-sm text-muted-foreground">
          {TX_TYPE_LABEL[tx.transaction_type] ?? tx.transaction_type} de{" "}
          <strong>{tx.ticker}</strong> em {fmtDate(tx.transaction_date)} será removida.
          Esta ação não pode ser desfeita.
        </p>
        <div className="flex gap-2 justify-end">
          <button onClick={onCancel} className="px-4 py-2 text-sm rounded-md bg-gray-100 hover:bg-gray-200 font-medium transition-all duration-200">
            Cancelar
          </button>
          <button onClick={onConfirm} disabled={loading} className="px-4 py-2 text-sm rounded-md bg-red-500 text-white hover:bg-red-600 font-semibold disabled:opacity-60 transition-all duration-200">
            {loading ? "Excluindo..." : "Excluir"}
          </button>
        </div>
      </div>
    </div>
  );
}

function BulkDeleteConfirm({ count, onConfirm, onCancel, loading }: {
  count: number; onConfirm: () => void; onCancel: () => void; loading: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-lg border-2 border-gray-200 w-full max-w-sm p-6 flex flex-col gap-4">
        <h3 className="text-base font-bold tracking-tight">Excluir {count} transaç{count === 1 ? "ão" : "ões"}?</h3>
        <p className="text-sm text-muted-foreground">
          {count === 1
            ? "A transação selecionada será removida permanentemente."
            : `As ${count} transações selecionadas serão removidas permanentemente.`}{" "}
          Esta ação não pode ser desfeita.
        </p>
        <div className="flex gap-2 justify-end">
          <button onClick={onCancel} className="px-4 py-2 text-sm rounded-md bg-gray-100 hover:bg-gray-200 font-medium transition-all duration-200">
            Cancelar
          </button>
          <button onClick={onConfirm} disabled={loading} className="px-4 py-2 text-sm rounded-md bg-red-500 text-white hover:bg-red-600 font-semibold disabled:opacity-60 transition-all duration-200">
            {loading ? "Excluindo..." : `Excluir ${count}`}
          </button>
        </div>
      </div>
    </div>
  );
}

export function TransactionsContent() {
  const [filterTicker, setFilterTicker] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterClass, setFilterClass] = useState("");

  const { data: transactions = [], isLoading } = useTransactions({
    ticker: filterTicker || undefined,
    transaction_type: filterType || undefined,
    asset_class: filterClass || undefined,
  });
  const { sorted: sortedTxs, col: sortCol, dir: sortDir, toggle: sortToggle } = useSortedData(
    transactions as Record<string, unknown>[],
    "transaction_date",
    "desc"
  );

  const createMut = useCreateTransaction();
  const updateMut = useUpdateTransaction();
  const deleteMut = useDeleteTransaction();
  const bulkDeleteMut = useBulkDeleteTransactions();

  const [showNew, setShowNew] = useState(false);
  const [editing, setEditing] = useState<TransactionResponse | null>(null);
  const [deleting, setDeleting] = useState<TransactionResponse | null>(null);
  const [mutError, setMutError] = useState<string>("");

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showBulkDeleteModal, setShowBulkDeleteModal] = useState(false);

  const allSelected = transactions.length > 0 && transactions.every((tx) => selectedIds.has(tx.id));
  const someSelected = selectedIds.size > 0;

  const toggleAll = () => {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(transactions.map((tx) => tx.id)));
    }
  };

  const toggleOne = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleCreate = async (data: TransactionCreate | TransactionUpdate) => {
    setMutError("");
    try {
      await createMut.mutateAsync(data as TransactionCreate);
      setShowNew(false);
    } catch (e) {
      setMutError(e instanceof Error ? e.message : "Erro ao criar transação");
    }
  };

  const handleUpdate = async (data: TransactionCreate | TransactionUpdate) => {
    if (!editing) return;
    setMutError("");
    try {
      await updateMut.mutateAsync({ id: editing.id, data: data as TransactionUpdate });
      setEditing(null);
    } catch (e) {
      setMutError(e instanceof Error ? e.message : "Erro ao atualizar transação");
    }
  };

  const handleDelete = async () => {
    if (!deleting) return;
    try {
      await deleteMut.mutateAsync(deleting.id);
      setDeleting(null);
    } catch {
      setDeleting(null);
    }
  };

  const handleBulkDelete = async () => {
    try {
      await bulkDeleteMut.mutateAsync(Array.from(selectedIds));
      setSelectedIds(new Set());
      setShowBulkDeleteModal(false);
    } catch {
      setShowBulkDeleteModal(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Transações</h2>
          <p className="text-sm text-muted-foreground">Histórico completo da carteira</p>
        </div>
        <div className="flex items-center gap-2">
          {transactions.length > 0 && (
            <button
              onClick={() => exportToCsv(transactions)}
              className="px-3 py-2 text-sm rounded-md bg-gray-100 hover:bg-gray-200 font-medium transition-all duration-200"
              title="Exportar para CSV"
            >
              ↓ CSV
            </button>
          )}
          <button
            onClick={() => { setMutError(""); setShowNew(true); }}
            className="px-4 py-2 text-sm rounded-md bg-blue-500 text-white font-semibold hover:bg-blue-600 hover:scale-105 transition-all duration-200"
          >
            + Nova transação
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <input
          placeholder="Filtrar por ticker"
          value={filterTicker}
          onChange={(e) => setFilterTicker(e.target.value.toUpperCase())}
          className="rounded-md bg-gray-100 px-3 py-1.5 text-sm w-36 border-2 border-transparent focus:outline-none focus:bg-white focus:border-blue-500 transition-all duration-200"
        />
        <select value={filterType} onChange={(e) => setFilterType(e.target.value)} className="rounded-md bg-gray-100 px-3 py-1.5 text-sm border-2 border-transparent focus:outline-none focus:bg-white focus:border-blue-500 transition-all duration-200">
          <option value="">Todos os tipos</option>
          {TX_TYPES.map((t) => <option key={t} value={t}>{TX_TYPE_LABEL[t]}</option>)}
        </select>
        <select value={filterClass} onChange={(e) => setFilterClass(e.target.value)} className="rounded-md bg-gray-100 px-3 py-1.5 text-sm border-2 border-transparent focus:outline-none focus:bg-white focus:border-blue-500 transition-all duration-200">
          <option value="">Todas as classes</option>
          {ASSET_CLASSES.map((ac) => <option key={ac} value={ac}>{ASSET_LABEL[ac] ?? ac}</option>)}
        </select>
        {(filterTicker || filterType || filterClass) && (
          <button onClick={() => { setFilterTicker(""); setFilterType(""); setFilterClass(""); }} className="text-sm text-muted-foreground hover:text-foreground px-2 transition-colors">
            Limpar filtros
          </button>
        )}
      </div>

      {/* Bulk action bar */}
      {someSelected && (
        <div className="flex items-center gap-3 px-4 py-2.5 bg-blue-50 border border-blue-200 rounded-lg">
          <span className="text-sm font-medium text-blue-700">
            {selectedIds.size} selecionada{selectedIds.size !== 1 ? "s" : ""}
          </span>
          <button
            onClick={() => setShowBulkDeleteModal(true)}
            className="px-3 py-1.5 text-xs rounded-md bg-red-500 text-white font-semibold hover:bg-red-600 transition-all duration-200"
          >
            Excluir selecionadas
          </button>
          <button
            onClick={() => setSelectedIds(new Set())}
            className="text-xs text-blue-600 hover:text-blue-800 transition-colors ml-auto"
          >
            Desmarcar tudo
          </button>
        </div>
      )}

      {/* Table */}
      <div className="rounded-lg bg-white overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-4 py-3 w-10">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={toggleAll}
                    className="rounded cursor-pointer"
                    title="Selecionar tudo"
                  />
                </th>
                <SortableHeader col="transaction_date" label="Data" activeCol={sortCol} dir={sortDir} onSort={sortToggle} className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted-foreground" />
                <SortableHeader col="ticker" label="Ticker" activeCol={sortCol} dir={sortDir} onSort={sortToggle} className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted-foreground" />
                <SortableHeader col="transaction_type" label="Tipo" activeCol={sortCol} dir={sortDir} onSort={sortToggle} className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted-foreground" />
                <SortableHeader col="asset_class" label="Classe" activeCol={sortCol} dir={sortDir} onSort={sortToggle} className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted-foreground" />
                <SortableHeader col="quantity" label="Qtd" activeCol={sortCol} dir={sortDir} onSort={sortToggle} className="text-right px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted-foreground" align="right" />
                <SortableHeader col="unit_price" label="Preço Unit." activeCol={sortCol} dir={sortDir} onSort={sortToggle} className="text-right px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted-foreground" align="right" />
                <SortableHeader col="total_value" label="Total" activeCol={sortCol} dir={sortDir} onSort={sortToggle} className="text-right px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted-foreground" align="right" />
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {isLoading && (
                <tr><td colSpan={9} className="px-4 py-8 text-center text-muted-foreground text-sm">Carregando...</td></tr>
              )}
              {!isLoading && transactions.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-4 py-8 text-center text-muted-foreground text-sm">
                    Nenhuma transação encontrada.{" "}
                    <button onClick={() => setShowNew(true)} className="text-blue-500 hover:text-blue-600 font-medium transition-colors">
                      Adicionar a primeira
                    </button>
                  </td>
                </tr>
              )}
              {sortedTxs.map((tx_) => { const tx = tx_ as TransactionResponse; return (
                <tr key={tx.id} className={`hover:bg-gray-50/50 transition-colors ${selectedIds.has(tx.id) ? "bg-blue-50/40" : ""}`}>
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(tx.id)}
                      onChange={() => toggleOne(tx.id)}
                      className="rounded cursor-pointer"
                    />
                  </td>
                  <td className="px-4 py-3 text-muted-foreground tabular-nums">{fmtDate(tx.transaction_date)}</td>
                  <td className="px-4 py-3 font-mono font-semibold">{tx.ticker}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-bold ${TX_BADGE[tx.transaction_type] ?? "bg-gray-100 text-gray-600"}`}>
                      {TX_TYPE_LABEL[tx.transaction_type] ?? tx.transaction_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">{ASSET_LABEL[tx.asset_class] ?? tx.asset_class}</td>
                  <td className="px-4 py-3 text-right tabular-nums font-medium">{Number(tx.quantity).toLocaleString("pt-BR")}</td>
                  <td className="px-4 py-3 text-right tabular-nums font-medium">{fmtBRL(tx.unit_price)}</td>
                  <td className="px-4 py-3 text-right tabular-nums font-semibold">{fmtBRL(tx.total_value)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 justify-end">
                      <button onClick={() => { setMutError(""); setEditing(tx); }} className="text-xs text-muted-foreground hover:text-foreground px-2 py-1 rounded-md hover:bg-gray-100 transition-all duration-200">
                        Editar
                      </button>
                      <button onClick={() => setDeleting(tx)} className="text-xs text-muted-foreground hover:text-red-500 px-2 py-1 rounded-md hover:bg-red-50 transition-all duration-200">
                        Excluir
                      </button>
                    </div>
                  </td>
                </tr>
              ); })}
            </tbody>
          </table>
        </div>
      </div>

      {showNew && <TransactionModal onClose={() => setShowNew(false)} onSave={handleCreate} loading={createMut.isPending} error={mutError} />}
      {editing && <TransactionModal initial={editing} onClose={() => setEditing(null)} onSave={handleUpdate} loading={updateMut.isPending} error={mutError} />}
      {deleting && <DeleteConfirm tx={deleting} onConfirm={handleDelete} onCancel={() => setDeleting(null)} loading={deleteMut.isPending} />}
      {showBulkDeleteModal && (
        <BulkDeleteConfirm
          count={selectedIds.size}
          onConfirm={handleBulkDelete}
          onCancel={() => setShowBulkDeleteModal(false)}
          loading={bulkDeleteMut.isPending}
        />
      )}
    </div>
  );
}
