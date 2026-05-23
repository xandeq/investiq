"use client";
import { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Check, X } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

const DISMISS_KEY = "investiq:onboarding:dismissed_at";
const DISMISS_TTL_DAYS = 7;

interface OnboardingStep {
  key: string;
  label: string;
  description: string;
  href: string;
  done: boolean;
}

function useOnboardingStatus() {
  const profile = useQuery({ queryKey: ["investor-profile"], queryFn: () => apiClient("/profile").catch(() => null), staleTime: 60_000 });
  const transactions = useQuery({ queryKey: ["transactions", {}], queryFn: () => apiClient("/portfolio/transactions?limit=1").catch(() => []), staleTime: 60_000 });
  const jobs = useQuery({ queryKey: ["ai", "jobs"], queryFn: () => apiClient("/ai/jobs").catch(() => []), staleTime: 60_000 });

  const steps: OnboardingStep[] = [
    {
      key: "profile",
      label: "Configure seu perfil",
      description: "Perfil de risco e objetivos para recomendações personalizadas",
      href: "/profile",
      done: !!profile.data,
    },
    {
      key: "transaction",
      label: "Adicione uma transação",
      description: "Importe ou cadastre sua carteira para ver análises reais",
      href: "/portfolio/transactions",
      done: Array.isArray(transactions.data) && transactions.data.length > 0,
    },
    {
      key: "ai",
      label: "Rode sua primeira análise",
      description: "IA analisa seus ativos e sugere oportunidades em segundos",
      href: "/ai",
      done: Array.isArray(jobs.data) && jobs.data.length > 0,
    },
  ];
  const pending = steps.filter(s => !s.done);
  const pct = Math.round((steps.filter(s => s.done).length / steps.length) * 100);
  return { steps, pending, pct, loading: profile.isLoading || transactions.isLoading };
}

function isDismissed(): boolean {
  try {
    const raw = localStorage.getItem(DISMISS_KEY);
    if (!raw) return false;
    const ts = parseInt(raw, 10);
    return Date.now() - ts < DISMISS_TTL_DAYS * 86_400_000;
  } catch { return false; }
}

export function OnboardingBanner() {
  const { steps, pending, pct, loading } = useOnboardingStatus();
  const [dismissed, setDismissed] = useState(false);

  if (loading || pct === 100 || dismissed) return null;
  if (isDismissed()) return null;

  const next = pending[0];
  const doneCount = steps.filter(s => s.done).length;

  function dismiss() {
    try { localStorage.setItem(DISMISS_KEY, String(Date.now())); } catch { /* ignore */ }
    setDismissed(true);
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8, height: 0, marginBottom: 0 }}
        transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
        className="rounded-xl bg-zinc-900 text-white p-5 space-y-4"
      >
        <div className="flex items-center justify-between">
          <p className="text-sm font-bold tracking-tight">Configure seu copiloto</p>
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-zinc-400">{doneCount}/{steps.length} passos</span>
            <button
              onClick={dismiss}
              aria-label="Ocultar por 7 dias"
              title="Ocultar por 7 dias"
              className="text-zinc-500 hover:text-zinc-300 transition-colors p-0.5 rounded"
            >
              <X size={14} />
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {steps.map((s, i) => (
            <div key={s.key} className="flex items-center gap-2">
              <motion.div
                initial={{ scale: 0.85, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.25, delay: i * 0.07 }}
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-colors shrink-0 ${
                  s.done ? "bg-blue-500 text-white" : "bg-zinc-700 text-zinc-400"
                }`}
              >
                {s.done ? <Check size={12} weight="bold" /> : i + 1}
              </motion.div>
              <span className={`text-xs hidden sm:block truncate max-w-[120px] ${s.done ? "text-zinc-400 line-through" : "text-zinc-300"}`}>
                {s.label}
              </span>
              {i < steps.length - 1 && <div className="h-px w-3 sm:w-6 bg-zinc-700 shrink-0" />}
            </div>
          ))}
        </div>

        <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-blue-500"
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          />
        </div>

        {next && (
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-medium text-white">{next.label}</p>
              <p className="text-xs text-zinc-400 mt-0.5 leading-relaxed">{next.description}</p>
            </div>
            <Link
              href={next.href}
              className="shrink-0 px-3 py-1.5 rounded-lg bg-blue-500 hover:bg-blue-400 text-white text-xs font-semibold transition-colors"
            >
              Começar →
            </Link>
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  );
}
