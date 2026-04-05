export interface FIIDividendMonth {
  month: string;  // "2026-01"
  rate: number;   // absolute R$ value per share
}

export interface FIIPortfolio {
  num_imoveis: number | null;
  tipo_contrato: string | null;
  vacancia: number | null;
}

export interface FIIDetailData {
  current_price: number | null;
  pvp: number | null;
  dy_12m: number | null;         // decimal ratio e.g. 0.0856 = 8.56%
  dividends_monthly: FIIDividendMonth[];
  portfolio: FIIPortfolio;
  last_dividend: number | null;
  daily_liquidity: number | null;
  book_value: number | null;
}

export interface FIIAnalysisResult {
  narrative: string;
  current_price: number | null;
  pvp: number | null;
  dy_12m: number | null;
  last_dividend: number | null;
  daily_liquidity: number | null;
  book_value: number | null;
  dividends_monthly: FIIDividendMonth[];
  portfolio: FIIPortfolio;
}
