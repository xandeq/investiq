export type PrazoLabel = "6m" | "1a" | "2a" | "5a";
export type PerfilLabel = "conservador" | "moderado" | "arrojado";
export type WizardStatus = "pending" | "running" | "completed" | "failed";

export interface WizardAllocation {
  acoes_pct: number;
  fiis_pct: number;
  renda_fixa_pct: number;
  caixa_pct: number;
  rationale: string;
}

export interface WizardDeltaItem {
  asset_class: string;
  label: string;
  current_pct: number;
  suggested_pct: number;
  delta_pct: number;
  action: string;
  valor_delta: number;
}

export interface WizardResult {
  allocation: WizardAllocation;
  macro: Record<string, string>;
  portfolio_context: Record<string, { pct: number; valor: number }> | null;
  delta: WizardDeltaItem[] | null;
  provider_used: string | null;
  completed_at: string | null;
}

export interface WizardStartResponse {
  job_id: string;
  status: WizardStatus;
  disclaimer: string;
}

export interface WizardJobResponse {
  job_id: string;
  status: WizardStatus;
  perfil: string;
  prazo: string;
  valor: number;
  disclaimer: string;
  result: WizardResult | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}
