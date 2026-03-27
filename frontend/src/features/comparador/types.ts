export interface ComparadorRow {
  label: string;
  category: string;
  gross_pct: string | null;
  ir_rate_pct: string | null;
  net_pct: string | null;
  net_value: string | null;
  is_exempt: boolean;
  risk_label: string;
  data_source: string;
  is_best: boolean;
  is_portfolio: boolean;
  note: string | null;
}

export interface ComparadorResponse {
  prazo: string;
  holding_days: number;
  valor_inicial: string | null;
  disclaimer: string;
  rows: ComparadorRow[];
  best_category: string | null;
  portfolio_cdb_equivalent: string | null;
  ibovespa_data_stale: boolean;
  cdi_annual_pct: string | null;
}

export type PrazoLabel = "6m" | "1a" | "2a" | "5a";
