export type OpportunityScore = number; // 0–100

export interface Opportunity {
  id: string;
  ticker: string;
  name: string | null;
  asset_type: "acao" | "fii" | "crypto" | "renda_fixa" | string;
  score: OpportunityScore;
  upside_pct: number | null;
  current_price: number | null;
  currency: "BRL" | "USD" | string;
  drop_pct: number | null;
  risk_level: "baixo" | "medio" | "alto" | "evitar" | string | null;
  cause_explanation: string | null;
  recommended_amount_brl: number | null;
  detected_at: string;
}

export interface OpportunitiesResponse {
  items: Opportunity[];
  total: number;
  refreshed_at: string;
}
