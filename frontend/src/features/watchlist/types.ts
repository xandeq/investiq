export interface WatchlistItem {
  id: string;
  tenant_id: string;
  ticker: string;
  notes: string | null;
  price_alert_target: string | null;
  created_at: string | null;
}

export interface WatchlistQuote {
  ticker: string;
  notes: string | null;
  price_alert_target: string | null;
  alert_triggered_at: string | null;
  price: string | null;
  data_stale: boolean;
  pl: string | null;
  dy: string | null;
  pvp: string | null;
}

export interface WatchlistItemCreate {
  ticker: string;
  notes?: string | null;
  price_alert_target?: number | null;
}

export interface WatchlistItemUpdate {
  notes?: string | null;
  price_alert_target?: number | null;
}
