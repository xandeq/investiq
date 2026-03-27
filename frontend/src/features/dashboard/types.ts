export interface AllocationItem {
  asset_class: string;
  value: string;   // Decimal as string — e.g. "120000.00"
  pct: string;     // Decimal as string — e.g. "64.72"
}

export interface TimeseriesPoint {
  date: string;    // "YYYY-MM-DD"
  value: string;   // Decimal as string
}

export interface RecentTransaction {
  ticker: string;
  type: string;    // "buy" | "sell"
  quantity: string;
  unit_price: string;
  date: string;    // "YYYY-MM-DD"
}

export interface DashboardSummary {
  net_worth: string;
  total_invested: string;
  total_return: string;
  total_return_pct: string;
  daily_pnl: string;
  daily_pnl_pct: string;
  data_stale: boolean;
  asset_allocation: AllocationItem[];
  portfolio_timeseries: TimeseriesPoint[];
  recent_transactions: RecentTransaction[];
}
