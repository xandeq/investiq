"use client";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Warning,
  Tray,
  Info,
  ArrowClockwise,
  TrendDown,
  TrendUp,
  Bell,
  Lightbulb,
  Wallet,
} from "@phosphor-icons/react";
import { useInbox } from "@/features/advisor/hooks/useInbox";
import type { InboxCard, InboxCardKind, InboxSeverity } from "@/features/advisor/types";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

const SEV_STYLES: Record<InboxSeverity, { bg: string; bar: string; iconColor: string }> = {
  alert: { bg: "bg-red-50",   bar: "bg-red-500",   iconColor: "text-red-500" },
  warn:  { bg: "bg-amber-50", bar: "bg-amber-500", iconColor: "text-amber-500" },
  info:  { bg: "bg-blue-50",  bar: "bg-blue-500",  iconColor: "text-blue-500" },
};

const KIND_ICON: Record<InboxCardKind, React.ElementType> = {
  concentration_risk:   Warning,
  low_diversification:  Warning,
  underperformer:       TrendDown,
  no_passive_income:    Lightbulb,
  opportunity_detected: TrendUp,
  insight:              Info,
  watchlist_alert:      Bell,
  swing_signal:         TrendUp,
  cash_parking:         Wallet,
};

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (diff < 1) return "agora";
  if (diff < 60) return `${diff}min`;
  if (diff < 1440) return `${Math.floor(diff / 60)}h`;
  return `${Math.floor(diff / 1440)}d`;
}

function CardRow({ card, index }: { card: InboxCard; index: number }) {
  const cfg = SEV_STYLES[card.severity];
  const Icon = KIND_ICON[card.kind] ?? Info;
  const Wrapper = card.cta ? Link : "div";
  const wrapperProps = card.cta
    ? { href: card.cta.href, className: "block" }
    : ({} as Record<string, never>);

  return (
    <motion.div
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1], delay: index * 0.05 }}
    >
      {/* @ts-expect-error — Wrapper alternates between Link and "div" */}
      <Wrapper {...wrapperProps}>
        <div
          className={`relative flex items-start gap-3 rounded-lg px-3 py-3 overflow-hidden transition-colors ${cfg.bg} ${card.cta ? "hover:brightness-95 cursor-pointer" : ""}`}
        >
          <div className={`absolute left-0 top-0 bottom-0 w-1 rounded-l-lg ${cfg.bar}`} />
          <Icon className={`mt-0.5 h-4 w-4 flex-shrink-0 ${cfg.iconColor}`} aria-hidden />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold text-zinc-900 leading-tight">
                {card.title}
              </span>
              {card.ticker && (
                <span className="text-xs font-mono bg-white/70 border border-zinc-200 rounded px-1.5 py-0.5 text-zinc-600">
                  {card.ticker}
                </span>
              )}
              <span className="text-xs text-zinc-400 ml-auto">{timeAgo(card.created_at)}</span>
            </div>
            <p className="text-xs text-zinc-500 mt-0.5 line-clamp-2">{card.body}</p>
            {card.cta && (
              <span className="text-xs font-medium text-blue-600 mt-1 inline-block">
                {card.cta.label} →
              </span>
            )}
          </div>
        </div>
      </Wrapper>
    </motion.div>
  );
}

export function ActionInbox() {
  const { data, isLoading, isFetching, error, refetch } = useInbox();

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Tray className="h-4 w-4 text-zinc-400" aria-hidden />
          <h3 className="font-semibold text-zinc-900">Próximas ações</h3>
          {data && data.cards.length > 0 && (
            <span className="inline-flex items-center justify-center rounded-full bg-blue-500 text-white text-xs font-bold px-2 h-5 min-w-5">
              {data.cards.length}
            </span>
          )}
          <span className="text-xs text-zinc-400 hidden sm:inline">• 6 fontes agregadas</span>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="p-1.5 rounded-md hover:bg-zinc-100 text-zinc-400 active:scale-[0.97] transition-all duration-150 disabled:opacity-40"
          title="Atualizar"
          aria-label="Atualizar caixa de entrada"
        >
          <ArrowClockwise className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
        </button>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.06 }}
            >
              <ShimmerSkeleton className="h-16 rounded-lg" />
            </motion.div>
          ))}
        </div>
      )}

      {!isLoading && error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <p className="font-medium">Não foi possível carregar suas ações.</p>
          <button
            onClick={() => refetch()}
            className="mt-2 underline hover:no-underline font-medium"
          >
            Tentar novamente
          </button>
        </div>
      )}

      {!isLoading && !error && data && data.cards.length === 0 && (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Tray className="h-8 w-8 text-zinc-200 mb-2" aria-hidden />
          <p className="text-sm text-zinc-400">Sem ações pendentes no momento.</p>
          <p className="text-xs text-zinc-300 mt-1">Atualizamos a cada 15 minutos.</p>
        </div>
      )}

      {!isLoading && !error && data && data.cards.length > 0 && (
        <div className="space-y-2">
          {data.cards.map((card, i) => (
            <CardRow key={card.id} card={card} index={i} />
          ))}
        </div>
      )}

      {data && data.meta.sources_failed.length > 0 && (
        <p className="mt-3 text-[11px] text-zinc-300">
          Algumas fontes ficaram fora ({data.meta.sources_failed.join(", ")}).
        </p>
      )}
    </div>
  );
}
