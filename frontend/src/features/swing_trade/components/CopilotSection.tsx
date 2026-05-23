"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Lightning,
  ArrowClockwise,
  Robot,
  ChartLineUp,
  Coins,
  Warning,
  MagnifyingGlass,
  X,
} from "@phosphor-icons/react";
import type { DividendPlay, SwingPick } from "../types";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

const fmt = (n: number) =>
  n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const confColor: Record<string, string> = {
  alta: "bg-emerald-50 text-emerald-700 border border-emerald-200",
  média: "bg-amber-50 text-amber-700 border border-amber-200",
  baixa: "bg-zinc-100 text-zinc-500 border border-zinc-200",
};

const prazoBadge: Record<string, string> = {
  dias: "bg-blue-50 text-blue-600 border border-blue-200",
  semanas: "bg-indigo-50 text-indigo-600 border border-indigo-200",
  meses: "bg-violet-50 text-violet-700 border border-violet-200",
};

// ─── Swing Pick Card ────────────────────────────────────────────────────────

interface SwingPickCardProps {
  pick: SwingPick;
  rank: number;
  index: number;
  onOpen: (pick: SwingPick) => void;
}

function SwingPickCard({ pick, rank, index, onOpen }: SwingPickCardProps) {
  const potGain = ((pick.stop_gain - pick.entrada) / pick.entrada) * 100;
  const potLoss = ((pick.stop_loss - pick.entrada) / pick.entrada) * 100;
  const rrDisplay = pick.rr >= 1 ? pick.rr.toFixed(1) : "< 1";
  const rrColor =
    pick.rr >= 3
      ? "text-emerald-600"
      : pick.rr >= 2
      ? "text-amber-600"
      : "text-zinc-500";

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.38, ease: [0.16, 1, 0.3, 1], delay: index * 0.06 }}
      whileHover={{ y: -2, boxShadow: "0 8px 28px -8px rgba(0,0,0,0.10)" }}
      className="bg-white border border-zinc-200 rounded-xl p-5 transition-colors"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="w-7 h-7 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center shrink-0 tabular-nums">
            {rank}
          </span>
          <div>
            <span className="text-xl font-bold text-zinc-900 font-mono tracking-tight">
              {pick.ticker}
            </span>
            <div className="flex gap-1.5 mt-0.5">
              <span
                className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${confColor[pick.confianca] ?? "bg-zinc-100 text-zinc-500"}`}
              >
                {pick.confianca}
              </span>
              <span
                className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${prazoBadge[pick.prazo] ?? "bg-zinc-100 text-zinc-600"}`}
              >
                {pick.prazo}
              </span>
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className={`text-lg font-bold tabular-nums ${rrColor}`}>
            R/R {rrDisplay}:1
          </div>
          <div className="text-[11px] text-zinc-400">risco/retorno</div>
        </div>
      </div>

      {/* Thesis */}
      <p className="text-sm text-zinc-600 mb-4 leading-relaxed">{pick.tese}</p>

      {/* Price levels */}
      <div className="grid grid-cols-3 sm:grid-cols-3 gap-2 mb-4">
        <div className="bg-blue-50 rounded-lg p-2.5 text-center">
          <div className="text-[10px] text-blue-500 font-semibold uppercase tracking-wide">Entrada</div>
          <div className="text-sm font-bold text-blue-700 tabular-nums">R${fmt(pick.entrada)}</div>
        </div>
        <div className="bg-red-50 rounded-lg p-2.5 text-center">
          <div className="text-[10px] text-red-500 font-semibold uppercase tracking-wide">Stop</div>
          <div className="text-sm font-bold text-red-600 tabular-nums">R${fmt(pick.stop_loss)}</div>
          <div className="text-[10px] text-red-400 tabular-nums">{potLoss.toFixed(1)}%</div>
        </div>
        <div className="bg-emerald-50 rounded-lg p-2.5 text-center">
          <div className="text-[10px] text-emerald-600 font-semibold uppercase tracking-wide">Alvo</div>
          <div className="text-sm font-bold text-emerald-700 tabular-nums">R${fmt(pick.stop_gain)}</div>
          <div className="text-[10px] text-emerald-500 tabular-nums">+{potGain.toFixed(1)}%</div>
        </div>
      </div>

      {/* Trigger */}
      <div className="bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 mb-4 flex items-start gap-1.5">
        <Lightning size={12} weight="fill" className="text-amber-500 mt-0.5 shrink-0" aria-hidden />
        <span className="text-[12px] text-amber-800 leading-snug">{pick.motivo}</span>
      </div>

      {/* CTA */}
      <button
        onClick={() => onOpen(pick)}
        className="w-full bg-blue-600 hover:bg-blue-700 active:scale-[0.97] text-white text-sm font-semibold py-2.5 rounded-lg transition-all duration-150"
      >
        Abrir Operação
      </button>
    </motion.div>
  );
}

// ─── Dividend Play Card ─────────────────────────────────────────────────────

interface DividendPlayCardProps {
  play: DividendPlay;
  rank: number;
  index: number;
  onOpen: (play: DividendPlay) => void;
}

function DividendPlayCard({ play, rank, index, onOpen }: DividendPlayCardProps) {
  const potUpside = ((play.alvo_preco - play.entrada) / play.entrada) * 100;
  const potLoss = ((play.stop_loss - play.entrada) / play.entrada) * 100;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.38, ease: [0.16, 1, 0.3, 1], delay: index * 0.06 }}
      whileHover={{ y: -2, boxShadow: "0 8px 28px -8px rgba(0,0,0,0.10)" }}
      className="bg-white border border-emerald-200 rounded-xl p-5 transition-colors"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="w-7 h-7 rounded-full bg-emerald-600 text-white text-xs font-bold flex items-center justify-center shrink-0 tabular-nums">
            {rank}
          </span>
          <div>
            <span className="text-xl font-bold text-zinc-900 font-mono tracking-tight">
              {play.ticker}
            </span>
            <div className="flex gap-1.5 mt-0.5">
              <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                DY {play.dy_estimado}
              </span>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-violet-50 text-violet-600 border border-violet-200">
                {play.prazo_sugerido}
              </span>
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-emerald-600 tabular-nums">
            +{potUpside.toFixed(1)}%
          </div>
          <div className="text-[11px] text-zinc-400">upside alvo</div>
        </div>
      </div>

      {/* Thesis */}
      <p className="text-sm text-zinc-600 mb-4 leading-relaxed">{play.tese}</p>

      {/* Price levels */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <div className="bg-blue-50 rounded-lg p-2.5 text-center">
          <div className="text-[10px] text-blue-500 font-semibold uppercase tracking-wide">Entrada</div>
          <div className="text-sm font-bold text-blue-700 tabular-nums">R${fmt(play.entrada)}</div>
        </div>
        <div className="bg-red-50 rounded-lg p-2.5 text-center">
          <div className="text-[10px] text-red-500 font-semibold uppercase tracking-wide">Stop</div>
          <div className="text-sm font-bold text-red-600 tabular-nums">R${fmt(play.stop_loss)}</div>
          <div className="text-[10px] text-red-400 tabular-nums">{potLoss.toFixed(1)}%</div>
        </div>
        <div className="bg-emerald-50 rounded-lg p-2.5 text-center">
          <div className="text-[10px] text-emerald-600 font-semibold uppercase tracking-wide">Alvo</div>
          <div className="text-sm font-bold text-emerald-700 tabular-nums">R${fmt(play.alvo_preco)}</div>
        </div>
      </div>

      {/* Discount reason */}
      <div className="bg-orange-50 border border-orange-100 rounded-lg px-3 py-2 mb-4 flex items-start gap-1.5">
        <Coins size={12} weight="fill" className="text-orange-400 mt-0.5 shrink-0" aria-hidden />
        <span className="text-[12px] text-orange-800 leading-snug">{play.motivo_desconto}</span>
      </div>

      {/* CTA */}
      <button
        onClick={() => onOpen(play)}
        className="w-full bg-emerald-600 hover:bg-emerald-700 active:scale-[0.97] text-white text-sm font-semibold py-2.5 rounded-lg transition-all duration-150"
      >
        Abrir Operação
      </button>
    </motion.div>
  );
}

// ─── Open Operation Modal ───────────────────────────────────────────────────

interface OpenOperationModalProps {
  ticker: string;
  entry: number;
  stopLoss: number;
  target: number;
  notes: string;
  onConfirm: (payload: {
    ticker: string;
    entry_price: number;
    stop_price: number;
    target_price: number;
    notes: string;
    quantity: number;
  }) => void;
  onClose: () => void;
}

function OpenOperationModal({
  ticker, entry, stopLoss, target, notes, onConfirm, onClose,
}: OpenOperationModalProps) {
  const [qty, setQty] = useState(1);
  const capital = qty * entry;
  const riskBrl = qty * (entry - stopLoss);
  const gainBrl = qty * (target - entry);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.18 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.96, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.96, y: 12 }}
        transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
        className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 p-6"
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-zinc-900">
            Abrir Operação —{" "}
            <span className="font-mono text-blue-600">{ticker}</span>
          </h2>
          <button
            onClick={onClose}
            className="flex items-center justify-center h-7 w-7 rounded-full text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 active:scale-[0.97] transition-all duration-150"
            aria-label="Fechar"
          >
            <X size={16} weight="bold" />
          </button>
        </div>

        {/* Summary */}
        <div className="grid grid-cols-3 gap-2 mb-5">
          <div className="bg-blue-50 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-blue-500 font-semibold uppercase">ENTRADA</div>
            <div className="text-sm font-bold text-blue-700 tabular-nums">R${fmt(entry)}</div>
          </div>
          <div className="bg-red-50 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-red-500 font-semibold uppercase">STOP</div>
            <div className="text-sm font-bold text-red-600 tabular-nums">R${fmt(stopLoss)}</div>
          </div>
          <div className="bg-emerald-50 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-emerald-600 font-semibold uppercase">ALVO</div>
            <div className="text-sm font-bold text-emerald-700 tabular-nums">R${fmt(target)}</div>
          </div>
        </div>

        {/* Quantity */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-zinc-700 mb-1">
            Quantidade de ações
          </label>
          <input
            type="number"
            min={1}
            value={qty}
            onChange={(e) => setQty(Math.max(1, parseInt(e.target.value) || 1))}
            className="w-full border border-zinc-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 tabular-nums"
          />
        </div>

        {/* Capital at risk summary */}
        <div className="bg-zinc-50 rounded-lg p-3 mb-5 space-y-1">
          <div className="flex justify-between text-sm">
            <span className="text-zinc-500">Capital necessário</span>
            <span className="font-semibold tabular-nums">R${fmt(capital)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-red-500">Risco máximo (stop)</span>
            <span className="font-semibold text-red-600 tabular-nums">-R${fmt(riskBrl)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-emerald-600">Ganho potencial (alvo)</span>
            <span className="font-semibold text-emerald-700 tabular-nums">+R${fmt(gainBrl)}</span>
          </div>
        </div>

        {/* Notes (pre-filled) */}
        <div className="mb-5">
          <label className="block text-sm font-medium text-zinc-700 mb-1">
            Tese (editável)
          </label>
          <textarea
            defaultValue={notes}
            id="copilot-notes"
            rows={2}
            className="w-full border border-zinc-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 border border-zinc-300 text-zinc-700 text-sm font-medium py-2.5 rounded-lg hover:bg-zinc-50 active:scale-[0.97] transition-all duration-150"
          >
            Cancelar
          </button>
          <button
            onClick={() => {
              const notesEl = document.getElementById("copilot-notes") as HTMLTextAreaElement;
              onConfirm({
                ticker,
                entry_price: entry,
                stop_price: stopLoss,
                target_price: target,
                notes: notesEl?.value ?? notes,
                quantity: qty,
              });
            }}
            className="flex-1 bg-blue-600 hover:bg-blue-700 active:scale-[0.97] text-white text-sm font-semibold py-2.5 rounded-lg transition-all duration-150"
          >
            Confirmar Operação
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ─── Skeleton loader ────────────────────────────────────────────────────────

function PickSkeleton({ index }: { index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: index * 0.06 }}
      className="bg-white border border-zinc-100 rounded-xl p-5 space-y-3"
    >
      <div className="flex items-center gap-3">
        <ShimmerSkeleton className="w-7 h-7 rounded-full" />
        <div className="flex-1 space-y-1.5">
          <ShimmerSkeleton className="h-5 w-20" />
          <ShimmerSkeleton className="h-3 w-32" />
        </div>
      </div>
      <ShimmerSkeleton className="h-3 w-full" />
      <ShimmerSkeleton className="h-3 w-4/5" />
      <div className="grid grid-cols-3 gap-2">
        {[0, 1, 2].map((i) => (
          <ShimmerSkeleton key={i} className="h-14 rounded-lg" />
        ))}
      </div>
      <ShimmerSkeleton className="h-9 rounded-lg" />
    </motion.div>
  );
}

// ─── CopilotSection (public export) ─────────────────────────────────────────

export interface CopilotSectionProps {
  swingPicks: import("../types").SwingPick[];
  dividendPlays: import("../types").DividendPlay[];
  universeScanned: number;
  fromCache: boolean;
  isLoading: boolean;
  error?: string | null;
  onCreateOperation: (payload: {
    ticker: string;
    entry_price: number;
    stop_price: number;
    target_price: number;
    notes: string;
    quantity: number;
  }) => void;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export function CopilotSection({
  swingPicks,
  dividendPlays,
  universeScanned,
  fromCache,
  isLoading,
  error,
  onCreateOperation,
  onRefresh,
  isRefreshing,
}: CopilotSectionProps) {
  const [modal, setModal] = useState<{
    ticker: string;
    entry: number;
    stopLoss: number;
    target: number;
    notes: string;
  } | null>(null);

  const openSwing = (pick: SwingPick) =>
    setModal({
      ticker: pick.ticker,
      entry: pick.entrada,
      stopLoss: pick.stop_loss,
      target: pick.stop_gain,
      notes: pick.tese,
    });

  const openDividend = (play: DividendPlay) =>
    setModal({
      ticker: play.ticker,
      entry: play.entrada,
      stopLoss: play.stop_loss,
      target: play.alvo_preco,
      notes: play.tese,
    });

  const handleConfirm = (payload: Parameters<typeof onCreateOperation>[0]) => {
    onCreateOperation(payload);
    setModal(null);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => (
            <PickSkeleton key={i} index={i} />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-xl bg-red-50 border border-red-100 p-6 text-center"
      >
        <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-red-100">
          <Warning size={20} weight="fill" className="text-red-500" aria-hidden />
        </div>
        <p className="text-sm text-red-600 font-medium">{error}</p>
        <button
          onClick={onRefresh}
          className="mt-3 text-sm text-red-500 underline hover:no-underline"
        >
          Tentar novamente
        </button>
      </motion.div>
    );
  }

  const hasContent = swingPicks.length > 0 || dividendPlays.length > 0;

  return (
    <>
      {/* Meta bar */}
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex items-center justify-between mb-5"
      >
        <div className="flex items-center gap-2 text-sm text-zinc-500">
          <MagnifyingGlass size={14} className="text-zinc-400" aria-hidden />
          <span className="tabular-nums">{universeScanned}</span>
          <span>ações analisadas</span>
          {fromCache && (
            <span className="text-xs bg-zinc-100 text-zinc-400 px-2 py-0.5 rounded-full">
              cache
            </span>
          )}
        </div>
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700 font-medium disabled:opacity-50 active:scale-[0.97] transition-all duration-150"
        >
          <ArrowClockwise
            size={14}
            className={isRefreshing ? "animate-spin" : ""}
            aria-hidden
          />
          Atualizar análise
        </button>
      </motion.div>

      {!hasContent && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="text-center py-12"
        >
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-zinc-50 border border-zinc-200">
            <Robot size={22} className="text-zinc-400" aria-hidden />
          </div>
          <p className="text-base font-medium text-zinc-700">
            Nenhum setup identificado agora
          </p>
          <p className="text-sm text-zinc-400 mt-1">
            O mercado pode estar em fase lateral. Tente atualizar mais tarde.
          </p>
        </motion.div>
      )}

      {/* Swing Trade Picks */}
      {swingPicks.length > 0 && (
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <ChartLineUp size={16} weight="fill" className="text-blue-600" aria-hidden />
            <h2 className="text-base font-bold text-zinc-900">
              Swing Trade — Top {swingPicks.length} Setups
            </h2>
            <span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full font-medium border border-blue-200">
              dias a semanas
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {swingPicks.map((pick, i) => (
              <SwingPickCard key={pick.ticker} pick={pick} rank={i + 1} index={i} onOpen={openSwing} />
            ))}
          </div>
        </div>
      )}

      {/* Dividend Plays */}
      {dividendPlays.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Coins size={16} weight="fill" className="text-emerald-600" aria-hidden />
            <h2 className="text-base font-bold text-zinc-900">
              Dividendos Baratos — Entrar Agora
            </h2>
            <span className="text-xs bg-emerald-50 text-emerald-600 px-2 py-0.5 rounded-full font-medium border border-emerald-200">
              semanas a meses
            </span>
          </div>
          <p className="text-xs text-zinc-400 mb-4 leading-relaxed">
            Ações com desconto técnico que pagam dividendos acima da média. Estratégia: comprar,
            receber proventos e sair no alvo.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {dividendPlays.map((play, i) => (
              <DividendPlayCard key={play.ticker} play={play} rank={i + 1} index={i} onOpen={openDividend} />
            ))}
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4, duration: 0.4 }}
        className="mt-8 bg-zinc-50 rounded-lg px-4 py-3 flex items-start gap-2"
      >
        <Warning size={13} weight="fill" className="text-zinc-400 mt-0.5 shrink-0" aria-hidden />
        <p className="text-[11px] text-zinc-400 leading-relaxed">
          Análise automatizada baseada em dados técnicos e IA. Não é recomendação formal de
          investimento. Sempre valide o preço no book antes de executar e use stop obrigatório.
        </p>
      </motion.div>

      {/* Modal */}
      <AnimatePresence>
        {modal && (
          <OpenOperationModal
            ticker={modal.ticker}
            entry={modal.entry}
            stopLoss={modal.stopLoss}
            target={modal.target}
            notes={modal.notes}
            onConfirm={handleConfirm}
            onClose={() => setModal(null)}
          />
        )}
      </AnimatePresence>
    </>
  );
}
