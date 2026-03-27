"use client";
import { useState } from "react";
import { ImportJob } from "../types";
import { UploadDropzone } from "./UploadDropzone";
import { StagingReviewTable } from "./StagingReviewTable";
import { ImportHistory } from "./ImportHistory";

export function ImportContent() {
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

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

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Importar Transacoes</h1>

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
