// TypeScript contracts for the Outcome Tracker module (Phase 43).
//
// Mirrors backend app/modules/outcome_tracker — Decimal fields are serialized
// as strings by _serialize() in the router.

export type OutcomeStatus = "open" | "closed" | "stopped";
export type OutcomeDirection = "long" | "short";

export interface SignalOutcome {
  id: string;
  tenant_id: string;
  ticker: string;
  pattern: string | null;
  direction: OutcomeDirection;
  entry_price: string; // Decimal string
  stop_price: string;  // Decimal string
  target_1: string | null;
  target_2: string | null;
  exit_price: string | null;
  exit_date: string | null; // ISO date
  status: OutcomeStatus;
  r_multiple: string | null; // Decimal string, e.g. "1.5000"
  signal_grade: string | null; // A+, A, B, C, etc.
  signal_score: string | null;
  created_at: string; // ISO datetime
  updated_at: string | null;
}

export interface OutcomeListResponse {
  outcomes: SignalOutcome[];
  count: number;
}

export interface OutcomeCreatePayload {
  ticker: string;
  direction: OutcomeDirection;
  entry_price: number;
  stop_price: number;
  pattern?: string;
  target_1?: number;
  target_2?: number;
  signal_grade?: string;
  signal_score?: number;
}

export interface OutcomeClosePayload {
  exit_price: number;
  exit_date?: string; // ISO date YYYY-MM-DD
  status?: "closed" | "stopped";
}

export interface GradeBreakdownEntry {
  n: number;
  winrate: number;
  avg_r: number;
}

export interface OutcomeStats {
  total_closed: number;
  winrate: number | null;
  avg_r: number | null;
  expectancy: number | null;
  profit_factor: number | null;
  r_sharpe: number | null;
  max_consecutive_wins: number;
  max_consecutive_losses: number;
  avg_holding_days: number | null;
  grade_breakdown: Record<string, GradeBreakdownEntry>;
}

export interface ExpectancyByPattern {
  pattern: string;
  count: number;
  winrate: number;
  avg_r: number;
  expectancy: number;
}

export interface ExpectancyResponse {
  expectancy: ExpectancyByPattern[];
}
