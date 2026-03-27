"use client";
import { useState, useEffect, useRef } from "react";
import { startWizard, getWizardJob } from "../api";
import type { WizardJobResponse, PrazoLabel, PerfilLabel, WizardStatus } from "../types";

export function useWizard() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<WizardJobResponse | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  };

  useEffect(() => {
    if (!jobId) return;
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const data = await getWizardJob(jobId);
        setJob(data);
        if (data.status === "completed" || data.status === "failed") stopPolling();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Erro ao consultar resultado");
        stopPolling();
      }
    }, 2500);
    return stopPolling;
  }, [jobId]);

  async function submit(perfil: PerfilLabel, prazo: PrazoLabel, valor: number) {
    setIsStarting(true);
    setError(null);
    setJob(null);
    try {
      const res = await startWizard(perfil, prazo, valor);
      setJobId(res.job_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao iniciar análise");
    } finally {
      setIsStarting(false);
    }
  }

  const status: WizardStatus | null = job?.status ?? (isStarting ? "pending" : null);
  return { submit, job, status, isStarting, error, reset: () => { stopPolling(); setJobId(null); setJob(null); setError(null); } };
}
