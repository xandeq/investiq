// Phase 27 — Comparador RF vs RV types (client-side calc, per D-01)
// Replaces v1.0-era ComparadorRow / ComparadorResponse shapes.

export type TipoRF = "CDB" | "LCI" | "LCA" | "TESOURO_SELIC" | "TESOURO_IPCA";

export interface ComparadorInputs {
  valor: number;          // R$, e.g. 10000
  prazoMeses: number;     // months, e.g. 24
  tipoRF: TipoRF;
  taxaPct: number;        // user-editable annual rate for the selected tipo_rf (% a.a.)
  spreadPct: number;      // only used when tipoRF === "TESOURO_IPCA" (IPCA + spread% a.a.)
}

export interface ComparadorRow {
  label: string;              // "CDB 100% CDI" | "CDI" | "SELIC" | "IPCA+" | ...
  category: "produto_rf" | "cdi" | "selic" | "ipca";
  taxaBrutaAnualPct: number;  // % a.a. nominal gross rate
  taxaLiquidaAnualPct: number; // % a.a. after IR regressivo (equal to bruta when isento)
  isExempt: boolean;           // true for LCI/LCA
  irRateAnualPct: number;      // 0 when isExempt; otherwise 15/17.5/20/22.5
  retornoNominalPct: number;   // compound net return over prazoMeses (%)
  retornoRealPct: number;      // (1+nominal)/(1+ipcaAcum) - 1, in % — NaN when IPCA unavailable
  totalAcumuladoBRL: number;   // valor * (1 + retornoNominalPct/100)
}

export interface ProjectionPoint {
  mes: number;              // 0..prazoMeses
  produto_rf: number;       // acumulado em R$
  cdi: number;
  selic: number;
  ipca: number;
}

export interface ComparadorResult {
  rows: ComparadorRow[];       // length = 4 (produto_rf, cdi, selic, ipca)
  projection: ProjectionPoint[]; // length = prazoMeses + 1 (month 0 = valor inicial)
  ipcaAvailable: boolean;        // false when macro.ipca is null
}
