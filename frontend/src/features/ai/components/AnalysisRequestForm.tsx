"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { requestAssetAnalysis } from "../api";
import { useAnalysisJob } from "../hooks/useAnalysisJob";
import { SkillResultCard } from "./SkillResultCard";

export function AnalysisRequestForm() {
  const [ticker, setTicker] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const queryClient = useQueryClient();
  const { data: job, isLoading: isPolling } = useAnalysisJob(jobId);

  const isRunning =
    isSubmitting || (!!jobId && (job?.status === "pending" || job?.status === "running"));
  const isCompleted = job?.status === "completed";
  const isFailed = job?.status === "failed";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!ticker.trim()) return;
    setSubmitError(null);
    setIsSubmitting(true);
    setJobId(null);
    try {
      const created = await requestAssetAnalysis(ticker.trim());
      setJobId(created.id);
      // Invalidate job list cache so history updates
      queryClient.invalidateQueries({ queryKey: ["ai", "jobs"] });
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Erro ao iniciar análise");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-5">
      <form onSubmit={handleSubmit} className="flex gap-2 items-end">
        <div className="flex-1">
          <label
            htmlFor="ticker-input"
            className="block text-sm font-medium text-foreground mb-1"
          >
            Ticker (ex: VALE3, PETR4)
          </label>
          <input
            id="ticker-input"
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="VALE3"
            disabled={isRunning}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
          />
        </div>
        <button
          type="submit"
          disabled={isRunning || !ticker.trim()}
          className="rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {isRunning ? (
            <span className="flex items-center gap-2">
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
              Analisando...
            </span>
          ) : (
            "Analisar"
          )}
        </button>
      </form>

      {submitError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-600">
          {submitError}
        </div>
      )}

      {isFailed && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-600">
          A análise falhou. Tente novamente em instantes.
        </div>
      )}

      {isCompleted && job?.result && (
        <div className="space-y-4">
          <SkillResultCard
            result={job.result.dcf ?? null}
            title="DCF — Fluxo de Caixa Descontado"
          />
          <SkillResultCard
            result={job.result.valuation ?? null}
            title="Valuation Relativa"
          />
          <SkillResultCard
            result={job.result.earnings ?? null}
            title="Análise de Lucros"
          />
        </div>
      )}
    </div>
  );
}
