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
      {signal !== "neutral" && (
        <span
          className={`h-1.5 w-1.5 rounded-full ${cfg.dot} animate-pulse-dot shrink-0`}
          aria-hidden
        />
      )}
      <Icon size={11} strokeWidth={2.5} aria-hidden />
      {cfg.label}
    </span>
  );
}

// ─── Discount bar ───────────────────────────────────────────────────────────

function DiscountBar({ value }: { value: number }) {
  const pct = Math.min(100, Math.max(0, Math.abs(value)));
  const color =
    value <= -20
      ? "bg-emerald-400"
      : value <= -12
      ? "bg-amber-400"
      : "bg-zinc-300";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1 w-16 rounded-full bg-zinc-100 overflow-hidden shrink-0">
        <motion.div
          className={`h-full rounded-full ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1], delay: 0.05 }}
        />
      </div>
      <span
        className={`tabular-nums font-bold text-xs ${
          value < 0 ? "text-emerald-600" : "text-red-500"
        }`}
      >
        {value < 0 ? "" : "+"}
        {fmt(value)}%
      </span>
    </div>
  );
}

// ─── Row skeleton ───────────────────────────────────────────────────────────

function RadarRowSkeleton({ index }: { index: number }) {
  return (
    <motion.tr
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: index * 0.04 }}
      className="border-b border-zinc-100"
    >
      <td className="py-3 px-4"><ShimmerSkeleton className="h-4 w-14" /></td>
      <td className="py-3 px-4"><ShimmerSkeleton className="h-3 w-32" /></td>
      <td className="py-3 px-4 hidden md:table-cell"><ShimmerSkeleton className="h-3 w-20" /></td>
      <td className="py-3 px-4 text-right"><ShimmerSkeleton className="h-3 w-16 ml-auto" /></td>
      <td className="py-3 px-4 text-right hidden sm:table-cell"><ShimmerSkeleton className="h-3 w-16 ml-auto" /></td>
      <td className="py-3 px-4"><ShimmerSkeleton className="h-3 w-24" /></td>
      <td className="py-3 px-4 text-right hidden sm:table-cell"><ShimmerSkeleton className="h-3 w-10 ml-auto" /></td>
      <td className="py-3 px-4 text-center"><ShimmerSkeleton className="h-5 w-20 rounded-full mx-auto" /></td>
    </motion.tr>
  );
}

// ─── Data row ───────────────────────────────────────────────────────────────

function RadarRow({ item, index }: { item: SwingSignalItem; index: number }) {
  const isBuy = item.signal === "buy";

  return (
    <motion.tr
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{
        duration: 0.32,
        ease: [0.16, 1, 0.3, 1],
        delay: index * 0.04,
      }}
      className={`border-b border-zinc-100 transition-colors ${
        isBuy ? "bg-emerald-50/40 hover:bg-emerald-50" : "hover:bg-zinc-50"
      }`}
    >
      <td className="py-3 px-4">
        <span className="font-mono font-bold text-sm text-zinc-900">
          {item.ticker}
        </span>
      </td>
      <td className="py-3 px-4 text-xs text-zinc-700 max-w-[180px] truncate">
        {item.name}
      </td>
      <td className="py-3 px-4 text-xs text-zinc-400 hidden md:table-cell">
        {item.sector ?? "—"}
      </td>
      <td className="py-3 px-4 text-right tabular-nums text-xs font-medium text-zinc-900">
        R$ {fmt(item.current_price)}
      </td>
      <td className="py-3 px-4 text-right tabular-nums text-xs text-zinc-500 hidden sm:table-cell">
        R$ {fmt(item.high_30d)}
      </td>
      <td className="py-3 px-4">
        <DiscountBar value={item.discount_pct} />
      </td>
      <td className="py-3 px-4 text-right tabular-nums text-xs text-zinc-600 hidden sm:table-cell">
        {item.dy != null ? `${fmt(item.dy)}%` : "—"}
      </td>
      <td className="py-3 px-4 text-center">
        <SignalBadge signal={item.signal} />
      </td>
    </motion.tr>
  );
}

// ─── Empty state ────────────────────────────────────────────────────────────

function RadarEmpty() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="rounded-xl border border-dashed border-zinc-200 bg-white p-12 text-center"
    >
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-zinc-50">
        <svg viewBox="0 0 40 40" fill="none" className="h-7 w-7" aria-hidden>
          <circle cx="20" cy="20" r="13" stroke="#D4D4D8" strokeWidth="1.5" />
          <circle cx="20" cy="20" r="8" stroke="#E4E4E7" strokeWidth="1.5" />
          <circle cx="20" cy="20" r="3" fill="#A1A1AA" />
          <line x1="20" y1="2" x2="20" y2="7" stroke="#D4D4D8" strokeWidth="1.5" strokeLinecap="round" />
          <line x1="20" y1="33" x2="20" y2="38" stroke="#D4D4D8" strokeWidth="1.5" strokeLinecap="round" />
          <line x1="2" y1="20" x2="7" y2="20" stroke="#D4D4D8" strokeWidth="1.5" strokeLinecap="round" />
          <line x1="33" y1="20" x2="38" y2="20" stroke="#D4D4D8" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </div>
      <p className="text-sm font-medium text-zinc-700">
        Nenhuma ação no radar no momento.
      </p>
      <p className="text-xs text-zinc-400 mt-1 max-w-xs mx-auto leading-relaxed">
        O radar monitora ações de alta liquidez e destaca quedas maiores que 12% do topo de 30 dias.
      </p>
    </motion.div>
  );
}

// ─── RadarSection (public export) ───────────────────────────────────────────

export function RadarSection({
  signals,
  isLoading,
}: {
  signals: SwingSignalItem[] | undefined;
  isLoading: boolean;
}) {
  if (!signals && !isLoading) return <RadarEmpty />;

  const sorted = signals
    ? [...signals].sort((a, b) => a.discount_pct - b.discount_pct)
    : [];

  return (
    <div className="rounded-xl border border-zinc-200 bg-white shadow-sm overflow-hidden">
      {/* Summary bar */}
      {!isLoading && sorted.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="px-4 py-2.5 bg-zinc-50 border-b border-zinc-200 flex items-center gap-4 text-xs text-zinc-500"
        >
          <span className="font-medium text-zinc-700 tabular-nums">
            {sorted.length} ativo{sorted.length !== 1 ? "s" : ""} no radar
          </span>
          <span className="text-zinc-300">|</span>
          <span>
            Comprar:{" "}
            <span className="font-semibold text-emerald-600">
              {sorted.filter((s) => s.signal === "buy").length}
            </span>
          </span>
          <span>
            Vender:{" "}
            <span className="font-semibold text-red-500">
              {sorted.filter((s) => s.signal === "sell").length}
            </span>
          </span>
          <span>
            Neutro:{" "}
            <span className="font-semibold text-zinc-500">
              {sorted.filter((s) => s.signal === "neutral").length}
            </span>
          </span>
        </motion.div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-200">
              <th className="text-left py-3 px-4 text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                Ticker
              </th>
              <th className="text-left py-3 px-4 text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                Nome
              </th>
              <th className="text-left py-3 px-4 text-[11px] font-semibold text-zinc-400 uppercase tracking-wider hidden md:table-cell">
                Setor
              </th>
              <th className="text-right py-3 px-4 text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                Preço
              </th>
              <th className="text-right py-3 px-4 text-[11px] font-semibold text-zinc-400 uppercase tracking-wider hidden sm:table-cell">
                Topo 30d
              </th>
              <th className="text-left py-3 px-4 text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                Desconto
              </th>
              <th className="text-right py-3 px-4 text-[11px] font-semibold text-zinc-400 uppercase tracking-wider hidden sm:table-cell">
                DY
              </th>
              <th className="text-center py-3 px-4 text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                Sinal
              </th>
            </tr>
          </thead>
          <tbody>
            {isLoading
              ? Array.from({ length: 8 }).map((_, i) => (
                  <RadarRowSkeleton key={i} index={i} />
                ))
              : sorted.map((item, i) => (
                  <RadarRow key={item.ticker} item={item} index={i} />
                ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
