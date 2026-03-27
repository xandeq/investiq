"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useImportJob } from "../hooks/useImportJob";
import { confirmImport, cancelImport } from "../api";

interface StagingReviewTableProps {
  jobId: string;
  onConfirmed: () => void;
  onCancelled: () => void;
}

export function StagingReviewTable({ jobId, onConfirmed, onCancelled }: StagingReviewTableProps) {
  const { data: job, isLoading } = useImportJob(jobId);
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState(false);

  async function handleConfirm() {
    setConfirming(true);
    try {
      await confirmImport(jobId);
      queryClient.invalidateQueries({ queryKey: ["imports", "history"] });
      onConfirmed();
    } catch (err) {
      console.error("Confirm failed:", err);
    } finally {
      setConfirming(false);
    }
  }

  async function handleCancel() {
    setConfirming(true);
    try {
      await cancelImport(jobId);
      onCancelled();
    } catch (err) {
      console.error("Cancel failed:", err);
    } finally {
      setConfirming(false);
    }
  }

  // Loading / pending / running
  if (isLoading || !job || job.status === "pending" || job.status === "running") {
    return (
      <div className="rounded-lg border bg-card p-8 text-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <p className="text-sm font-medium">Processando arquivo... aguarde</p>
          <p className="text-xs text-muted-foreground">Isso pode levar até 30 segundos para PDFs</p>
        </div>
      </div>
    );
  }

  // Failed
  if (job.status === "failed") {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6">
        <h3 className="text-sm font-semibold text-red-800 mb-2">Falha ao processar arquivo</h3>
        <p className="text-sm text-red-700 mb-4">{job.error_message || "Erro desconhecido"}</p>
        <button
          onClick={handleCancel}
          disabled={confirming}
          className="text-sm text-red-700 underline hover:no-underline"
        >
          Descartar
        </button>
      </div>
    );
  }

  // Confirmed
  if (job.status === "confirmed") {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 p-6">
        <h3 className="text-sm font-semibold text-green-800">Importacao concluida</h3>
        <p className="text-sm text-green-700 mt-1">
          {job.confirmed_count ?? 0} transacoes adicionadas
          {(job.duplicate_count ?? 0) > 0
            ? ` (${job.duplicate_count} duplicatas ignoradas)`
            : ""}
        </p>
      </div>
    );
  }

  // Cancelled
  if (job.status === "cancelled") {
    return (
      <div className="rounded-lg border bg-muted/20 p-6">
        <p className="text-sm text-muted-foreground">Importacao cancelada</p>
      </div>
    );
  }

  // Completed — show review table
  const rows = job.staged_rows ?? [];
  const stagingCount = job.staging_count ?? rows.length;
  const duplicateCount = job.duplicate_count ?? rows.filter((r) => r.is_duplicate).length;

  return (
    <div className="rounded-lg border bg-card">
      <div className="p-4 border-b">
        <h3 className="text-sm font-semibold">Revisar Transacoes</h3>
        <p className="text-xs text-muted-foreground mt-1">
          {stagingCount} transacoes encontradas
          {duplicateCount > 0 ? ` (${duplicateCount} duplicatas serao ignoradas)` : ""}
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/30 text-left">
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground">Ticker</th>
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground">Tipo</th>
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground">Data</th>
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground">Qtde</th>
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground">Preco Unit.</th>
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground">Total</th>
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground">Classe</th>
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground">Fonte</th>
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-b last:border-0 hover:bg-muted/20">
                <td className="px-3 py-2 font-medium">{row.ticker}</td>
                <td className="px-3 py-2 text-muted-foreground">{row.transaction_type}</td>
                <td className="px-3 py-2 text-muted-foreground">{row.transaction_date}</td>
                <td className="px-3 py-2">{row.quantity}</td>
                <td className="px-3 py-2">R$ {parseFloat(row.unit_price).toFixed(2)}</td>
                <td className="px-3 py-2">R$ {parseFloat(row.total_value).toFixed(2)}</td>
                <td className="px-3 py-2 text-muted-foreground">{row.asset_class}</td>
                <td className="px-3 py-2 text-muted-foreground text-xs">{row.parser_source}</td>
                <td className="px-3 py-2">
                  {row.is_duplicate ? (
                    <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-yellow-100 text-yellow-800">
                      Duplicata
                    </span>
                  ) : (
                    <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-muted text-muted-foreground">
                      Novo
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="p-4 flex gap-3 justify-end border-t">
        <button
          onClick={handleCancel}
          disabled={confirming}
          className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
        >
          Cancelar
        </button>
        <button
          onClick={handleConfirm}
          disabled={confirming}
          className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
        >
          {confirming && (
            <span className="h-3 w-3 animate-spin rounded-full border border-primary-foreground border-t-transparent" />
          )}
          Confirmar Importacao
        </button>
      </div>
    </div>
  );
}
