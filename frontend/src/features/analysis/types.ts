/**
 * TypeScript interfaces for the AI Analysis module (Phase 16).
 * Mirrors backend/app/modules/analysis/schemas.py exactly.
 */

export type AnalysisType = "dcf" | "earnings" | "dividend" | "sector";

export interface DataMetadata {
  data_timestamp: string;
  data_version_id: string;
  data_sources: Array<{ source: string; type: string; freshness: string }>;
  cache_hit: boolean;
  cache_ttl_seconds: number;
}

export interface AnalysisJobStatus {
  job_id: string;
  status: string;
  message: string | null;
}

export interface AnalysisResponse {
  analysis_id: string;
  analysis_type: AnalysisType;
  ticker: string;
  status: "pending" | "running" | "completed" | "failed" | "stale";
  result: Record<string, unknown> | null;
  data_metadata: DataMetadata | null;
  disclaimer: string;
  error_message: string | null;
}

export interface DCFResult {
  ticker: string;
  fair_value: number;
  fair_value_range: { low: number; high: number };
  current_price: number;
  upside_pct: number | null;
  assumptions: {
    growth_rate: number;
    discount_rate: number;
    terminal_growth: number;
    selic_rate: number;
    beta: number | null;
  };
  projected_fcfs: number[];
  key_drivers: string[];
  scenarios: {
    bear: Record<string, unknown>;
    base: Record<string, unknown>;
    bull: Record<string, unknown>;
  };
  narrative: string;
  data_completeness: Record<string, unknown>;
  data_version_id: string;
  data_timestamp: string;
  data_sources: Array<{ source: string; type: string; date: string }>;
  disclaimer: string;
}

export interface EarningsResult {
  ticker: string;
  eps_history: Array<{ year: number; eps: number }>;
  eps_cagr_5y: number | null;
  quality_metrics: {
    earnings_quality: string;
    accrual_ratio: number | null;
    fcf_conversion: number | null;
  };
  narrative: string;
  data_completeness: Record<string, unknown>;
  data_version_id: string;
  data_timestamp: string;
}

export interface DividendResult {
  ticker: string;
  current_yield: number | null;
  payout_ratio: number | null;
  coverage_ratio: number | null;
  consistency: { score: number };
  sustainability: "safe" | "warning" | "risk";
  dividend_history: Array<{ year: number; dps: number }>;
  narrative: string;
}

export interface SectorResult {
  ticker: string;
  sector: string;
  sector_key: string;
  peers_found: number;
  peers_attempted: number;
  target_metrics: {
    pe_ratio: number | null;
    price_to_book: number | null;
    dividend_yield: number | null;
    roe: number | null;
  };
  sector_averages: Record<string, unknown>;
  sector_medians: Record<string, unknown>;
  target_percentiles: Record<string, unknown>;
  peers: Array<{ ticker: string; metrics: Record<string, unknown> }>;
  narrative: string;
  data_completeness: Record<string, unknown>;
}
