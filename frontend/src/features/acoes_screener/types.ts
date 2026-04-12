export interface AcoesUniverseRow {
  ticker: string;
  short_name: string | null;
  sector: string | null;
  regular_market_price: string | null; // Decimal from API comes as string
  variacao_12m_pct: string | null;
  dy: string | null;
  pl: string | null;
  market_cap: number | null;
}

export interface AcoesUniverseResponse {
  disclaimer: string;
  results: AcoesUniverseRow[];
}
