"use client";
import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowClockwise,
  CheckCircle,
  Lightning,
  Warning,
  TrendUp,
  TrendDown,
  X,
  Timer,
  ChartBar,
  Info,
} from "@phosphor-icons/react";
import { useOpportunities } from "../hooks/useOpportunities";
import type { Opportunity } from "../types";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

// ─── Helpers ───────────────────────────────────────────────────────────────

function fmt(n: number | null, decimals = 2): string {
  if (n == null) return "—";
  return n.toLocaleString("pt-BR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (diff < 1) return "agora";
  if (diff < 60) return `${diff}min atrás`;
  if (diff < 1440) return `${Math.floor(diff / 60)}h atrás`;
  return `${Math.floor(diff / 1440)}d atrás`;
}

function timeUntilRefresh(nextMs: number): string {
  const diff = Math.max(0, Math.floor((nextMs - Date.now()) / 1000));
  if (diff < 60) return `${diff}s`;
  return `${Math.floor(diff / 60)}min`;
}

// ─── Score coloring ────────────────────────────────────────────────────────

interface ScoreTheme {
  /** Card background */
  cardBg: string;
  /** Left accent bar */
  bar: string;
  /** Score pill bg/text */
  scoreBg: string;
  scoreText: string;
  /** Score label */
  label: string;
  /** Icon */
  icon: React.ElementType;
  iconColor: string;
}

function scoreTheme(score: number): ScoreTheme {
  if (score >= 70) {
    return {
      cardBg: "bg-emerald-50 border-emerald-200 hover:border-emerald-300",
      bar: "bg-emerald-500",
      scoreBg: "bg-emerald-100",
      scoreText: "text-emerald-700",
      label: "Alta",
      icon: TrendUp,
      iconColor: "text-emerald-500",
    };
  }
  if (score >= 40) {
    return {
      cardBg: "bg-amber-50 border-amber-200 hover:border-amber-300",
      bar: "bg-amber-500",
      scoreBg: "bg-amber-100",
      scoreText: "text-amber-700",
      label: "Média",
      icon: ChartBar,
      iconColor: "text-amber-500",
    };
  }
  return {
    cardBg: "bg-red-50 border-red-200 hover:border-red-300",
    bar: "bg-red-500",
    scoreBg: "bg-red-100",
    scoreText: "text-red-700",
    label: "Baixa",
    icon: TrendDown,
    iconColor: "text-red-500",
  };
}

const ASSET_LABELS: Record<string, string> = {
  acao: "Ação",
  fii: "FII",
  crypto: "Crypto",
  renda_fixa: "Renda Fixa",
};

const RISK_STYLES: Record<string, string> = {
  baixo: "bg-emerald-100 text-emerald-700",
  medio: "bg-amber-100 text-amber-700",
  alto: "bg-red-100 text-red-700",
  evitar: "bg-zinc-900 text-white",
};

// ─── Score bar ─────────────────────────────────────────────────────────────

function ScoreBar({ score, color }: { score: number; color: string }) {
  return (
    <div className="h-1.5 w-full rounded-full bg-zinc-200 overflow-hidden">
      <motion.div
        className={`h-full rounded-full ${color}`}
        initial={{ width: 0 }}
        animate={{ width: `${score}%` }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
      />
    </div>
  );
}

// ─── Detail Modal ──────────────────────────────────────────────────────────

function DetailModal({
  opp,
  onClose,
}: {
  opp: Opportunity;
  onClose: () => void;
}) {
  const theme = scoreTheme(opp.score);
  const Icon = theme.icon;
  const priceLabel =
    opp.currency === "USD"
      ? `US$ ${fmt(opp.current_price)}`
      : `R$ ${fmt(opp.current_price)}`;

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        {/* Backdrop */}
        <motion.div
          className="absolute inset-0 bg-black/40 backdrop-blur-sm"
          onClick={onClose}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        />

        {/* Panel */}
        <motion.div
          className="relative z-10 w-full max-w-lg rounded-2xl bg-white shadow-2xl overflow-hidden"
          initial={{ opacity: 0, scale: 0.96, y: 16 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 16 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
        >
          {/* Header bar */}
          <div className={`h-1.5 ${theme.bar}`} />

          <div className="p-6">
            {/* Title row */}
            <div className="flex items-start justify-between gap-3 mb-4">
              <div className="flex items-center gap-3">
                <div
                  className={`w-10 h-10 rounded-xl ${theme.scoreBg} flex items-center justify-center`}
                >
                  <Icon
                    className={`h-5 w-5 ${theme.iconColor}`}
                    weight="fill"
                  />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-lg text-zinc-900">
                      {opp.ticker}
                    </span>
                    {opp.risk_level && (
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          RISK_STYLES[opp.risk_level.toLowerCase()] ??
                          "bg-zinc-100 text-zinc-600"
                        }`}
                      >
                        {opp.risk_level}
                      </span>
                    )}
                  </div>
                  {opp.name && (
                    <p className="text-xs text-zinc-400 mt-0.5">{opp.name}</p>
                  )}
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 active:scale-[0.97] transition-all duration-150"
                aria-label="Fechar"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Score */}
            <div className="mb-5">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-medium text-zinc-500">
                  Score de oportunidade
                </span>
                <span
                  className={`text-sm font-bold ${theme.scoreText}`}
                >{`${opp.score}/100 — ${theme.label}`}</span>
              </div>
              <ScoreBar score={opp.score} color={theme.bar} />
            </div>

            {/* Metrics grid */}
            <div className="grid grid-cols-2 gap-3 mb-5">
              {opp.current_price != null && (
                <div className="rounded-lg bg-zinc-50 p-3">
                  <p className="text-xs text-zinc-400 mb-0.5">Preço atual</p>
                  <p className="font-semibold text-sm text-zinc-900">
                    {priceLabel}
                  </p>
                </div>
              )}
              {opp.drop_pct != null && (
                <div className="rounded-lg bg-zinc-50 p-3">
                  <p className="text-xs text-zinc-400 mb-0.5">Variação</p>
                  <p
                    className={`font-semibold text-sm ${
                      opp.drop_pct < 0 ? "text-red-600" : "text-emerald-600"
                    }`}
                  >
                    {opp.drop_pct > 0 ? "+" : ""}
                    {fmt(opp.drop_pct)}%
                  </p>
                </div>
              )}
              {opp.upside_pct != null && (
                <div className="rounded-lg bg-zinc-50 p-3">
                  <p className="text-xs text-zinc-400 mb-0.5">Upside alvo</p>
                  <p className="font-semibold text-sm text-emerald-600">
                    +{fmt(opp.upside_pct)}%
                  </p>
                </div>
              )}
              {opp.recommended_amount_brl != null && (
                <div className="rounded-lg bg-zinc-50 p-3">
                  <p className="text-xs text-zinc-400 mb-0.5">
                    Aporte sugerido
                  </p>
                  <p className="font-semibold text-sm text-zinc-900">
                    R$ {fmt(opp.recommended_amount_brl)}
                  </p>
                </div>
              )}
              <div className="rounded-lg bg-zinc-50 p-3">
                <p className="text-xs text-zinc-400 mb-0.5">Tipo</p>
                <p className="font-semibold text-sm text-zinc-900">
                  {ASSET_LABELS[opp.asset_type] ?? opp.asset_type}
                </p>
              </div>
              <div className="rounded-lg bg-zinc-50 p-3">
                <p className="text-xs text-zinc-400 mb-0.5">Detectado</p>
                <p className="font-semibold text-sm text-zinc-900">
                  {timeAgo(opp.detected_at)}
                </p>
              </div>
            </div>

            {/* Causa */}
            {opp.cause_explanation && (
              <div className="rounded-lg border border-zinc-100 bg-zinc-50 p-4">
                <div className="flex items-center gap-1.5 mb-2">
                  <Info className="h-3.5 w-3.5 text-zinc-400" />
                  <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">
                    Análise
                  </span>
                </div>
                <p className="text-sm text-zinc-700 leading-relaxed">
                  {opp.cause_explanation}
                </p>
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

// ─── Opportunity Card ──────────────────────────────────────────────────────

function OpportunityCard({
  opp,
  index,
  onClick,
}: {
  opp: Opportunity;
  index: number;
  onClick: () => void;
}) {
  const theme = scoreTheme(opp.score);
  const Icon = theme.icon;
  const priceLabel =
    opp.currency === "USD"
      ? `US$ ${fmt(opp.current_price)}`
      : `R$ ${fmt(opp.current_price)}`;

  return (
    <motion.button
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.35,
        ease: [0.16, 1, 0.3, 1],
        delay: index * 0.045,
      }}
      onClick={onClick}
      className={`relative w-full text-left rounded-xl border p-4 overflow-hidden transition-all duration-200 cursor-pointer active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${theme.cardBg}`}
      aria-label={`Ver detalhes de ${opp.ticker}`}
    >
      {/* Left accent bar */}
      <div
        className={`absolute left-0 top-0 bottom-0 w-1 rounded-l-xl ${theme.bar}`}
      />

      {/* Top row */}
      <div className="flex items-start justify-between gap-2 mb-3 pl-1">
        <div className="flex items-center gap-2.5">
          <div
            className={`w-8 h-8 rounded-lg ${theme.scoreBg} flex items-center justify-center shrink-0`}
          >
            <Icon
              className={`h-4 w-4 ${theme.iconColor}`}
              weight="fill"
              aria-hidden
            />
          </div>
          <div>
            <span className="font-mono font-bold text-sm text-zinc-900 block leading-tight">
              {opp.ticker}
            </span>
            {opp.name && (
              <span className="text-xs text-zinc-400 block leading-tight truncate max-w-[100px]">
                {opp.name}
              </span>
            )}
          </div>
        </div>

        {/* Score pill */}
        <span
          className={`text-xs font-bold px-2 py-0.5 rounded-full shrink-0 ${theme.scoreBg} ${theme.scoreText}`}
        >
          {opp.score}
        </span>
      </div>

      {/* Score bar */}
      <div className="pl-1 mb-3">
        <ScoreBar score={opp.score} color={theme.bar} />
      </div>

      {/* Metrics row */}
      <div className="pl-1 flex items-center justify-between gap-2">
        <div className="flex items-center gap-3 text-xs text-zinc-500 flex-wrap">
          {opp.current_price != null && (
            <span className="tabular-nums">{priceLabel}</span>
          )}
          {opp.drop_pct != null && (
            <span
              className={`font-medium ${
                opp.drop_pct < 0 ? "text-red-600" : "text-emerald-600"
              }`}
            >
              {opp.drop_pct > 0 ? "+" : ""}
              {fmt(opp.drop_pct)}%
            </span>
          )}
          {opp.upside_pct != null && (
            <span className="text-emerald-600 font-medium">
              ↑{fmt(opp.upside_pct)}%
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {opp.asset_type && (
            <span className="text-xs text-zinc-400 bg-white/70 border border-zinc-200 rounded px-1.5 py-0.5">
              {ASSET_LABELS[opp.asset_type] ?? opp.asset_type}
            </span>
          )}
        </div>
      </div>

      {/* Time */}
      <p className="pl-1 mt-2 text-xs text-zinc-400">
        {timeAgo(opp.detected_at)}
      </p>
    </motion.button>
  );
}

// ─── Skeleton Cards ────────────────────────────────────────────────────────

function SkeletonCard({ index }: { index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: index * 0.04 }}
      className="rounded-xl border border-zinc-200 bg-white p-4 space-y-3"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <ShimmerSkeleton className="w-8 h-8 rounded-lg" />
          <div className="space-y-1">
            <ShimmerSkeleton className="h-4 w-14" />
            <ShimmerSkeleton className="h-3 w-20" />
          </div>
        </div>
        <ShimmerSkeleton className="h-5 w-8 rounded-full" />
      </div>
      <ShimmerSkeleton className="h-1.5 w-full rounded-full" />
      <div className="flex items-center justify-between">
        <ShimmerSkeleton className="h-3 w-24" />
        <ShimmerSkeleton className="h-4 w-14 rounded" />
      </div>
      <ShimmerSkeleton className="h-3 w-16" />
    </motion.div>
  );
}

// ─── Empty State ───────────────────────────────────────────────────────────

function EmptyState({ onRefresh }: { onRefresh: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="col-span-full flex flex-col items-center justify-center py-20 text-center"
    >
      <div className="w-16 h-16 rounded-2xl bg-zinc-100 flex items-center justify-center mb-4">
        <CheckCircle className="h-8 w-8 text-emerald-400" weight="fill" />
      </div>
      <h3 className="font-semibold text-zinc-700 text-base mb-1">
        Nenhuma oportunidade agora
      </h3>
      <p className="text-sm text-zinc-400 max-w-xs mb-5">
        O scanner analisa o mercado a cada 5 minutos. Tente atualizar ou aguarde
        o próximo ciclo.
      </p>
      <button
        onClick={onRefresh}
        className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 active:scale-[0.97] transition-all duration-150"
      >
        <ArrowClockwise className="h-4 w-4" />
        Atualizar agora
      </button>
    </motion.div>
  );
}

// ─── Error State ───────────────────────────────────────────────────────────

function ErrorState({
  message,
  onRefresh,
}: {
  message: string;
  onRefresh: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="col-span-full rounded-xl bg-red-50 border border-red-100 p-6 text-center"
    >
      <Warning className="h-8 w-8 text-red-400 mx-auto mb-3" weight="fill" />
      <p className="text-sm text-red-700 font-medium mb-1">
        Erro ao carregar oportunidades
      </p>
      <p className="text-xs text-red-500 mb-4">{message}</p>
      <button
        onClick={onRefresh}
        className="px-4 py-2 rounded-lg text-sm font-medium bg-red-600 text-white hover:bg-red-700 active:scale-[0.97] transition-all duration-150"
      >
        Tentar novamente
      </button>
    </motion.div>
  );
}

// ─── Main Grid Component ───────────────────────────────────────────────────

export function OpportunitiesGrid() {
  const [selectedOpp, setSelectedOpp] = useState<Opportunity | null>(null);
  const { data, isLoading, isFetching, error, refetch, dataUpdatedAt } =
    useOpportunities(20);

  const handleClose = useCallback(() => setSelectedOpp(null), []);

  const nextRefreshMs = dataUpdatedAt + 5 * 60 * 1000;

  const items = data?.items ?? [];
  const greenCount = items.filter((o) => o.score >= 70).length;
  const amberCount = items.filter((o) => o.score >= 40 && o.score < 70).length;
  const redCount = items.filter((o) => o.score < 40).length;

  return (
    <>
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 flex items-center gap-2">
            <Lightning className="h-6 w-6 text-blue-500" weight="fill" />
            Oportunidades do Dia
          </h1>
          <p className="text-sm text-zinc-400 mt-0.5">
            Score IA baseado em preço, risco e contexto de mercado. Atualização
            automática a cada 5 min.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {/* Score legend pills */}
          {!isLoading && items.length > 0 && (
            <div className="hidden sm:flex items-center gap-2 text-xs">
              <span className="flex items-center gap-1 bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" />
                Alta ({greenCount})
              </span>
              <span className="flex items-center gap-1 bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 inline-block" />
                Média ({amberCount})
              </span>
              <span className="flex items-center gap-1 bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 inline-block" />
                Baixa ({redCount})
              </span>
            </div>
          )}

          {/* Refresh button + countdown */}
          <div className="flex items-center gap-2">
            {!isLoading && dataUpdatedAt > 0 && (
              <span className="text-xs text-zinc-400 flex items-center gap-1">
                <Timer className="h-3 w-3" />
                Próx. em {timeUntilRefresh(nextRefreshMs)}
              </span>
            )}
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="p-2 rounded-lg text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 disabled:opacity-40 active:scale-[0.97] transition-all duration-150"
              title="Atualizar agora"
              aria-label="Atualizar oportunidades"
            >
              <ArrowClockwise
                className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`}
              />
            </button>
          </div>
        </div>
      </div>

      {/* Refreshing indicator strip */}
      <AnimatePresence>
        {isFetching && !isLoading && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-4 overflow-hidden"
          >
            <div className="rounded-lg bg-blue-50 border border-blue-100 px-4 py-2 text-xs text-blue-600 flex items-center gap-2">
              <ArrowClockwise className="h-3.5 w-3.5 animate-spin" />
              Atualizando oportunidades...
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Bento grid — responsive 1/2/3/4 cols */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 auto-rows-auto">
        {isLoading
          ? Array.from({ length: 12 }).map((_, i) => (
              <SkeletonCard key={i} index={i} />
            ))
          : error
          ? null
          : items.map((opp, i) => (
              <OpportunityCard
                key={opp.id}
                opp={opp}
                index={i}
                onClick={() => setSelectedOpp(opp)}
              />
            ))}

        {!isLoading && !error && items.length === 0 && (
          <EmptyState onRefresh={() => refetch()} />
        )}

        {!isLoading && error && (
          <ErrorState
            message={
              error instanceof Error
                ? error.message
                : "Erro desconhecido"
            }
            onRefresh={() => refetch()}
          />
        )}
      </div>

      {/* Last update footer */}
      {!isLoading && data?.refreshed_at && (
        <p className="mt-6 text-center text-xs text-zinc-400">
          Dados de mercado atualizados em{" "}
          {new Date(data.refreshed_at).toLocaleString("pt-BR", {
            hour: "2-digit",
            minute: "2-digit",
            day: "2-digit",
            month: "2-digit",
          })}
        </p>
      )}

      {/* Detail modal */}
      {selectedOpp && (
        <DetailModal opp={selectedOpp} onClose={handleClose} />
      )}
    </>
  );
}
