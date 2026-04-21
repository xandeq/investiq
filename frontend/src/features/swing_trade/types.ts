// TypeScript contracts for the Swing Trade module (Phase 20).
//
// These mirror the pydantic schemas at
// backend/app/modules/swing_trade/schemas.py exactly. Decimal fields on the
// backend are serialized as JSON strings or numbers depending on the pydantic
// config — for the /swing-trade router they are emitted as numbers, so we
// type them as `number` on the wire. Nullable fields match the backend's
// `| None = None` defaults.

export type SwingSignal = "buy" | "sell" | "neutral";
export type OperationStatus = "open" | "closed" | "stopped";
export type LiveSignal = "hold" | "sell" | "stop";

export interface SwingSignalItem {
  ticker: string;
  name: string;
  sector: string;
  current_price: number;
  high_30d: number;
  discount_pct: number; // negative = down from 30d high
  dy: number | null;
  signal: SwingSignal;
  signal_strength: number; // abs(discount_pct)
  in_portfolio: boolean;
  quantity: number | null;
}

export interface SwingSignalsResponse {
  portfolio_signals: SwingSignalItem[];
  radar_signals: SwingSignalItem[];
  generated_at: string; // ISO 8601 datetime
}

export interface SwingOperation {
  id: string;
  ticker: string;
  asset_class: string;
  quantity: number;
  entry_price: number;
  entry_date: string; // ISO 8601 datetime
  target_price: number | null;
  stop_price: number | null;
  status: OperationStatus;
  exit_price: number | null;
  exit_date: string | null;
  notes: string | null;
  created_at: string;

  // Enriched (read-side)
  current_price: number | null;
  pnl_pct: number | null;
  pnl_brl: number | null;
  days_open: number | null;
  target_progress_pct: number | null;
  live_signal: LiveSignal | null;
}

export interface OperationListResponse {
  open_count: number;
  closed_count: number;
  results: SwingOperation[];
}

export interface OperationCreatePayload {
  ticker: string;
  asset_class?: string;
  quantity: number;
  entry_price: number;
  entry_date: string; // ISO 8601 datetime
  target_price?: number;
  stop_price?: number;
  notes?: string;
}

export interface OperationClosePayload {
  exit_price: number;
  exit_date?: string; // ISO 8601 datetime
}

// ---------------------------------------------------------------------------
// Copilot types
// ---------------------------------------------------------------------------

export interface SwingPick {
  ticker: string;
  tese: string;
  entrada: number;
  stop_loss: number;
  stop_gain: number;
  rr: number;
  prazo: string;   // "dias" | "semanas" | "meses"
  confianca: string; // "alta" | "média" | "baixa"
  motivo: string;
}

export interface DividendPlay {
  ticker: string;
  tese: string;
  entrada: number;
  stop_loss: number;
  alvo_preco: number;
  dy_estimado: string;
  prazo_sugerido: string;
  motivo_desconto: string;
}

export interface CopilotResponse {
  swing_picks: SwingPick[];
  dividend_plays: DividendPlay[];
  universe_scanned: number;
  from_cache: boolean;
  error?: string | null;
}
