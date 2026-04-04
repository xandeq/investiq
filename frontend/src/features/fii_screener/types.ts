export interface FIIScoredRow {
  ticker: string;
  short_name: string | null;
  segmento: string | null;
  dy_12m: string | null;
  pvp: string | null;
  daily_liquidity: number | null;
  score: string | null;
  dy_rank: number | null;
  pvp_rank: number | null;
  liquidity_rank: number | null;
  score_updated_at: string | null;
}

export interface FIIScoredResponse {
  disclaimer: string;
  score_available: boolean;
  total: number;
  results: FIIScoredRow[];
}
