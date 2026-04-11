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

// ---------------------------------------------------------------------------
// Radar de Oportunidades
// ---------------------------------------------------------------------------

export interface RadarMacro {
  selic: number;
  cdi: number;
  ipca: number;
  ptax_usd: number;
}

export interface RadarAcaoItem {
  ticker: string;
  name: string;
  setor: string;
  current_price: number;
  high_52w: number;
  low_52w: number | null;
  discount_from_high_pct: number;
  pl: number | null;
  signal: string;
  logo_url: string | null;
}

export interface RadarFiiItem {
  ticker: string;
  name: string;
  segmento: string;
  current_price: number;
  high_52w: number;
  low_52w: number | null;
  discount_from_high_pct: number;
  dy_anual_pct: number | null;
  signal: string;
}

export interface RadarCryptoItem {
  symbol: string;
  name: string;
  current_price_brl: number;
  current_price_usd: number | null;
  ath_brl: number;
  ath_usd: number | null;
  ath_date: string;
  discount_from_ath_pct: number;
  change_24h_pct: number | null;
  change_30d_pct: number | null;
  change_1y_pct: number | null;
  signal: string;
}

export interface RadarRendaFixaItem {
  tipo: string;
  taxa_pct: number;
  vencimento: string;
  signal: string;
}

export interface RadarReport {
  generated_at: string;
  cache_expires_in_minutes: number;
  macro: RadarMacro;
  acoes: RadarAcaoItem[];
  fiis: RadarFiiItem[];
  crypto: RadarCryptoItem[];
  renda_fixa: RadarRendaFixaItem[];
}
