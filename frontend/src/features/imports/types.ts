/**
 * TypeScript types for the import broker integration feature.
 * Maps directly to backend response schemas from backend/app/modules/imports/schemas.py.
 */

export type ImportJobStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "confirmed"
  | "cancelled";

export interface ImportJob {
  id: string;
  file_id: string;
  file_type: "pdf" | "csv";
  status: ImportJobStatus;
  staging_count: number | null;
  confirmed_count: number | null;
  duplicate_count: number | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface StagingRow {
  id: string;
  ticker: string;
  asset_class: string;
  transaction_type: string;
  transaction_date: string;
  quantity: string;      // Decimal as string — project convention
  unit_price: string;    // Decimal as string
  total_value: string;   // Decimal as string
  brokerage_fee: string; // Decimal as string
  irrf_withheld: string; // Decimal as string
  notes: string;
  parser_source: string;
  is_duplicate: boolean;
}

export interface ImportJobDetail extends ImportJob {
  staged_rows: StagingRow[];
}

export interface ConfirmResponse {
  job_id: string;
  confirmed_count: number;
  duplicate_count: number;
  status: string;
}
