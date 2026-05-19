export interface FundSearchResult {
  cnpj: string;
  name: string;
  admin: string | null;
  fund_class: string | null;
}

export interface FundInfoResponse {
  cnpj: string;
  name: string;
  admin: string | null;
  fund_class: string | null;
  status: string | null;
}

export interface FundPosition {
  cnpj: string;
  name: string;
  quantity: string;
  cmp: string;
  total_cost: string;
  current_nav: string | null;
  nav_stale: boolean;
  unrealized_pnl: string | null;
  unrealized_pnl_pct: string | null;
  quote_date: string | null;
}
