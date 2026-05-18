export interface PositionResponse {
  ticker: string;
  asset_class: string;
  quantity: string;
  cmp: string;
  total_cost: string;
  current_price: string | null;
  current_price_stale: boolean;
  unrealized_pnl: string | null;
  unrealized_pnl_pct: string | null;
}

export interface AllocationItem {
  asset_class: string;
  total_value: string;
  percentage: string;
}

export interface PnLResponse {
  positions: PositionResponse[];
  realized_pnl_total: string;
  unrealized_pnl_total: string;
  total_portfolio_value: string;
  total_invested: string;
  total_return_pct: string | null;
  allocation: AllocationItem[];
}

export interface DividendResponse {
  id: string;
  ticker: string;
  asset_class: string;
  transaction_type: string;
  transaction_date: string;  // "YYYY-MM-DD"
  quantity: string;
  unit_price: string;
  total_value: string;
  is_exempt: boolean;
}

export interface BenchmarkResponse {
  cdi: string | null;
  ibovespa_price: string | null;
  data_stale: boolean;
  fetched_at: string | null;
}

export interface TransactionResponse {
  id: string;
  ticker: string;
  asset_class: string;
  transaction_type: string;
  transaction_date: string; // "YYYY-MM-DD"
  quantity: string;
  unit_price: string;
  total_value: string;
  brokerage_fee: string | null;
  irrf_withheld: string | null;
  gross_profit: string | null;
  notes: string | null;
  is_exempt: boolean;
  coupon_rate: string | null;
  maturity_date: string | null;
  created_at: string | null;
}

export interface TransactionCreate {
  ticker: string;
  asset_class: string;
  transaction_type: string;
  transaction_date: string;
  quantity: string;
  unit_price: string;
  brokerage_fee?: string | null;
  notes?: string | null;
  is_exempt?: boolean;
  coupon_rate?: string | null;
  maturity_date?: string | null;
}

export interface TransactionUpdate {
  transaction_date?: string;
  quantity?: string;
  unit_price?: string;
  brokerage_fee?: string | null;
  notes?: string | null;
  is_exempt?: boolean;
}

// ─── Phase 42: Investment Goals ───────────────────────────────────────────────

export type GoalStatus = "nao_iniciado" | "em_andamento" | "em_risco" | "concluido";

export interface GoalResponse {
  id: string;
  tenant_id: string;
  name: string;
  target_amount: string;
  current_amount: string;
  asset_class: string | null;
  deadline: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
  progress_pct: string;
  remaining_amount: string;
  months_to_deadline: number | null;
  monthly_contribution_needed: string | null;
  status: GoalStatus;
  auto_current_amount: string | null;
}

export interface GoalCreate {
  name: string;
  target_amount: string;
  current_amount?: string;
  asset_class?: string | null;
  deadline?: string | null;
  notes?: string | null;
}

export interface GoalUpdate {
  name?: string;
  target_amount?: string;
  current_amount?: string;
  asset_class?: string | null;
  deadline?: string | null;
  notes?: string | null;
}
