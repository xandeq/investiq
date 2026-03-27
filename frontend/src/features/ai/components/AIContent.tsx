"use client";
import { useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { PremiumGate } from "./PremiumGate";
import { AnalysisRequestForm } from "./AnalysisRequestForm";
import { MacroResultCard } from "./MacroResultCard";
import { useAnalysisJob } from "../hooks/useAnalysisJob";
import { useJobList } from "../hooks/useJobList";
import { requestMacroAnalysis } from "../api";
import { useProfile } from "@/features/profile/hooks/useProfile";

function MacroSection() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: job } = useAnalysisJob(jobId);

  const isRunning =
    isSubmitting || (!!jobId && (job?.status === "pending" || job?.status === "running"));

  async function handleMacroAnalysis() {
    setError(null);
    setIsSubmitting(true);
    setJobId(null);
    try {
      const created = await requestMacroAnalysis();
      setJobId(created.id);
      queryClient.invalidateQueries({ queryKey: ["ai", "jobs"] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao iniciar análise macro");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-bold tracking-tight">Impacto Macro no Portfólio</h2>
        <button
          onClick={handleMacroAnalysis}
          disabled={isRunning}
          className="rounded-md bg-emerald-500 text-white px-4 py-2 text-sm font-semibold hover:bg-emerald-600 hover:scale-105 disabled:opacity-50 transition-all duration-200"
        >
          {isRunning ? (
            <span className="flex items-center gap-2">
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-white/30 border-t-white" />
              Analisando...
            </span>
          ) : (
            "Analisar Impacto Macro"
          )}
        </button>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border-l-4 border-red-500 p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {job?.status === "failed" && (
        <div className="rounded-md bg-red-50 border-l-4 border-red-500 p-3 text-sm text-red-600">
          Análise macro falhou. Tente novamente.
        </div>
      )}

      {job?.status === "completed" && job.result?.macro && (
        <MacroResultCard result={job.result.macro} />
      )}
    </div>
  );
}

function JobHistory() {
  const { data: jobs, isLoading } = useJobList();

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-10 rounded-md bg-gray-100 animate-pulse" />
        ))}
      </div>
    );
  }

  const recent = jobs?.slice(0, 5) ?? [];

  if (recent.length === 0) {
    return <p className="text-sm text-muted-foreground">Nenhuma análise solicitada ainda.</p>;
  }

  return (
    <div className="space-y-2">
      {recent.map((job) => (
        <div
          key={job.id}
          className="flex items-center justify-between rounded-md bg-gray-100 px-4 py-2.5 text-sm"
        >
          <span className="font-semibold">
            {job.ticker ?? "Macro"}{" "}
            <span className="text-muted-foreground font-normal text-xs">({job.job_type})</span>
          </span>
          <div className="flex items-center gap-3">
            <span className={
              job.status === "completed" ? "text-emerald-600 font-medium text-xs" :
              job.status === "failed" ? "text-red-500 font-medium text-xs" :
              "text-amber-600 font-medium text-xs"
            }>
              {job.status}
            </span>
            <span className="text-muted-foreground text-xs">
              {new Date(job.created_at).toLocaleDateString("pt-BR")}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

function ProfileBanner() {
  const { data: profile, error } = useProfile();
  const noProfile = error || !profile;
  const incomplete = profile && profile.completion_pct < 100;

  if (!noProfile && !incomplete) return null;

  return (
    <div className="rounded-lg bg-amber-50 border-l-4 border-amber-500 px-4 py-3 flex items-center justify-between gap-4">
      <p className="text-sm text-amber-700">
        {noProfile
          ? "Configure seu perfil de investidor para análises de IA personalizadas."
          : `Seu perfil está ${profile?.completion_pct}% completo. Complete-o para análises mais precisas.`}
      </p>
      <Link
        href="/profile"
        className="text-sm font-semibold text-amber-700 hover:text-amber-800 transition-colors whitespace-nowrap"
      >
        {noProfile ? "Configurar agora" : "Completar perfil"}
      </Link>
    </div>
  );
}

export function AIContent() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Análise de IA</h2>
        <p className="text-sm text-muted-foreground mt-1">Insights gerados por inteligência artificial para sua carteira</p>
      </div>

      <ProfileBanner />

      <PremiumGate>
        <div className="space-y-6">
          {/* Asset analysis section */}
          <section className="rounded-lg bg-white p-6">
            <h2 className="text-base font-bold tracking-tight mb-4">Análise de Ativo</h2>
            <AnalysisRequestForm />
          </section>

          {/* Macro analysis section */}
          <section className="rounded-lg bg-white p-6">
            <MacroSection />
          </section>
        </div>
      </PremiumGate>

      {/* Job history */}
      <section className="rounded-lg bg-white p-6">
        <h2 className="text-base font-bold tracking-tight mb-4">Histórico de Análises</h2>
        <JobHistory />
      </section>
    </div>
  );
}
