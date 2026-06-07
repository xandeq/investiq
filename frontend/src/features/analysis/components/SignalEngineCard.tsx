"use client";

/**
 * SignalEngineCard — taste-skill component
 *
 * Displays a BUY / WAIT / SKIP verdict derived from the 10-gate signal engine,
 * Entry / Stop / Target levels, and a perpetually pulsing R:R badge.
 *
 * Data source: GET /api/signals/current?ticker={ticker}
 * Hook:        useSignalCurrent
 *
 * Design rules:
 *   - Glassmorphism card (backdrop-blur + translucent bg)
 *   - Verdict badge drives the accent colour (emerald / amber / zinc)
 *   - R:R badge has a CSS perpetual pulse keyed on verdict state
 *   - Mobile-first, collapses to single-column on <sm
 *   - Strict TypeScript, no implicit any
 */

import { motion } from "framer-motion";
import {
  TrendUp,
  Timer,
  XCircle,
  Target,
  ArrowDown,
  ArrowUp,
  Scales,
} from "@phosphor-icons/react";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import { useSignalCurrent, type SignalVerdict, type SignalCurrentData } from "@/hooks/useSignalCurrent";

// ─── types ──────────────────────────────────────────────────────────────────

interface Props {
  ticker: string;
  /** Opt out of the PremiumGate wrapper when the parent already handles it. */
  standalone?: boolean;
}

// ─── verdict config ──────────────────────────────────────────────────────────

interface VerdictConfig {
  label: string;
  Icon: React.ElementType;
  cardBorder: string;
  cardBg: string;
  badgeBg: string;
  badgeText: string;
  badgeBorder: string;
  accentText: string;
  rrPulseColor: string;
}

const VERDICT_CONFIG: Record<SignalVerdict, VerdictConfig> = {
  BUY: {
    label: "COMPRAR",
    Icon: TrendUp,
    cardBorder: "border-emerald-200",
    cardBg: "bg-emerald-50/40",
    badgeBg: "bg-emerald-500",
    badgeText: "text-white",
    badgeBorder: "border-emerald-600",
    accentText: "text-emerald-700",
    rrPulseColor: "#10b981", // emerald-500
  },
  WAIT: {
    label: "AGUARDAR",
    Icon: Timer,
    cardBorder: "border-amber-200",
    cardBg: "bg-amber-50/40",
    badgeBg: "bg-amber-400",
    badgeText: "text-white",
    badgeBorder: "border-amber-500",
    accentText: "text-amber-700",
    rrPulseColor: "#f59e0b", // amber-400
  },
  SKIP: {
    label: "EVITAR",
    Icon: XCircle,
    cardBorder: "border-zinc-200",
    cardBg: "bg-zinc-50/40",
    badgeBg: "bg-zinc-400",
    badgeText: "text-white",
    badgeBorder: "border-zinc-500",
    accentText: "text-zinc-500",
    rrPulseColor: "#a1a1aa", // zinc-400
  },
};

// ─── helpers ─────────────────────────────────────────────────────────────────

function brl(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function fmtRR(rr: number): string {
  return `${rr.toFixed(1)}x`;
}

// ─── sub-components ──────────────────────────────────────────────────────────

function VerdictBadge({ verdict }: { verdict: SignalVerdict }) {
  const cfg = VERDICT_CONFIG[verdict];
  const { Icon } = cfg;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-widest ${cfg.badgeBg} ${cfg.badgeText} ${cfg.badgeBorder}`}
    >
      <Icon size={13} weight="bold" aria-hidden />
      {cfg.label}
    </span>
  );
}

/**
 * PulseBadge — perpetual CSS animation on the R:R chip.
 * We inject a scoped keyframe via inline <style> to avoid touching tailwind.config.
 */
function RRPulseBadge({ rr, color }: { rr: number; color: string }) {
  const id = "rr-pulse-kf";
  return (
    <>
      {/* Inject the keyframe once — safe because SSR doesn't run animations */}
      <style>{`
        @keyframes ${id} {
          0%, 100% { box-shadow: 0 0 0 0 ${color}55; opacity: 1; }
          50%       { box-shadow: 0 0 0 6px ${color}00; opacity: 0.85; }
        }
        .rr-pulse { animation: ${id} 2s ease-in-out infinite; }
      `}</style>
      <span
        className="rr-pulse inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold tabular-nums"
        style={{
          borderColor: color,
          color: color,
          backgroundColor: `${color}18`,
        }}
        aria-label={`Risco Retorno ${fmtRR(rr)}`}
      >
        <Scales size={11} weight="bold" aria-hidden />
        {fmtRR(rr)} R/R
      </span>
    </>
  );
}

function GateProgress({ passed, total }: { passed: number; total: number }) {
  const pct = total > 0 ? (passed / total) * 100 : 0;
  const barColor =
    pct >= 100
      ? "bg-emerald-500"
      : pct >= 60
      ? "bg-amber-400"
      : "bg-zinc-300";

  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-400">
          Gates técnicos
        </span>
        <span className="text-[10px] font-semibold tabular-nums text-zinc-500">
          {passed}/{total}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-100">
        <motion.div
          className={`h-full rounded-full ${barColor}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1], delay: 0.15 }}
        />
      </div>
    </div>
  );
}

function LevelRow({
  label,
  value,
  Icon,
  color,
}: {
  label: string;
  value: number;
  Icon: React.ElementType;
  color: string;
}) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-white/30 last:border-0">
      <div className="flex items-center gap-1.5">
        <Icon size={12} weight="bold" className={color} aria-hidden />
        <span className="text-xs text-zinc-500">{label}</span>
      </div>
      <span className={`text-sm font-semibold tabular-nums ${color}`}>{brl(value)}</span>
    </div>
  );
}

// ─── card body variants ───────────────────────────────────────────────────────

function BuyCard({ data }: { data: SignalCurrentData }) {
  const cfg = VERDICT_CONFIG.BUY;
  const setup = data.setup!; // BUY always has a setup
  return (
    <>
      <GateProgress passed={data.passed_gates} total={data.total_gates} />

      {/* Pattern chip */}
      {setup.pattern && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-700">
            {setup.pattern}
          </span>
          <span className="text-[10px] font-medium capitalize text-zinc-400">
            {setup.direction === "long" ? "Alta" : "Baixa"}
          </span>
        </div>
      )}

      {/* Levels */}
      <div className="rounded-xl border border-white/40 bg-white/50 backdrop-blur-sm px-3 py-1">
        <LevelRow label="Entrada" value={setup.entry} Icon={ArrowUp} color="text-zinc-800" />
        <LevelRow label="Stop"    value={setup.stop}  Icon={ArrowDown} color="text-red-600" />
        <LevelRow label="Alvo"    value={setup.target} Icon={Target} color="text-emerald-600" />
      </div>

      <p className={`text-[10px] leading-snug ${cfg.accentText}`}>
        Setup A+ confirmado — todos os gates técnicos satisfeitos. Gerencie o risco com stop definido.
      </p>
    </>
  );
}

function WaitCard({ data }: { data: SignalCurrentData }) {
  const setup = data.setup;
  return (
    <>
      <GateProgress passed={data.passed_gates} total={data.total_gates} />

      {setup && (
        <div className="rounded-xl border border-white/40 bg-white/50 backdrop-blur-sm px-3 py-1">
          <LevelRow label="Entrada" value={setup.entry} Icon={ArrowUp} color="text-zinc-800" />
          <LevelRow label="Stop"    value={setup.stop}  Icon={ArrowDown} color="text-red-600" />
          <LevelRow label="Alvo"    value={setup.target} Icon={Target} color="text-amber-700" />
        </div>
      )}

      <p className="text-[10px] leading-snug text-amber-700">
        {data.passed_gates === 0
          ? "Sem condições técnicas satisfeitas no momento. Aguardar formação."
          : `${data.passed_gates} de ${data.total_gates} condições satisfeitas — aguardar confluência adicional antes de entrar.`}
      </p>
    </>
  );
}

function SkipCard({ data }: { data: SignalCurrentData }) {
  return (
    <>
      <GateProgress passed={data.passed_gates} total={data.total_gates} />
      <p className="text-[10px] leading-snug text-zinc-400">
        {data.passed_gates === 0
          ? "Nenhuma condição técnica atingida. Ativo fora de setup no momento."
          : `Apenas ${data.passed_gates} de ${data.total_gates} gates técnicos satisfeitos — setup insuficiente.`}
      </p>
    </>
  );
}

// ─── loading skeleton ─────────────────────────────────────────────────────────

function SignalEngineCardSkeleton() {
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white/60 p-4 space-y-3 backdrop-blur-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2">
          <ShimmerSkeleton className="h-3 w-24" />
          <ShimmerSkeleton className="h-7 w-20 rounded-full" />
        </div>
        <ShimmerSkeleton className="h-6 w-20 rounded-full" />
      </div>
      <ShimmerSkeleton className="h-1.5 w-full rounded-full" />
      <div className="rounded-xl border border-zinc-100 p-3 space-y-2">
        <ShimmerSkeleton className="h-8 w-full rounded-lg" />
        <ShimmerSkeleton className="h-8 w-full rounded-lg" />
        <ShimmerSkeleton className="h-8 w-full rounded-lg" />
      </div>
      <ShimmerSkeleton className="h-3 w-3/4" />
    </div>
  );
}

// ─── SignalEngineCard (public export) ────────────────────────────────────────

export function SignalEngineCard({ ticker }: Props) {
  const { data, isLoading, error } = useSignalCurrent(ticker);

  if (isLoading) return <SignalEngineCardSkeleton />;

  // Graceful degradation — never crash the stock detail page
  if (error || !data) return null;

  const cfg = VERDICT_CONFIG[data.verdict];
  const hasSetup = data.setup !== null;
  const showRR = hasSetup && data.setup!.rr > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className={[
        // Glassmorphism base
        "rounded-2xl border p-4 backdrop-blur-sm",
        "bg-white/60 supports-[backdrop-filter]:bg-white/40",
        cfg.cardBorder,
        cfg.cardBg,
        "space-y-3",
      ].join(" ")}
      role="region"
      aria-label={`Sinal de operação: ${data.verdict}`}
    >
      {/* ── Header row ── */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-400 mb-1">
            Signal Engine
          </p>
          <VerdictBadge verdict={data.verdict} />
        </div>
        {showRR && (
          <RRPulseBadge rr={data.setup!.rr} color={cfg.rrPulseColor} />
        )}
      </div>

      {/* ── Body — driven by verdict ── */}
      {data.verdict === "BUY" && data.setup && <BuyCard data={data} />}
      {data.verdict === "WAIT" && <WaitCard data={data} />}
      {data.verdict === "SKIP" && <SkipCard data={data} />}

      {/* ── Footer disclaimer ── */}
      <p className="text-[9px] text-zinc-300 leading-snug">
        Análise técnica automatizada. Não constitui recomendação de investimento.
      </p>
    </motion.div>
  );
}
