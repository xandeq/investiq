"use client";
import Link from "next/link";
import { motion } from "framer-motion";
import { Check } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

interface OnboardingStep { key: string; label: string; href: string; done: boolean; }

function useOnboardingStatus() {
  const profile = useQuery({ queryKey: ["investor-profile"], queryFn: () => apiClient("/profile").catch(() => null), staleTime: 60_000 });
  const transactions = useQuery({ queryKey: ["transactions", {}], queryFn: () => apiClient("/portfolio/transactions?limit=1").catch(() => []), staleTime: 60_000 });
  const jobs = useQuery({ queryKey: ["ai", "jobs"], queryFn: () => apiClient("/ai/jobs").catch(() => []), staleTime: 60_000 });

  const steps: OnboardingStep[] = [
    { key: "profile", label: "Configure seu perfil", href: "/profile", done: !!profile.data },
    { key: "transaction", label: "Adicione sua primeira transação", href: "/portfolio/transactions", done: Array.isArray(transactions.data) && transactions.data.length > 0 },
    { key: "ai", label: "Rode sua primeira análise de IA", href: "/ai", done: Array.isArray(jobs.data) && jobs.data.length > 0 },
  ];
  const pending = steps.filter(s => !s.done);
  const pct = Math.round((steps.filter(s => s.done).length / steps.length) * 100);
  return { steps, pending, pct, loading: profile.isLoading || transactions.isLoading };
}

export function OnboardingBanner() {
  const { steps, pending, pct, loading } = useOnboardingStatus();
  if (loading || pct === 100) return null;
  const next = pending[0];
  const doneCount = steps.filter(s => s.done).length;

  return (
    <motion.div
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-xl bg-zinc-900 text-white p-5 space-y-4"
    >
      <div className="flex items-center justify-between">
        <p className="text-sm font-bold tracking-tight">Configure seu copiloto</p>
        <span className="text-xs font-semibold text-zinc-400">{doneCount}/{steps.length} passos</span>
      </div>

      <div className="flex items-center gap-2">
        {steps.map((s, i) => (
          <div key={s.key} className="flex items-center gap-2">
            <motion.div
              initial={{ scale: 0.85, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.25, delay: i * 0.07 }}
              className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                s.done ? "bg-blue-500 text-white" : "bg-zinc-700 text-zinc-400"
              }`}
            >
              {s.done ? <Check size={12} weight="bold" /> : i + 1}
            </motion.div>
            <span className={`text-xs hidden sm:block ${s.done ? "text-zinc-300" : "text-zinc-500"}`}>{s.label}</span>
            {i < steps.length - 1 && <div className="h-px w-4 sm:w-8 bg-zinc-700" />}
          </div>
        ))}
      </div>

      <div className="h-1.5 rounded-full bg-zinc-700 overflow-hidden">
        <motion.div
          className="h-full rounded-full bg-blue-500"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        />
      </div>

      <div className="flex items-center justify-between">
        <p className="text-sm text-zinc-400">{next?.label}</p>
        <Link href={next?.href ?? "/"} className="text-sm font-semibold text-blue-400 hover:text-blue-300 transition-colors">
          Fazer agora →
        </Link>
      </div>
    </motion.div>
  );
}
