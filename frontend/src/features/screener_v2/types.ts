// Phase 8: Snapshot-based screener + renda fixa catalog types

export interface AcaoRow {
  ticker: string;
  short_name: string | null;
  sector: string | null;
  price: string | null;
  change_pct: string | null;
  volume: number | null;
  market_cap: number | null;
  pl: string | null;
  pvp: string | null;
  dy: string | null;
  ev_ebitda: string | null;
  snapshot_date: string;
}

export interface AcaoScreenerResponse {
  disclaimer: string;
  total: number;
  limit: number;
  offset: number;
  results: AcaoRow[];
}

export interface AcaoScreenerParams {
  min_dy?: number;
  max_pl?: number;
  max_pvp?: number;
  max_ev_ebitda?: number;
  sector?: string;
  min_volume?: number;
  min_market_cap?: number;
  exclude_portfolio?: boolean;
  limit?: number;
  offset?: number;
}

export interface FIIRow {
  ticker: string;
  short_name: string | null;
  segmento: string | null;
  price: string | null;
  change_pct: string | null;
  volume: number | null;
  pvp: string | null;
  dy: string | null;
  vacancia_financeira: string | null;
  num_cotistas: number | null;
  snapshot_date: string;
}

export interface FIIScreenerResponse {
  disclaimer: string;
  total: number;
  limit: number;
  offset: number;
  results: FIIRow[];
}

export interface FIIScreenerParams {
  min_dy?: number;
  max_pvp?: number;
  segmento?: string;
  max_vacancia?: number;
  min_cotistas?: number;
  min_volume?: number;
  exclude_portfolio?: boolean;
  limit?: number;
  offset?: number;
}

export interface IRBreakdown {
  period_label: string;
  holding_days: number;
  gross_pct: string;
  ir_rate_pct: string;
  net_pct: string;
  is_exempt: boolean;
}

export interface FixedIncomeCatalogRow {
  instrument_type: string;
  indexer: string;
  label: string;
  min_months: number;
  max_months: number | null;
  min_rate_pct: string;
  max_rate_pct: string | null;
  ir_breakdowns: IRBreakdown[];
}

export interface FixedIncomeCatalogResponse {
  results: FixedIncomeCatalogRow[];
}

export interface TesouroRateRow {
  tipo_titulo: string;
  vencimento: string;
  taxa_indicativa: string | null;
  pu: string | null;
  data_base: string;
  source: string;
}

export interface TesouroRatesResponse {
  results: TesouroRateRow[];
}
