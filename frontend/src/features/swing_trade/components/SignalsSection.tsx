"use client";
import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import type { SwingSignalItem } from "../types";

// ─── formatters ────────────────────────────────────────────────────────────

function fmt(n: number | null | undefined, decimals = 2): string {
  if (n == null) return "—";
  return n.toLocaleString("pt-BR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

// ─── signal config ──────────────────────────────────────────────────────────

const SIGNAL_CONFIG: Record<
  string,
  { label: string; pill: string; dot: string; Icon: React.ElementType }
> = {
  buy: {
    label: "COMPRAR",
    pill: "bg-emerald-50 text-emerald-700 border-emerald-200 ring-1 ring-emerald-300/60",
    dot: "bg-emerald-400",
    Icon: TrendingUp,
  },
  sell: {
    label: "VENDER",
    pill: "bg-red-50 text-red-600 border-red-200 ring-1 ring-red-300/60",
    dot: "bg-red-400",
    Icon: TrendingDown,
  },
  neutral: {
    label: "NEUTRO",
    pill: "bg-zinc-100 text-zinc-500 border-zinc-200",
    dot: "bg-zinc-400",
    Icon: Minus,
  },
};

// ─── SignalBadge ────────────────────────────────────────────────────────────

function SignalBadge({ signal }: { signal: string }) {
  const cfg = SIGNAL_CONFIG[signal] ?? SIGNAL_CONFIG.neutral;
  const { Icon } = cfg;
  return (
    <span
      className={`inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full border font-semibold uppercase tracking-wider ${cfg.pill}`}
    >
      {/* Pulse dot only on actionable signals */}
      {signal !== "neutral" && (
        <span
          className={`h-1.5 w-1.5 rounded-full ${cfg.dot} animate-pulse-dot`}
          aria-hidden
        />
      )}
      <Icon size={11} strokeWidth={2.5} aria-hidden />
      {cfg.label}
    </span>
  );
}

// ─── Strength bar ───────────────────────────────────────────────────────────

function StrengthBar({ value }: { value: number }) {
  const pct = Math.min(100, Math.max(0, Math.abs(value)));
  const color =
    value >= 60
      ? "bg-emerald-400"
      : value >= 30
      ? "bg-amber-400"
      : "bg-zinc-300";
  return (
    <div className="h-1 w-full rounded-full bg-zinc-100 overflow-hidden">
      <motion.div
        className={`h-full rounded-full ${color}`}
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
      />
    </div>
  );
}

// ─── SignalCard ─────────────────────────────────────────────────────────────

function SignalCard({ item, index }: { item: SwingSignalItem; index: number }) {
  const isDiscount = item.discount_pct < 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.38,
        ease: [0.16, 1, 0.3, 1],
        delay: index * 0.05,
      }}
      whileHover={{ y: -2, boxShadow: "0 8px 24px -8px rgba(0,0,0,0.10)" }}
      className="rounded-xl border border-zinc-200 bg-white p-4 transition-colors"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="min-w-0">
          <div className="font-mono font-bold text-[15px] text-zinc-900 tracking-tight">
            {item.ticker}
          </div>
          <div className="text-xs text-zinc-500 mt-0.5 truncate max-w-[180px]">
            {item.name}
          </div>
          {item.sector && (
            <div className="text-[10px] text-zinc-400 mt-0.5 uppercase tracking-wider">
              {item.sector}
            </div>
          )}
        </div>
        <SignalBadge signal={item.signal} />
      </div>

      {/* Signal strength bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] font-medium text-zinc-400 uppercase tracking-wider">
            Força do sinal
          </span>
          <span className="text-[10px] font-semibold text-zinc-600 tabular-nums">
            {fmt(item.signal_strength, 0)}%
          </span>
        </div>
        <StrengthBar value={item.signal_strength} />
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2.5 text-xs">
        <div>
          <div className="text-zinc-400 mb-0.5">Preço atual</div>
          <div className="font-semibold text-zinc-900 tabular-nums">
            R$ {fmt(item.current_price)}
          </div>
        </div>
        <div>
          <div className="text-zinc-400 mb-0.5">Topo 30d</div>
          <div className="font-semibold text-zinc-900 tabular-nums">
            R$ {fmt(item.high_30d)}
          </div>
        </div>
        <div>
          <div className="text-zinc-400 mb-0.5">Desconto</div>
          <div
            className={`font-bold tabular-nums ${
              isDiscount ? "text-emerald-600" : "text-red-500"
            }`}
          >
            {isDiscount ? "" : "+"}
            {fmt(item.discount_pct)}%
          </div>
        </div>
        <div>
          <div className="text-zinc-400 mb-0.5">DY anual</div>
          <div className="font-semibold text-zinc-900 tabular-nums">
            {item.dy != null ? `${fmt(item.dy)}%` : "—"}
          </div>
        </div>
      </div>

      {/* Portfolio row */}
      {item.in_portfolio && item.quantity != null && (
        <div className="mt-3 pt-2.5 border-t border-zinc-100 flex items-center justify-between text-xs">
          <span className="text-zinc-400">Em carteira</span>
          <span className="font-semibold text-zinc-700 tabular-nums font-mono">
            {fmt(item.quantity, 0)} cotas
          </span>
        </div>
      )}
    </motion.div>
  );
}

// ─── Loading skeletons ──────────────────────────────────────────────────────

function SignalCardSkeleton({ index }: { index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: index * 0.04 }}
      className="rounded-xl border border-zinc-200 bg-white p-4 space-y-3"
    >
      <div className="flex justify-between">
        <div className="space-y-1.5">
          <ShimmerSkeleton className="h-4 w-16" />
          <ShimmerSkeleton className="h-3 w-28" />
        </div>
        <ShimmerSkeleton className="h-6 w-20 rounded-full" />
      </div>
      <ShimmerSkeleton className="h-1.5 w-full rounded-full" />
      <div className="grid grid-cols-2 gap-3">
        <ShimmerSkeleton className="h-9 rounded-lg" />
        <ShimmerSkeleton className="h-9 rounded-lg" />
        <ShimmerSkeleton className="h-9 rounded-lg" />
        <ShimmerSkeleton className="h-9 rounded-lg" />
      </div>
    </motion.div>
  );
}

// ─── Empty state ────────────────────────────────────────────────────────────

function SignalsEmpty() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="rounded-xl border border-dashed border-zinc-200 bg-white p-12 text-center"
    >
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-zinc-50">
        <svg viewBox="0 0 40 40" fill="none" className="h-7 w-7" aria-hidden>
          <rect x="4" y="10" width="32" height="24" rx="3" fill="#F4F4F5" stroke="#D4D4D8" strokeWidth="1.5" />
          <path d="M10 26 L16 20 L22 23 L30 14" stroke="#A1A1AA" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <p className="text-sm font-medium text-zinc-700">
        Nenhuma posição na carteira para gerar sinais.
      </p>
      <p className="text-xs text-zinc-400 mt-1 max-w-xs mx-auto leading-relaxed">
        Importe suas transações para ver sinais de swing trade das suas ações.
      </p>
    </motion.div>
  );
}

// ─── SignalsSection (public export) ────────────────────────────────────────

export function SignalsSection({
  signals,
  isLoading,
}: {
  signals: SwingSignalItem[] | undefined;
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <SignalCardSkeleton key={i} index={i} />
        ))}
      </div>
    );
  }

  if (!signals || signals.length === 0) return <SignalsEmpty />;

  const sorted = [...signals].sort(
    (a, b) => b.signal_strength - a.signal_strength
  );

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {sorted.map((item, i) => (
        <SignalCard key={item.ticker} item={item} index={i} />
      ))}
    </div>
  );
}
