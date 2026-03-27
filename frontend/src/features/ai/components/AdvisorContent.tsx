"use client";
import { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { requestPortfolioAnalysis } from "../api";
import { useAnalysisJob } from "../hooks/useAnalysisJob";
import { useJobList } from "../hooks/useJobList";
import { PremiumGate } from "./PremiumGate";
import type { AnalysisJob } from "../types";

interface AdvisorResult {
  diagnostico: string;
  pontos_positivos: string[];
  pontos_de_atencao: string[];
  sugestoes: string[];
  proximos_passos: string[];
  disclaimer?: string;
}

function ResultCard({ title, items, colorClass }: { title: string; items: string[]; colorClass: string }) {
  if (!items || items.length === 0) return null;
  return (
    <div className={`rounded-lg p-5 ${colorClass}`}>
      <h3 className="text-sm font-bold mb-3">{title}</h3>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="text-sm flex gap-2">
            <span className="mt-0.5 shrink-0 text-current">•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function AdvisorResultView({ result }: { result: AdvisorResult }) {
  return (
    <div className="space-y-4">
      <div className="rounded-lg bg-gray-100 p-5">
        <h3 className="text-sm font-bold mb-2">Diagnóstico</h3>
        <p className="text-sm text-muted-foreground leading-relaxed">{result.diagnostico}</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ResultCard title="Pontos Positivos" items={result.pontos_positivos} colorClass="bg-emerald-50 border-l-4 border-emerald-500" />
        <ResultCard title="Pontos de Atenção" items={result.pontos_de_atencao} colorClass="bg-amber-50 border-l-4 border-amber-500" />
      </div>
      <ResultCard title="Sugestões" items={result.sugestoes} colorClass="bg-blue-50 border-l-4 border-blue-500" />
      <ResultCard title="Próximos Passos" items={result.proximos_passos} colorClass="bg-gray-100 border-l-4 border-gray-400" />
      {result.disclaimer && (
        <p className="text-xs text-muted-foreground border-t border-gray-100 pt-3">{result.disclaimer}</p>
      )}
    </div>
  );
}

function AdvisorHistory({ jobs, onSelect }: { jobs: AnalysisJob[]; onSelect: (jobId: string) => void }) {
  const portfolioJobs = jobs.filter((j) => j.job_type === "portfolio");
  if (portfolioJobs.length === 0) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Análises anteriores</h3>
      {portfolioJobs.slice(0, 5).map((job) => (
        <button
          key={job.id}
          onClick={() => job.status === "completed" && onSelect(job.id)}
          disabled={job.status !== "completed"}
          className="w-full text-left rounded-md bg-gray-100 px-4 py-3 text-sm hover:bg-gray-200 transition-all duration-200 disabled:opacity-50"
        >
          <div className="flex items-center justify-between">
            <span className="font-semibold">Análise de carteira</span>
            <span className={
              job.status === "completed" ? "text-emerald-600 text-xs font-medium" :
              job.status === "failed" ? "text-red-500 text-xs font-medium" :
              "text-amber-600 text-xs font-medium"
            }>
              {job.status === "completed" ? "Concluída" :
               job.status === "failed" ? "Falhou" : "Em andamento"}
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            {new Date(job.created_at).toLocaleDateString("pt-BR", {
              day: "2-digit", month: "2-digit", year: "numeric",
              hour: "2-digit", minute: "2-digit"
            })}
          </p>
        </button>
      ))}
    </div>
  );
}

function AdvisorMain() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: jobs } = useJobList();
  const { data: job } = useAnalysisJob(jobId);

  // Resume polling if user navigated away while a job was running
  useEffect(() => {
    if (jobId !== null) return;
    const inProgress = (jobs ?? []).find(
      (j) => j.job_type === "portfolio" && (j.status === "pending" || j.status === "running")
    );
    if (inProgress) setJobId(inProgress.id);
  }, [jobs, jobId]);

  const isRunning =
    isSubmitting || (!!jobId && (job?.status === "pending" || job?.status === "running"));

  const advisorResult: AdvisorResult | null =
    job?.status === "completed" && job.result?.advisor ? job.result.advisor as AdvisorResult : null;

  const jobFailed = !!jobId && job?.status === "failed";
  const failureMessage = job?.error_message || "A análise falhou. Tente novamente em alguns minutos.";

  async function handleAnalyze() {
    setError(null);
    setIsSubmitting(true);
    setJobId(null);
    try {
      const created = await requestPortfolioAnalysis();
      setJobId(created.id);
      queryClient.invalidateQueries({ queryKey: ["ai", "jobs"] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao iniciar análise");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-8">
      {/* Action button */}
      <div className="rounded-lg bg-[#111827] text-white p-8 text-center space-y-4">
        <div>
          <h2 className="text-lg font-bold tracking-tight">Análise completa da carteira</h2>
          <p className="text-sm text-gray-400 mt-1">
            A IA analisa suas posições, alocação, P&L e contexto macro para gerar um diagnóstico personalizado.
          </p>
        </div>
        <button
          onClick={handleAnalyze}
          disabled={isRunning}
          className="px-6 py-3 rounded-md bg-blue-500 text-white hover:bg-blue-400 hover:scale-105 disabled:opacity-50 transition-all duration-200 font-semibold"
        >
          {isRunning ? (
            <span className="flex items-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
              Analisando sua carteira...
            </span>
          ) : (
            "Analisar minha carteira agora"
          )}
        </button>
        {error && <p className="text-sm text-red-400">{error}</p>}
        {jobFailed && !error && (
          <p className="text-sm text-red-400">{failureMessage}</p>
        )}
      </div>

      {/* In progress indicator */}
      {isRunning && !advisorResult && (
        <div className="rounded-lg bg-gray-100 p-6 space-y-3">
          <div className="flex items-center gap-3">
            <span className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-blue-500" />
            <span className="text-sm font-semibold">Análise em andamento...</span>
          </div>
          <p className="text-xs text-muted-foreground">
            Isso leva ~1-2 minutos. Você pode navegar para outras páginas — a análise continua em segundo plano e o resultado aparecerá aqui quando você voltar.
          </p>
          {["Carregando posições e P&L", "Buscando contexto macro", "Processando com IA", "Estruturando resultados"].map((step) => (
            <div key={step} className="h-3 bg-gray-200 rounded animate-pulse" style={{ width: `${60 + Math.random() * 30}%` }} />
          ))}
        </div>
      )}

      {/* Result */}
      {advisorResult && <AdvisorResultView result={advisorResult} />}

      {/* History */}
      {!isRunning && <AdvisorHistory jobs={jobs ?? []} onSelect={setJobId} />}
    </div>
  );
}

export function AdvisorContent() {
  return (
    <PremiumGate>
      <AdvisorMain />
    </PremiumGate>
  );
}
