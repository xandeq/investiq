"use client";
import { useState } from "react";
import type { DividendPlay, SwingPick } from "../types";

const fmt = (n: number) =>
  n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const confColor: Record<string, string> = {
  alta: "bg-emerald-100 text-emerald-700",
  média: "bg-yellow-100 text-yellow-700",
  baixa: "bg-gray-100 text-gray-500",
};

const prazoBadge: Record<string, string> = {
  dias: "bg-blue-50 text-blue-600",
  semanas: "bg-indigo-50 text-indigo-600",
  meses: "bg-purple-50 text-purple-700",
};

// ---------------------------------------------------------------------------
// Swing Pick Card
// ---------------------------------------------------------------------------

interface SwingPickCardProps {
  pick: SwingPick;
  rank: number;
  onOpen: (pick: SwingPick) => void;
}

function SwingPickCard({ pick, rank, onOpen }: SwingPickCardProps) {
  const potGain = ((pick.stop_gain - pick.entrada) / pick.entrada) * 100;
  const potLoss = ((pick.stop_loss - pick.entrada) / pick.entrada) * 100;
  const rrDisplay = pick.rr >= 1 ? pick.rr.toFixed(1) : "< 1";
  const rrColor = pick.rr >= 3 ? "text-emerald-600" : pick.rr >= 2 ? "text-yellow-600" : "text-gray-500";

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="w-7 h-7 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center">
            {rank}
          </span>
          <div>
            <span className="text-xl font-bold text-gray-900">{pick.ticker}</span>
            <div className="flex gap-1.5 mt-0.5">
              <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${confColor[pick.confianca] ?? "bg-gray-100 text-gray-500"}`}>
                Confiança {pick.confianca}
              </span>
              <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${prazoBadge[pick.prazo] ?? "bg-gray-100 text-gray-600"}`}>
                {pick.prazo}
              </span>
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className={`text-lg font-bold ${rrColor}`}>R/R {rrDisplay}:1</div>
          <div className="text-[11px] text-gray-400">risco/retorno</div>
        </div>
      </div>

      {/* Thesis */}
      <p className="text-sm text-gray-700 mb-4 leading-relaxed">{pick.tese}</p>

      {/* Price levels */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <div className="bg-blue-50 rounded-lg p-2.5 text-center">
          <div className="text-[10px] text-blue-500 font-medium uppercase tracking-wide">Entrada</div>
          <div className="text-sm font-bold text-blue-700">R${fmt(pick.entrada)}</div>
        </div>
        <div className="bg-red-50 rounded-lg p-2.5 text-center">
          <div className="text-[10px] text-red-500 font-medium uppercase tracking-wide">Stop Loss</div>
          <div className="text-sm font-bold text-red-600">R${fmt(pick.stop_loss)}</div>
          <div className="text-[10px] text-red-400">{potLoss.toFixed(1)}%</div>
        </div>
        <div className="bg-emerald-50 rounded-lg p-2.5 text-center">
          <div className="text-[10px] text-emerald-600 font-medium uppercase tracking-wide">Stop Gain</div>
          <div className="text-sm font-bold text-emerald-700">R${fmt(pick.stop_gain)}</div>
          <div className="text-[10px] text-emerald-500">+{potGain.toFixed(1)}%</div>
        </div>
      </div>

      {/* Trigger */}
      <div className="bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 mb-4">
        <span className="text-[11px] text-amber-600 font-semibold">⚡ Gatilho: </span>
        <span className="text-[12px] text-amber-800">{pick.motivo}</span>
      </div>

      {/* CTA */}
      <button
        onClick={() => onOpen(pick)}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold py-2.5 rounded-lg transition-colors"
      >
        Abrir Operação →
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Dividend Play Card
// ---------------------------------------------------------------------------

interface DividendPlayCardProps {
  play: DividendPlay;
  rank: number;
  onOpen: (play: DividendPlay) => void;
}

function DividendPlayCard({ play, rank, onOpen }: DividendPlayCardProps) {
  const potUpside = ((play.alvo_preco - play.entrada) / play.entrada) * 100;
  const potLoss = ((play.stop_loss - play.entrada) / play.entrada) * 100;

  return (
    <div className="bg-white border border-emerald-200 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="w-7 h-7 rounded-full bg-emerald-600 text-white text-xs font-bold flex items-center justify-center">
            {rank}
          </span>
          <div>
            <span className="text-xl font-bold text-gray-900">{play.ticker}</span>
            <div className="flex gap-1.5 mt-0.5">
              <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700">
                💰 {play.dy_estimado}
              </span>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-purple-50 text-purple-600">
                {play.prazo_sugerido}
              </span>
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-emerald-600">+{potUpside.toFixed(1)}%</div>
          <div className="text-[11px] text-gray-400">upside alvo</div>
        </div>
      </div>

      {/* Thesis */}
      <p className="text-sm text-gray-700 mb-4 leading-relaxed">{play.tese}</p>

      {/* Price levels */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <div className="bg-blue-50 rounded-lg p-2.5 text-center">
          <div className="text-[10px] text-blue-500 font-medium uppercase tracking-wide">Entrada até</div>
          <div className="text-sm font-bold text-blue-700">R${fmt(play.entrada)}</div>
        </div>
        <div className="bg-red-50 rounded-lg p-2.5 text-center">
          <div className="text-[10px] text-red-500 font-medium uppercase tracking-wide">Stop</div>
          <div className="text-sm font-bold text-red-600">R${fmt(play.stop_loss)}</div>
          <div className="text-[10px] text-red-400">{potLoss.toFixed(1)}%</div>
        </div>
        <div className="bg-emerald-50 rounded-lg p-2.5 text-center">
          <div className="text-[10px] text-emerald-600 font-medium uppercase tracking-wide">Alvo</div>
          <div className="text-sm font-bold text-emerald-700">R${fmt(play.alvo_preco)}</div>
        </div>
      </div>

      {/* Discount reason */}
      <div className="bg-orange-50 border border-orange-100 rounded-lg px-3 py-2 mb-4">
        <span className="text-[11px] text-orange-600 font-semibold">📉 Desconto: </span>
        <span className="text-[12px] text-orange-800">{play.motivo_desconto}</span>
      </div>

      {/* CTA */}
      <button
        onClick={() => onOpen(play)}
        className="w-full bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold py-2.5 rounded-lg transition-colors"
      >
        Abrir Operação →
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Open Operation Modal (pre-filled)
// ---------------------------------------------------------------------------

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

function OpenOperationModal({ ticker, entry, stopLoss, target, notes, onConfirm, onClose }: OpenOperationModalProps) {
  const [qty, setQty] = useState(1);
  const capital = qty * entry;
  const riskBrl = qty * (entry - stopLoss);
  const gainBrl = qty * (target - entry);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-gray-900">Abrir Operação — {ticker}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
        </div>

        {/* Summary */}
        <div className="grid grid-cols-3 gap-2 mb-5">
          <div className="bg-blue-50 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-blue-500 font-medium">ENTRADA</div>
            <div className="text-sm font-bold text-blue-700">R${fmt(entry)}</div>
          </div>
          <div className="bg-red-50 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-red-500 font-medium">STOP</div>
            <div className="text-sm font-bold text-red-600">R${fmt(stopLoss)}</div>
          </div>
          <div className="bg-emerald-50 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-emerald-600 font-medium">ALVO</div>
            <div className="text-sm font-bold text-emerald-700">R${fmt(target)}</div>
          </div>
        </div>

        {/* Quantity */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Quantidade de ações</label>
          <input
            type="number"
            min={1}
            value={qty}
            onChange={(e) => setQty(Math.max(1, parseInt(e.target.value) || 1))}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Capital at risk summary */}
        <div className="bg-gray-50 rounded-lg p-3 mb-5 space-y-1">
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Capital necessário</span>
            <span className="font-semibold">R${fmt(capital)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-red-500">Risco máximo (stop)</span>
            <span className="font-semibold text-red-600">-R${fmt(riskBrl)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-emerald-600">Ganho potencial (alvo)</span>
            <span className="font-semibold text-emerald-700">+R${fmt(gainBrl)}</span>
          </div>
        </div>

        {/* Notes (pre-filled) */}
        <div className="mb-5">
          <label className="block text-sm font-medium text-gray-700 mb-1">Tese (editável)</label>
          <textarea
            defaultValue={notes}
            id="copilot-notes"
            rows={2}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>

        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 border border-gray-300 text-gray-700 text-sm font-medium py-2.5 rounded-lg hover:bg-gray-50">
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
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold py-2.5 rounded-lg transition-colors"
          >
            Confirmar Operação ✓
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Skeleton loader
// ---------------------------------------------------------------------------

function PickSkeleton() {
  return (
    <div className="bg-white border border-gray-100 rounded-xl p-5 animate-pulse">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-7 h-7 rounded-full bg-gray-200" />
        <div className="flex-1 space-y-1.5">
          <div className="h-5 w-20 bg-gray-200 rounded" />
          <div className="h-3 w-32 bg-gray-100 rounded" />
        </div>
      </div>
      <div className="h-3 bg-gray-100 rounded mb-2 w-full" />
      <div className="h-3 bg-gray-100 rounded mb-4 w-4/5" />
      <div className="grid grid-cols-3 gap-2 mb-4">
        {[1, 2, 3].map((i) => <div key={i} className="h-14 bg-gray-100 rounded-lg" />)}
      </div>
      <div className="h-9 bg-gray-200 rounded-lg" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main CopilotSection export
// ---------------------------------------------------------------------------

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
          {[1, 2, 3].map((i) => <PickSkeleton key={i} />)}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl bg-red-50 border border-red-100 p-6 text-center">
        <div className="text-2xl mb-2">⚠️</div>
        <p className="text-sm text-red-600 font-medium">{error}</p>
        <button onClick={onRefresh} className="mt-3 text-sm text-red-500 underline">
          Tentar novamente
        </button>
      </div>
    );
  }

  const hasContent = swingPicks.length > 0 || dividendPlays.length > 0;

  return (
    <>
      {/* Meta bar */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span>🔍 {universeScanned} ações analisadas</span>
          {fromCache && (
            <span className="text-xs bg-gray-100 text-gray-400 px-2 py-0.5 rounded-full">cache</span>
          )}
        </div>
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700 font-medium disabled:opacity-50"
        >
          {isRefreshing ? (
            <span className="inline-block w-4 h-4 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin" />
          ) : "🔄"} Atualizar análise
        </button>
      </div>

      {!hasContent && (
        <div className="text-center py-12 text-gray-400">
          <div className="text-4xl mb-3">🤖</div>
          <p className="text-base font-medium">Nenhum setup identificado agora</p>
          <p className="text-sm mt-1">O mercado pode estar em fase lateral. Tente atualizar mais tarde.</p>
        </div>
      )}

      {/* Swing Trade Picks */}
      {swingPicks.length > 0 && (
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <h2 className="text-base font-bold text-gray-900">📈 Swing Trade — Top {swingPicks.length} Setups</h2>
            <span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full font-medium">
              dias a semanas
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {swingPicks.map((pick, i) => (
              <SwingPickCard key={pick.ticker} pick={pick} rank={i + 1} onOpen={openSwing} />
            ))}
          </div>
        </div>
      )}

      {/* Dividend Plays */}
      {dividendPlays.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <h2 className="text-base font-bold text-gray-900">💰 Dividendos Baratos — Entrar Agora</h2>
            <span className="text-xs bg-emerald-50 text-emerald-600 px-2 py-0.5 rounded-full font-medium">
              semanas a meses
            </span>
          </div>
          <p className="text-xs text-gray-500 mb-4">
            Ações com desconto técnico que pagam dividendos acima da média. Estratégia: comprar, receber proventos e sair no alvo.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {dividendPlays.map((play, i) => (
              <DividendPlayCard key={play.ticker} play={play} rank={i + 1} onOpen={openDividend} />
            ))}
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <div className="mt-8 bg-gray-50 rounded-lg px-4 py-3 text-[11px] text-gray-400 text-center">
        ⚠️ Análise automatizada baseada em dados técnicos e IA. Não é recomendação formal de investimento.
        Sempre valide o preço no book antes de executar e use stop obrigatório.
      </div>

      {/* Modal */}
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
    </>
  );
}
