export interface OpportunityRow {
  id: string;
  ticker: string;
  asset_type: "acao" | "crypto" | "renda_fixa";
  drop_pct: number;
  period: string;
  current_price: number;
  currency: "BRL" | "USD";
  risk_level: string | null;
  is_opportunity: boolean;
  cause_category: string | null;
  cause_explanation: string | null;
  risk_rationale: string | null;
  recommended_amount_brl: number | null;
  target_upside_pct: number | null;
  telegram_message: string | null;
  followed: boolean;
  detected_at: string; // ISO 8601
}

export interface OpportunityHistoryResponse {
  total: number;
  results: OpportunityRow[];
}
