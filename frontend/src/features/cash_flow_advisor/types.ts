export interface NextBigOutflow {
  date: string;
  amount: string;
  description: string;
}

export interface CashParkingRow {
  label: string;
  gross_annual_pct: string;
  holding_days: number;
  iof_pct: string;
  ir_pct: string;
  gross_value_brl: string;
  iof_value_brl: string;
  ir_value_brl: string;
  net_value_brl: string;
  net_pct: string;
  rank: number;
  note: string | null;
}

export interface CashParkingResponse {
  amount: string;
  holding_days: number;
  rows: CashParkingRow[];
  next_big_outflow: NextBigOutflow | null;
  generated_at: string;
  warnings: string[];
}
