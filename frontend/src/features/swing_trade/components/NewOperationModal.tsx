"use client";
import { useState, type FormEvent } from "react";
import type { OperationCreatePayload } from "../types";

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: OperationCreatePayload) => Promise<unknown>;
  isPending: boolean;
}

function todayIso(): string {
  // "YYYY-MM-DD" in local time — good default for <input type="date">.
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

export function NewOperationModal({ open, onClose, onSubmit, isPending }: Props) {
  const [ticker, setTicker] = useState("");
  const [assetClass, setAssetClass] = useState("acao");
  const [quantity, setQuantity] = useState("");
  const [entryPrice, setEntryPrice] = useState("");
  const [entryDate, setEntryDate] = useState(todayIso());
  const [targetPrice, setTargetPrice] = useState("");
  const [stopPrice, setStopPrice] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  function reset() {
    setTicker("");
    setAssetClass("acao");
    setQuantity("");
    setEntryPrice("");
    setEntryDate(todayIso());
    setTargetPrice("");
    setStopPrice("");
    setNotes("");
    setError(null);
  }

  function handleClose() {
    reset();
    onClose();
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    const q = Number(quantity);
    const ep = Number(entryPrice);
    if (!ticker.trim()) {
      setError("Ticker é obrigatório.");
      return;
    }
    if (!Number.isFinite(q) || q <= 0) {
      setError("Quantidade precisa ser um número positivo.");
      return;
    }
    if (!Number.isFinite(ep) || ep <= 0) {
      setError("Preço de entrada precisa ser um número positivo.");
      return;
    }

    const payload: OperationCreatePayload = {
      ticker: ticker.trim().toUpperCase(),
      asset_class: assetClass,
      quantity: q,
      entry_price: ep,
      // Convert YYYY-MM-DD to ISO datetime (midnight local)
      entry_date: new Date(`${entryDate}T00:00:00`).toISOString(),
    };

    if (targetPrice) {
      const tp = Number(targetPrice);
      if (Number.isFinite(tp) && tp > 0) payload.target_price = tp;
    }
    if (stopPrice) {
      const sp = Number(stopPrice);
      if (Number.isFinite(sp) && sp > 0) payload.stop_price = sp;
    }
    if (notes.trim()) {
      payload.notes = notes.trim();
    }

    try {
      await onSubmit(payload);
      reset();
      onClose();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Erro ao criar operação.",
      );
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-lg rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">Nova Operação</h2>
          <button
            type="button"
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600"
            aria-label="Fechar"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Ticker *
              </label>
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="PETR4"
                className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400 uppercase"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Classe
              </label>
              <select
                value={assetClass}
                onChange={(e) => setAssetClass(e.target.value)}
                className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
              >
                <option value="acao">Ação</option>
                <option value="fii">FII</option>
                <option value="bdr">BDR</option>
                <option value="etf">ETF</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Data de Entrada *
              </label>
              <input
                type="date"
                value={entryDate}
                onChange={(e) => setEntryDate(e.target.value)}
                className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Quantidade *
              </label>
              <input
                type="number"
                step="any"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                placeholder="100"
                className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Preço de Entrada *
              </label>
              <input
                type="number"
                step="0.01"
                value={entryPrice}
                onChange={(e) => setEntryPrice(e.target.value)}
                placeholder="32.50"
                className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Preço Alvo
              </label>
              <input
                type="number"
                step="0.01"
                value={targetPrice}
                onChange={(e) => setTargetPrice(e.target.value)}
                placeholder="opcional"
                className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Stop Loss
              </label>
              <input
                type="number"
                step="0.01"
                value={stopPrice}
                onChange={(e) => setStopPrice(e.target.value)}
                placeholder="opcional"
                className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
              />
            </div>

            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Notas
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                placeholder="Tese da operação, fonte do setup..."
                className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
              />
            </div>
          </div>

          {error && (
            <div className="rounded-md bg-red-50 border border-red-100 px-3 py-2 text-xs text-red-600">
              {error}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 rounded-md text-sm text-gray-600 border border-gray-200 hover:bg-gray-50 transition-colors"
              disabled={isPending}
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="px-4 py-2 rounded-md text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isPending ? "Salvando..." : "Criar Operação"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
