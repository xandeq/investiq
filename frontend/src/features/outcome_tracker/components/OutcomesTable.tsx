"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowUp, ArrowDown, Lock, Target } from "@phosphor-icons/react";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import type { OutcomeStatus, SignalOutcome } from "../types";

interface Props {
  outcomes: SignalOutcome[];
  isLoading: boolean;
  isError: boolean;
  onClose: (outcome: SignalOutcome) => void;
  closePending: boolean;
}

type FilterTab = "all" | OutcomeStatus;

const TABS: { key: FilterTab; label: string }[] = [
  { key: "all",     label: "Todos" },
  { key: "open",    label: "Abertos" },
  { key: "closed",  label: "Fechados" },
  { key: "stopped", label: "Stopados" },
];

function RBadge({ r }: { r: string | null }) {
  if (!r) return <span className="text-zinc-300 text-xs font-mono">—</span>;
  const v = parseFloat(r);
  const positive = v > 0;
  return (
    <span
      className={`inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-xs font-bold font-mono tabular-nums ${
        positive ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-600"
      }`}
    >
      {positive ? <ArrowUp size={10} weight="bold" aria-hidden /> : <ArrowDown size={10} weight="bold" aria-hidden />}
      {positive ? "+" : ""}{v.toFixed(2)}R
    </span>
  );
}

function StatusDot({ status }: { status: OutcomeStatus }) {
  const map: Record<OutcomeStatus, { cls: string; label: string }> = {
    open:    { cls: "bg-blue-400",    label: "Aberto" },
    closed:  { cls: "bg-emerald-500", label: "Fechado" },
    stopped: { cls: "bg-red-400",     label: "Stopado" },
  };
  const { cls, label } = map[status];
  return (
    <span className="flex items-center gap-1.5">
      <span className={`inline-block h-1.5 w-1.5 rounded-full ${cls}`} aria-hidden />
      <span className="text-xs text-zinc-500">{label}</span>
    </span>
  );
}

function OutcomeRow({
  outcome,
  index,
  onClose,
  closePending,
}: {
  outcome: SignalOutcome;
  index: number;
  onClose: () => void;
  closePending: boolean;
}) {
  const entry = parseFloat(outcome.entry_price);
  const stop  = parseFloat(outcome.stop_price);
  const t1    = outcome.target_1 ? parseFloat(outcome.target_1) : null;
  const isLong = outcome.direction === "long";

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1], delay: index * 0.035 }}
      className="flex items-center gap-3 border-t border-zinc-100 py-3 first:border-t-0"
    >
      {/* Ticker + direction */}
      <div className="w-28 shrink-0">
        <div className="flex items-center gap-1.5">
          <span
            className={`inline-block w-4 h-4 rounded-sm text-[9px] font-bold flex items-center justify-center ${
              isLong ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-600"
            }`}
            aria-label={isLong ? "Long" : "Short"}
          >
            {isLong ? "L" : "S"}
          </span>
          <span className="text-sm font-bold text-zinc-900 font-mono">{outcome.ticker}</span>
        </div>
        {outcome.pattern && (
          <span className="text-[10px] text-zinc-400 mt-0.5 block">{outcome.pattern}</span>
        )}
      </div>

      {/* Prices */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3 text-xs text-zinc-500 font-mono tabular-nums">
          <span>E: <strong className="text-zinc-700">{entry.toFixed(2)}</strong></span>
          <span>S: <strong className="text-zinc-700">{stop.toFixed(2)}</strong></span>
          {t1 && <span><Target size={10} className="inline mr-0.5" aria-hidden /><strong className="text-zinc-700">{t1.toFixed(2)}</strong></span>}
        </div>
        <StatusDot status={outcome.status} />
      </div>

      {/* R-multiple or close button */}
      <div className="shrink-0 flex items-center gap-2">
        {outcome.status !== "open" ? (
          <RBadge r={outcome.r_multiple} />
        ) : (
          <button
            onClick={onClose}
            disabled={closePending}
            className="flex items-center gap-1 rounded-lg border border-zinc-200 px-2.5 py-1 text-xs font-semibold text-zinc-600 hover:border-zinc-300 hover:bg-zinc-50 active:scale-[0.97] transition-all disabled:opacity-40"
          >
            <Lock size={11} aria-hidden />
            Fechar
          </button>
        )}
        {outcome.signal_grade && (
          <span className="inline-flex items-center justify-center w-6 h-6 rounded-md bg-zinc-100 text-xs font-bold text-zinc-600">
            {outcome.signal_grade}
          </span>
        )}
      </div>
    </motion.div>
  );
}

export function OutcomesTable({ outcomes, isLoading, isError, onClose, closePending }: Props) {
  const [filter, setFilter] = useState<FilterTab>("all");

  const filtered = filter === "all"
    ? outcomes
    : outcomes.filter((o) => o.status === filter);

  const counts: Record<FilterTab, number> = {
    all: outcomes.length,
    open: outcomes.filter((o) => o.status === "open").length,
    closed: outcomes.filter((o) => o.status === "closed").length,
    stopped: outcomes.filter((o) => o.status === "stopped").length,
  };

  return (
    <div className="rounded-xl border border-zinc-200 bg-white overflow-hidden">
      {/* Filter tabs */}
      <div className="flex border-b border-zinc-100">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            className={`relative flex items-center gap-1.5 px-3 py-2.5 text-xs font-semibold active:scale-[0.97] transition-all duration-150 ${
              filter === tab.key ? "text-zinc-900" : "text-zinc-400 hover:text-zinc-600"
            }`}
          >
            {tab.label}
            {counts[tab.key] > 0 && (
              <span className={`rounded-full px-1.5 py-px text-[10px] ${
                filter === tab.key ? "bg-zinc-900 text-white" : "bg-zinc-100 text-zinc-500"
              }`}>
                {counts[tab.key]}
              </span>
            )}
            {filter === tab.key && (
              <motion.span
                layoutId="outcome-tab-indicator"
                className="absolute bottom-0 left-0 right-0 h-0.5 bg-zinc-900 rounded-full"
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
              />
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="px-4 py-1">
        {isLoading && (
          <div className="space-y-3 py-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3 border-t border-zinc-100 py-3 first:border-t-0">
                <ShimmerSkeleton className="h-4 w-20" />
                <div className="flex-1 space-y-1.5">
                  <ShimmerSkeleton className="h-3 w-40" />
                  <ShimmerSkeleton className="h-3 w-16" />
                </div>
                <ShimmerSkeleton className="h-6 w-16" />
              </div>
            ))}
          </div>
        )}

        {isError && (
          <div className="py-6 text-center">
            <p className="text-sm text-red-500">Erro ao carregar resultados.</p>
          </div>
        )}

        {!isLoading && !isError && filtered.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center gap-3 py-10 text-center"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-50 border border-zinc-200">
              <Target size={20} className="text-zinc-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-zinc-700">
                {filter === "all"
                  ? "Nenhum resultado registrado ainda."
                  : `Nenhum resultado ${filter === "open" ? "aberto" : filter === "closed" ? "fechado" : "stopado"}.`}
              </p>
              <p className="text-xs text-zinc-400 mt-0.5">
                {filter === "all"
                  ? "Use o formulário acima para registrar sua primeira entrada."
                  : "Tente mudar o filtro de status."}
              </p>
            </div>
          </motion.div>
        )}

        {!isLoading && !isError && (
          <AnimatePresence mode="popLayout">
            {filtered.map((outcome, i) => (
              <OutcomeRow
                key={outcome.id}
                outcome={outcome}
                index={i}
                onClose={() => onClose(outcome)}
                closePending={closePending}
              />
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
