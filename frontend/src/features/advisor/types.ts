export interface PortfolioHealth {
  health_score: number;              // 0-100
  biggest_risk: string | null;       // one-sentence alert or null
  passive_income_monthly_brl: string; // Decimal as string from backend
  underperformers: string[];          // ["XXXX3 (-18%)", ...] max 3
  data_as_of: string | null;         // ISO datetime of screener snapshot
  total_assets: number;
  has_portfolio: boolean;
}
