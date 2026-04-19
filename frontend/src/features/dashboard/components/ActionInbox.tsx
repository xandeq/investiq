"use client";
import Link from "next/link";
import {
  AlertTriangle,
  Inbox,
  Info,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  Bell,
  Lightbulb,
} from "lucide-react";
import { useInbox } from "@/features/advisor/hooks/useInbox";
import type { InboxCard, InboxCardKind, InboxSeverity } from "@/features/advisor/types";

const SEV_STYLES: Record<InboxSeverity, { bg: string; bar: string; iconColor: string; label: string }> = {
  alert: { bg: "bg-red-50",   bar: "bg-red-500",   iconColor: "text-red-500",   label: "Alerta" },
  warn:  { bg: "bg-amber-50", bar: "bg-amber-500", iconColor: "text-amber-500", label: "Atenção" },
  info:  { bg: "bg-blue-50",  bar: "bg-blue-500",  iconColor: "text-blue-500",  label: "Info" },
};

const KIND_ICON: Record<InboxCardKind, React.ElementType> = {
  concentration_risk:    AlertTriangle,
  low_diversification:   AlertTriangle,
  underperformer:        TrendingDown,
  no_passive_income:     Lightbulb,
  opportunity_detected:  TrendingUp,
  insight:               Info,
  watchlist_alert:       Bell,
  swing_signal:          TrendingUp,
};

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (diff < 1) return "agora";
  if (diff < 60) return `${diff}min`;
  if (diff < 1440) return `${Math.floor(diff / 60)}h`;
  return `${Math.floor(diff / 1440)}d`;
}

function CardRow({ card }: { card: InboxCard }) {
  const cfg = SEV_STYLES[card.severity];
  const Icon = KIND_ICON[card.kind] ?? Info;
  const Wrapper = card.cta ? Link : "div";
  // Link href requires non-undefined; fall back to "#" but render <div> instead when no cta.
  const wrapperProps = card.cta
    ? { href: card.cta.href, className: "block" }
    : ({} as Record<string, never>);

  return (
    // @ts-expect-error — Wrapper alternates between Link and "div"; both accept className.
    <Wrapper {...wrapperProps}>
      <div
        className={`relative flex items-start gap-3 rounded-lg px-3 py-3 overflow-hidden transition-colors ${cfg.bg} ${card.cta ? "hover:brightness-95 cursor-pointer" : ""}`}
      >
        <div className={`absolute left-0 top-0 bottom-0 w-1 rounded-l-lg ${cfg.bar}`} />
        <Icon className={`mt-0.5 h-4 w-4 flex-shrink-0 ${cfg.iconColor}`} aria-hidden />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-gray-900 leading-tight">{card.title}</span>
            {card.ticker && (
              <span className="text-xs font-mono bg-white/70 border border-gray-200 rounded px-1.5 py-0.5 text-gray-600">
                {card.ticker}
              </span>
            )}
            <span className="text-xs text-muted-foreground ml-auto">{timeAgo(card.created_at)}</span>
          </div>
          <p className="text-xs text-gray-600 mt-0.5 line-clamp-2">{card.body}</p>
          {card.cta && (
            <span className="text-xs font-medium text-blue-600 mt-1 inline-block">
              {card.cta.label} →
            </span>
          )}
        </div>
      </div>
    </Wrapper>
  );
}

export function ActionInbox() {
  const { data, isLoading, isFetching, error, refetch } = useInbox();

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Inbox className="h-4 w-4 text-gray-500" aria-hidden />
          <h3 className="font-semibold text-gray-900">Próximas ações</h3>
          {data && data.cards.length > 0 && (
            <span className="inline-flex items-center justify-center rounded-full bg-blue-500 text-white text-xs font-bold px-2 h-5 min-w-5">
              {data.cards.length}
            </span>
          )}
          <span className="text-xs text-muted-foreground hidden sm:inline">• 5 fontes agregadas</span>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="p-1.5 rounded-md hover:bg-gray-100 text-muted-foreground transition-colors disabled:opacity-40"
          title="Atualizar"
          aria-label="Atualizar caixa de entrada"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
        </button>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {[1, 2, 3].map((n) => (
            <div key={n} className="h-16 rounded-lg bg-gray-100 animate-pulse" />
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
          <Inbox className="h-8 w-8 text-gray-300 mb-2" aria-hidden />
          <p className="text-sm text-muted-foreground">Sem ações pendentes no momento.</p>
          <p className="text-xs text-muted-foreground mt-1">Atualizamos a cada 15 minutos.</p>
        </div>
      )}

      {!isLoading && !error && data && data.cards.length > 0 && (
        <div className="space-y-2">
          {data.cards.map((card) => (
            <CardRow key={card.id} card={card} />
          ))}
        </div>
      )}

      {data && data.meta.sources_failed.length > 0 && (
        <p className="mt-3 text-[11px] text-muted-foreground">
          Algumas fontes ficaram fora ({data.meta.sources_failed.join(", ")}).
        </p>
      )}
    </div>
  );
}
