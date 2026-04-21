/**
 * Typed fetch wrappers for all /imports endpoints.
 * File uploads use raw fetch + FormData (NOT apiClient — apiClient sets Content-Type: application/json
 * which breaks multipart boundary). All other requests use the shared apiClient.
 */
import { apiClient } from "@/lib/api-client";
import { ImportJob, ImportJobDetail, ConfirmResponse } from "./types";

/**
 * Upload a broker PDF file. Returns a new ImportJob in "pending" status.
 * Uses raw fetch with FormData — do NOT use apiClient here.
 */
export async function uploadPdf(file: File): Promise<ImportJob> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch("/api/imports/pdf", {
    method: "POST",
    credentials: "include",
    body: formData, // No Content-Type header — browser sets it with boundary
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: "Upload failed" }));
    throw new Error(error.detail || error.error || `HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * Upload a CSV file. Returns a new ImportJob in "pending" status.
 * Uses raw fetch with FormData — same pattern as uploadPdf.
 */
export async function uploadCsv(file: File): Promise<ImportJob> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch("/api/imports/csv", {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: "Upload failed" }));
    throw new Error(error.detail || error.error || `HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * Fetch a single import job with its staged rows. Used by polling hook.
 */
export async function getImportJob(jobId: string): Promise<ImportJobDetail> {
  return apiClient<ImportJobDetail>(`/imports/jobs/${encodeURIComponent(jobId)}`);
}

/**
 * Confirm an import job — commits staged rows to the portfolio.
 */
export async function confirmImport(jobId: string): Promise<ConfirmResponse> {
  return apiClient<ConfirmResponse>(`/imports/jobs/${encodeURIComponent(jobId)}/confirm`, {
    method: "POST",
  });
}

/**
 * Cancel an import job — discards staged rows.
 */
export async function cancelImport(jobId: string): Promise<ImportJob> {
  return apiClient<ImportJob>(`/imports/jobs/${encodeURIComponent(jobId)}/cancel`, {
    method: "POST",
  });
}

/**
 * Re-parse a previously uploaded file without re-uploading.
 * Returns a new ImportJob that goes through the full parsing pipeline again.
 */
export async function reparseImport(jobId: string): Promise<ImportJob> {
  return apiClient<ImportJob>(`/imports/jobs/${encodeURIComponent(jobId)}/reparse`, {
    method: "POST",
  });
}

/**
 * List all import jobs for the current user (import history).
 */
export async function listImports(): Promise<ImportJob[]> {
  return apiClient<ImportJob[]>("/imports/history");
}

/**
 * Upload a Clear PosicaoDetalhada.xlsx position snapshot.
 * Returns a new ImportJob in "pending" status.
 */
export async function uploadXlsx(file: File): Promise<ImportJob> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch("/api/imports/xlsx", {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: "Upload failed" }));
    throw new Error(error.detail || error.error || `HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * Returns the direct URL for downloading the CSV template file.
 * Used as an anchor href — not fetched programmatically.
 */
export function getCsvTemplateUrl(): string {
  return "/api/imports/template.csv";
}

/**
 * Clear all transactions for the current user (Limpar carteira).
 * Returns count of soft-deleted transactions.
 */
export async function clearAllTransactions(): Promise<{ deleted: number; message: string }> {
  return apiClient<{ deleted: number; message: string }>("/portfolio/transactions", {
    method: "DELETE",
  });
}

/**
 * Revert (undo) all transactions created by a specific import job.
 * Returns count of soft-deleted transactions.
 */
export async function revertImport(importJobId: string): Promise<{ deleted: number; message: string }> {
  return apiClient<{ deleted: number; message: string }>(
    `/portfolio/transactions/revert-import/${encodeURIComponent(importJobId)}`,
    { method: "POST" }
  );
}
