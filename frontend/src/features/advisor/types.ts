export interface PortfolioHealth {
  health_score: number;              // 0-100
  biggest_risk: string | null;       // one-sentence alert or null
  passive_income_monthly_brl: string; // Decimal as string from backend
  underperformers: string[];          // ["XXXX3 (-18%)", ...] max 3
  data_as_of: string | null;         // ISO datetime of screener snapshot
  total_assets: number;
  has_portfolio: boolean;
}

export interface AdvisorAnalysisResult {
  diagnostico: string;
  pontos_positivos: string[];
  pontos_de_atencao: string[];
  sugestoes: string[];
  proximos_passos: string[];
  disclaimer: string;
  // Health snapshot included in AI result
  health_score: number | null;
  biggest_risk: string | null;
  passive_income_monthly_brl: string | null;
  underperformers: string[];
  completed_at: string | null;
}

export type AdvisorJobStatus = "pending" | "running" | "completed" | "failed";

export interface AdvisorJobResponse {
  job_id: string;
  status: AdvisorJobStatus;
  disclaimer: string;
  result: AdvisorAnalysisResult | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface AdvisorStartResponse {
  job_id: string;
  status: string;
  disclaimer: string;
}

// ── Smart Screener (Phase 25 — ADVI-03) ─────────────────────────────────────

export interface ComplementaryAsset {
  ticker: string;
  sector: string | null;
  preco_atual: number | null;        // regular_market_price from ScreenerSnapshot
  dy_12m_pct: number | null;         // dy from ScreenerSnapshot (fractional, e.g. 0.12 = 12%)
  variacao_12m_pct: number | null;   // variacao_12m_pct from ScreenerSnapshot (fractional)
  market_cap: number | null;
  relevance_score: number;           // 0-100, higher = more complementary
}

// ── Entry Signals (Phase 26 — ADVI-04) ──────────────────────────────────────

export interface EntrySignal {
  ticker: string;
  suggested_amount_brl: string;     // Decimal as string ("1000.00")
  target_upside_pct: number;        // positive = expected recovery %, e.g. 15.0 = 15%
  timeframe_days: number;           // swing-trade horizon (fixed 90)
  stop_loss_pct: number;            // stop-loss % (fixed 8.0)
  rsi: number | null;               // RSI value (null if unavailable)
  ma_signal: string | null;         // "buy" | "sell" | "neutral"
  generated_at: string;             // ISO datetime UTC
}
