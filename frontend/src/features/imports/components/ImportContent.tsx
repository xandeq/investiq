"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ImportJob } from "../types";
import { UploadDropzone } from "./UploadDropzone";
import { StagingReviewTable } from "./StagingReviewTable";
import { ImportHistory } from "./ImportHistory";
import { clearAllTransactions } from "../api";

export function ImportContent() {
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [clearStep, setClearStep] = useState<"idle" | "confirm">("idle");
  const [clearing, setClearing] = useState(false);
  const queryClient = useQueryClient();

  function handleJobCreated(job: ImportJob) {
    setActiveJobId(job.id);
  }

  function handleConfirmed() {
    setActiveJobId(null);
  }

  function handleCancelled() {
    setActiveJobId(null);
  }

  function handleReparseStarted(newJob: ImportJob) {
    setActiveJobId(newJob.id);
  }

  async function handleClearAll() {
    if (clearStep === "idle") {
      setClearStep("confirm");
      return;
    }
    setClearing(true);
    setClearStep("idle");
    try {
      const result = await clearAllTransactions();
      queryClient.invalidateQueries({ queryKey: ["portfolio"] });
      queryClient.invalidateQueries({ queryKey: ["imports", "history"] });
      alert(result.message);
    } catch (err) {
      console.error("Clear failed:", err);
      alert("Erro ao limpar carteira.");
    } finally {
      setClearing(false);
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Importar Transacoes</h1>

        {/* Limpar carteira — destructive action with 2-step confirm */}
        <div className="flex items-center gap-2">
          {clearStep === "confirm" ? (
            <>
              <span className="text-sm text-destructive font-medium">
                Isso vai remover TODAS as transacoes. Confirma?
              </span>
              <button
                onClick={handleClearAll}
                disabled={clearing}
                className="rounded-md bg-destructive px-3 py-1.5 text-sm text-white font-medium hover:bg-destructive/90 disabled:opacity-50"
              >
                {clearing ? "Limpando..." : "Sim, limpar tudo"}
              </button>
              <button
                onClick={() => setClearStep("idle")}
                className="rounded-md border px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted"
              >
                Cancelar
              </button>
            </>
          ) : (
            <button
              onClick={handleClearAll}
              disabled={clearing}
              className="rounded-md border border-destructive/40 px-3 py-1.5 text-sm text-destructive hover:bg-destructive/10 disabled:opacity-50"
            >
              🗑️ Limpar carteira
            </button>
          )}
        </div>
      </div>

      {!activeJobId ? (
        <UploadDropzone onJobCreated={handleJobCreated} />
      ) : (
        <StagingReviewTable
          jobId={activeJobId}
          onConfirmed={handleConfirmed}
          onCancelled={handleCancelled}
        />
      )}

      <ImportHistory onReparseStarted={handleReparseStarted} />
    </div>
  );
}
