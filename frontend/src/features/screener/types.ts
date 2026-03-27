export interface StockAnalysis {
  ticker: string;
  company_name: string;
  sector: string;

  // Valuation
  pe_ratio: number | null;
  pe_vs_sector: string | null;
  revenue_growth_5y: string | null;

  // Health
  debt_to_equity: number | null;
  debt_health: string | null;

  // Income
  dividend_yield: number | null;
  payout_score: string | null;

  // Qualitative
  moat_rating: string | null;
  moat_description: string | null;

  // Price targets (12 months)
  bull_target: number | null;
  bear_target: number | null;
  current_price_ref: number | null;

  // Risk
  risk_score: number | null;
  risk_reasoning: string | null;

  // Entry
  entry_zone: string | null;
  stop_loss: string | null;

  // Summary
  thesis: string | null;
}

export interface ScreenerResult {
  stocks: StockAnalysis[];
  summary: string;
  disclaimer: string;
  generated_at: string;
}

export interface ScreenerRun {
  id: string;
  status: "pending" | "running" | "completed" | "failed";
  sector_filter: string | null;
  custom_notes: string | null;
  created_at: string;
  completed_at: string | null;
  result: ScreenerResult | null;
}
