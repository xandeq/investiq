"use client";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useImportHistory } from "../hooks/useImportHistory";
import { reparseImport, revertImport } from "../api";
import { ImportJob, ImportJobStatus } from "../types";
import { useSortedData } from "@/hooks/useSort";
import { SortableHeader } from "@/components/ui/SortableHeader";

interface ImportHistoryProps {
  onReparseStarted: (newJob: ImportJob) => void;
}

function StatusBadge({ status }: { status: ImportJobStatus }) {
  const styles: Record<ImportJobStatus, string> = {
    confirmed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
    cancelled: "bg-gray-100 text-gray-600",
    pending: "bg-blue-100 text-blue-800",
    running: "bg-blue-100 text-blue-800",
    completed: "bg-yellow-100 text-yellow-800",
  };

  const labels: Record<ImportJobStatus, string> = {
    confirmed: "Confirmado",
    failed: "Falhou",
    cancelled: "Cancelado",
    pending: "Aguardando",
    running: "Processando",
    completed: "Aguardando revisao",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${styles[status]}`}
    >
      {labels[status]}
    </span>
  );
}

function SkeletonRow() {
  return (
    <tr className="border-b">
      {[...Array(5)].map((_, i) => (
        <td key={i} className="px-3 py-2">
          <div className="h-4 bg-muted animate-pulse rounded w-16" />
        </td>
      ))}
    </tr>
  );
}

const TH = "px-3 py-2 text-xs font-medium text-muted-foreground";

export function ImportHistory({ onReparseStarted }: ImportHistoryProps) {
  const { data: imports, isLoading } = useImportHistory();
  const queryClient = useQueryClient();
  const { sorted, col, dir, toggle } = useSortedData(imports ?? [], "created_at", "desc");
  const [reparsing, setReparsing] = useState<string | null>(null);
  const [reverting, setReverting] = useState<string | null>(null);
  const [revertConfirm, setRevertConfirm] = useState<string | null>(null);

  async function handleReparse(jobId: string) {
    setReparsing(jobId);
    try {
      const newJob = await reparseImport(jobId);
      queryClient.invalidateQueries({ queryKey: ["imports", "history"] });
      onReparseStarted(newJob);
    } catch (err) {
      console.error("Reparse failed:", err);
    } finally {
      setReparsing(null);
    }
  }

  async function handleRevert(jobId: string) {
    if (revertConfirm !== jobId) {
      setRevertConfirm(jobId);
      return;
    }
    setReverting(jobId);
    setRevertConfirm(null);
    try {
      const result = await revertImport(jobId);
      queryClient.invalidateQueries({ queryKey: ["imports", "history"] });
      queryClient.invalidateQueries({ queryKey: ["portfolio"] });
      alert(result.message);
    } catch (err) {
      console.error("Revert failed:", err);
      alert("Erro ao desfazer import.");
    } finally {
      setReverting(null);
    }
  }

  function formatDate(dateStr: string) {
    return new Date(dateStr).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  }

  return (
    <div className="rounded-lg border bg-card">
      <div className="p-4 border-b">
        <h2 className="text-lg font-semibold">Historico de Importacoes</h2>
      </div>

      {isLoading ? (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/30">
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground text-left">Data</th>
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground text-left">Tipo</th>
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground text-left">Status</th>
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground text-left">Transacoes</th>
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground text-left">Acao</th>
            </tr>
          </thead>
          <tbody>
            <SkeletonRow />
            <SkeletonRow />
            <SkeletonRow />
          </tbody>
        </table>
      ) : !imports || imports.length === 0 ? (
        <div className="p-8 text-center text-sm text-muted-foreground">
          Nenhum import realizado ainda.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/30">
                <SortableHeader col="created_at" label="Data" activeCol={col} dir={dir} onSort={toggle} className={`${TH} text-left`} />
                <SortableHeader col="file_type" label="Tipo" activeCol={col} dir={dir} onSort={toggle} className={`${TH} text-left`} />
                <SortableHeader col="status" label="Status" activeCol={col} dir={dir} onSort={toggle} className={`${TH} text-left`} />
                <SortableHeader col="confirmed_count" label="Transacoes" activeCol={col} dir={dir} onSort={toggle} className={`${TH} text-left`} />
                <th className={`${TH} text-left`}>Acao</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((job) => (
                <tr key={job.id} className="border-b last:border-0 hover:bg-muted/20">
                  <td className="px-3 py-2 text-muted-foreground">{formatDate(job.created_at)}</td>
                  <td className="px-3 py-2 uppercase text-xs font-medium">{job.file_type}</td>
                  <td className="px-3 py-2">
                    <StatusBadge status={job.status} />
                  </td>
                  <td className="px-3 py-2 text-muted-foreground">
                    {job.confirmed_count != null
                      ? `${job.confirmed_count} confirmadas`
                      : job.staging_count != null
                      ? `${job.staging_count} encontradas`
                      : "—"}
                  </td>
                  <td className="px-3 py-2">
                    {job.status === "confirmed" ? (
                      <div className="flex items-center gap-2">
                        {revertConfirm === job.id ? (
                          <>
                            <span className="text-xs text-destructive">Confirma?</span>
                            <button
                              onClick={() => handleRevert(job.id)}
                              disabled={reverting === job.id}
                              className="text-xs text-destructive hover:underline font-medium disabled:opacity-50"
                            >
                              {reverting === job.id ? "Desfazendo..." : "Sim, desfazer"}
                            </button>
                            <button
                              onClick={() => setRevertConfirm(null)}
                              className="text-xs text-muted-foreground hover:underline"
                            >
                              Cancelar
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => handleRevert(job.id)}
                            disabled={reverting === job.id}
                            className="text-xs text-muted-foreground hover:text-destructive hover:underline disabled:opacity-50"
                          >
                            Desfazer
                          </button>
                        )}
                      </div>
                    ) : (
                      <button
                        onClick={() => handleReparse(job.id)}
                        disabled={reparsing === job.id}
                        className="text-sm text-primary hover:underline disabled:opacity-50 flex items-center gap-1"
                      >
                        {reparsing === job.id && (
                          <span className="h-3 w-3 animate-spin rounded-full border border-primary border-t-transparent" />
                        )}
                        Re-processar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
