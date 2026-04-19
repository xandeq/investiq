export interface PortfolioHealth {
  health_score: number;              // 0-100
  biggest_risk: string | null;       // one-sentence alert or null
  passive_income_monthly_brl: string; // Decimal as string from backend
  underperformers: string[];          // ["XXXX3 (-18%)", ...] max 3
  data_as_of: string | null;         // ISO datetime of screener snapshot
  total_assets: number;
  has_portfolio: boolean;
}

// ── Action Inbox v1 ─────────────────────────────────────────────────────────

export type InboxCardKind =
  | "concentration_risk"
  | "low_diversification"
  | "underperformer"
  | "no_passive_income"
  | "opportunity_detected"
  | "insight"
  | "watchlist_alert"
  | "swing_signal";

export type InboxSeverity = "info" | "warn" | "alert";

export interface InboxCardCTA {
  label: string;
  href: string;
}

export interface InboxCard {
  id: string;
  kind: InboxCardKind;
  priority: number;                  // 0..1
  title: string;
  body: string;
  ticker: string | null;
  severity: InboxSeverity;
  cta: InboxCardCTA | null;
  created_at: string;                // ISO UTC
}

export interface InboxMeta {
  sources_ok: string[];
  sources_failed: string[];
}

export interface InboxResponse {
  generated_at: string;
  cards: InboxCard[];
  meta: InboxMeta;
}
