"use client";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, CheckCircle, Warning } from "@phosphor-icons/react";
import type { OutcomeClosePayload, SignalOutcome } from "../types";

interface Props {
  outcome: SignalOutcome | null;
  onClose: () => void;
  onConfirm: (id: string, payload: OutcomeClosePayload) => void;
  isPending: boolean;
}

function computeR(entry: string, stop: string, exit: number): number | null {
  const e = parseFloat(entry);
  const s = parseFloat(stop);
  const risk = e - s;
  if (Math.abs(risk) < 0.0001) return null;
  return (exit - e) / risk;
}

export function CloseOutcomeModal({ outcome, onClose, onConfirm, isPending }: Props) {
  const [exitPrice, setExitPrice] = useState("");
  const [status, setStatus] = useState<"closed" | "stopped">("closed");

  useEffect(() => {
    if (outcome) {
      setExitPrice("");
      setStatus("closed");
    }
  }, [outcome]);

  const preview = exitPrice
    ? computeR(outcome?.entry_price ?? "0", outcome?.stop_price ?? "0", parseFloat(exitPrice))
    : null;

  const previewColor =
    preview == null ? "text-zinc-400" :
    preview > 0 ? "text-emerald-600" :
    "text-red-500";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!outcome || !exitPrice) return;
    onConfirm(outcome.id, {
      exit_price: parseFloat(exitPrice),
      status,
    });
  };

  return (
    <AnimatePresence>
      {outcome && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/30 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="relative z-10 w-full max-w-sm rounded-2xl border border-zinc-200 bg-white shadow-xl p-6"
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Encerrar</p>
                <h3 className="text-lg font-bold text-zinc-900">
                  {outcome.ticker}
                  <span className="ml-2 text-sm font-normal text-zinc-500">
                    {outcome.direction === "long" ? "Compra" : "Venda"}
                  </span>
                </h3>
                <p className="text-sm text-zinc-400 mt-0.5">
                  Entrada: R$ {parseFloat(outcome.entry_price).toFixed(2)} · Stop: R$ {parseFloat(outcome.stop_price).toFixed(2)}
                </p>
              </div>
              <button
                onClick={onClose}
                className="ml-4 p-1.5 rounded-lg text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 transition-colors"
              >
                <X size={18} aria-label="Fechar" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Exit price */}
              <div>
                <label className="block text-xs font-semibold text-zinc-600 mb-1.5">
                  Preço de saída (R$)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  placeholder="Ex: 35.40"
                  value={exitPrice}
                  onChange={(e) => setExitPrice(e.target.value)}
                  className="w-full rounded-lg border border-zinc-300 px-3 py-2.5 text-sm font-mono text-zinc-900 placeholder:text-zinc-300 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
                  autoFocus
                  required
                />
                {/* R-multiple preview */}
                <p className={`text-xs mt-1.5 font-semibold ${previewColor}`}>
                  {preview != null
                    ? `R múltiplo: ${preview > 0 ? "+" : ""}${preview.toFixed(2)}R`
                    : exitPrice
                    ? "—"
                    : "Digite o preço para ver o R"}
                </p>
              </div>

              {/* Status selector */}
              <div>
                <p className="text-xs font-semibold text-zinc-600 mb-2">Tipo de encerramento</p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setStatus("closed")}
                    className={`flex-1 flex items-center justify-center gap-1.5 rounded-lg border py-2 text-sm font-medium transition-colors active:scale-[0.98] ${
                      status === "closed"
                        ? "border-emerald-500 bg-emerald-50 text-emerald-700"
                        : "border-zinc-200 text-zinc-500 hover:border-zinc-300"
                    }`}
                  >
                    <CheckCircle size={15} weight={status === "closed" ? "fill" : "regular"} aria-hidden />
                    Alvo atingido
                  </button>
                  <button
                    type="button"
                    onClick={() => setStatus("stopped")}
                    className={`flex-1 flex items-center justify-center gap-1.5 rounded-lg border py-2 text-sm font-medium transition-colors active:scale-[0.98] ${
                      status === "stopped"
                        ? "border-red-400 bg-red-50 text-red-600"
                        : "border-zinc-200 text-zinc-500 hover:border-zinc-300"
                    }`}
                  >
                    <Warning size={15} weight={status === "stopped" ? "fill" : "regular"} aria-hidden />
                    Stop acionado
                  </button>
                </div>
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={!exitPrice || isPending}
                className="w-full rounded-xl bg-zinc-900 py-3 text-sm font-semibold text-white transition-all hover:bg-zinc-800 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isPending ? "Registrando..." : "Confirmar encerramento"}
              </button>
            </form>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
