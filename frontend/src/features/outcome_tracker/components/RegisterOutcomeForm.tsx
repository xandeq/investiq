"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CaretDown, CaretUp, Plus } from "@phosphor-icons/react";
import type { OutcomeCreatePayload, OutcomeDirection } from "../types";

interface Props {
  onSubmit: (payload: OutcomeCreatePayload) => void;
  isPending: boolean;
}

const PATTERNS = [
  "IFR2", "Pivot de alta", "Rompimento", "Pullback", "Engolfo", "Harami", "Outro",
];

export function RegisterOutcomeForm({ onSubmit, isPending }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [ticker, setTicker] = useState("");
  const [direction, setDirection] = useState<OutcomeDirection>("long");
  const [entryPrice, setEntryPrice] = useState("");
  const [stopPrice, setStopPrice] = useState("");
  const [target1, setTarget1] = useState("");
  const [pattern, setPattern] = useState("");
  const [grade, setGrade] = useState("");

  const risk = entryPrice && stopPrice
    ? (parseFloat(entryPrice) - parseFloat(stopPrice)).toFixed(2)
    : null;

  const riskPct = entryPrice && stopPrice
    ? (((parseFloat(entryPrice) - parseFloat(stopPrice)) / parseFloat(entryPrice)) * 100).toFixed(1)
    : null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticker || !entryPrice || !stopPrice) return;

    onSubmit({
      ticker: ticker.toUpperCase(),
      direction,
      entry_price: parseFloat(entryPrice),
      stop_price: parseFloat(stopPrice),
      ...(target1 ? { target_1: parseFloat(target1) } : {}),
      ...(pattern ? { pattern } : {}),
      ...(grade ? { signal_grade: grade } : {}),
    });

    // Reset
    setTicker("");
    setEntryPrice("");
    setStopPrice("");
    setTarget1("");
    setPattern("");
    setGrade("");
    setExpanded(false);
  };

  return (
    <div className="rounded-xl border border-zinc-200 bg-white overflow-hidden">
      {/* Toggle header */}
      <button
        onClick={() => setExpanded((p) => !p)}
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium text-zinc-700 hover:bg-zinc-50 transition-colors"
      >
        <span className="flex items-center gap-2">
          <Plus size={15} weight="bold" aria-hidden />
          Registrar entrada
        </span>
        {expanded
          ? <CaretUp size={14} className="text-zinc-400" aria-hidden />
          : <CaretDown size={14} className="text-zinc-400" aria-hidden />
        }
      </button>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="overflow-hidden"
          >
            <form onSubmit={handleSubmit} className="border-t border-zinc-100 px-4 pb-4 pt-3 space-y-3">
              {/* Row 1: ticker + direction */}
              <div className="grid grid-cols-3 gap-2">
                <div className="col-span-2">
                  <label className="block text-[10px] font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                    Ativo
                  </label>
                  <input
                    type="text"
                    placeholder="PETR4"
                    value={ticker}
                    onChange={(e) => setTicker(e.target.value.toUpperCase())}
                    maxLength={8}
                    className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm font-mono text-zinc-900 placeholder:text-zinc-300 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors uppercase"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                    Direção
                  </label>
                  <div className="flex gap-1 h-[38px]">
                    {(["long", "short"] as OutcomeDirection[]).map((d) => (
                      <button
                        key={d}
                        type="button"
                        onClick={() => setDirection(d)}
                        className={`flex-1 rounded-lg border text-xs font-semibold transition-colors active:scale-[0.97] ${
                          direction === d
                            ? d === "long"
                              ? "border-emerald-500 bg-emerald-50 text-emerald-700"
                              : "border-red-400 bg-red-50 text-red-600"
                            : "border-zinc-200 text-zinc-500"
                        }`}
                      >
                        {d === "long" ? "L" : "S"}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Row 2: entry / stop / target */}
              <div className="grid grid-cols-3 gap-2">
                {[
                  { label: "Entrada", val: entryPrice, set: setEntryPrice, placeholder: "0.00" },
                  { label: "Stop", val: stopPrice, set: setStopPrice, placeholder: "0.00" },
                  { label: "Alvo 1", val: target1, set: setTarget1, placeholder: "0.00" },
                ].map(({ label, val, set, placeholder }) => (
                  <div key={label}>
                    <label className="block text-[10px] font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                      {label}
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      placeholder={placeholder}
                      value={val}
                      onChange={(e) => set(e.target.value)}
                      className="w-full rounded-lg border border-zinc-200 px-2.5 py-2 text-sm font-mono text-zinc-900 placeholder:text-zinc-300 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
                      required={label !== "Alvo 1"}
                    />
                  </div>
                ))}
              </div>

              {/* Risk preview */}
              {risk && (
                <p className="text-xs text-zinc-400">
                  Risco: R$ {Math.abs(parseFloat(risk)).toFixed(2)} por unidade
                  {riskPct && ` (${Math.abs(parseFloat(riskPct))}%)`}
                </p>
              )}

              {/* Pattern + Grade */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[10px] font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                    Setup
                  </label>
                  <select
                    value={pattern}
                    onChange={(e) => setPattern(e.target.value)}
                    className="w-full rounded-lg border border-zinc-200 px-2.5 py-2 text-sm text-zinc-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
                  >
                    <option value="">Selecionar...</option>
                    {PATTERNS.map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                    Grau do sinal
                  </label>
                  <select
                    value={grade}
                    onChange={(e) => setGrade(e.target.value)}
                    className="w-full rounded-lg border border-zinc-200 px-2.5 py-2 text-sm text-zinc-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
                  >
                    <option value="">Sem grau</option>
                    {["A+", "A", "B", "C"].map((g) => (
                      <option key={g} value={g}>{g}</option>
                    ))}
                  </select>
                </div>
              </div>

              <button
                type="submit"
                disabled={!ticker || !entryPrice || !stopPrice || isPending}
                className="w-full rounded-xl bg-zinc-900 py-2.5 text-sm font-semibold text-white transition-all hover:bg-zinc-800 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isPending ? "Registrando..." : "Registrar entrada"}
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
