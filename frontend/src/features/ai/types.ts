/**
 * TypeScript types for the AI analysis engine feature.
 */

export interface SkillResult {
  ticker: string;
  analysis: string;
  methodology: string;
  disclaimer: string;
}

export interface MacroResult {
  analysis: string;
  methodology: string;
  disclaimer: string;
}

export interface AdvisorResult {
  diagnostico: string;
  pontos_positivos: string[];
  pontos_de_atencao: string[];
  sugestoes: string[];
  proximos_passos: string[];
  disclaimer?: string;
}

export interface AnalysisResult {
  dcf?: SkillResult;
  valuation?: SkillResult;
  earnings?: SkillResult;
  macro?: MacroResult;
  advisor?: AdvisorResult;
}

export type JobStatus = "pending" | "running" | "completed" | "failed";

export interface AnalysisJob {
  id: string;
  job_type: string;
  ticker: string | null;
  status: JobStatus;
  created_at: string;
  completed_at: string | null;
  result: AnalysisResult | null;
  error_message?: string | null;
}
