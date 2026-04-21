// Phase 28 — Simulador de Alocação types (client-side calc, mirrors Phase 27 pattern)
// Replaces v1.0-era types (pessimista/base/otimista + caixa) with v1.7 architecture
// (conservador/moderado/arrojado + RF/ações/FIIs).

export type ScenarioKey = "conservador" | "moderado" | "arrojado";

export interface ScenarioAllocation {
  rf_pct: number;     // e.g. 80
  acoes_pct: number;  // e.g. 10
  fiis_pct: number;   // e.g. 10
}

export interface SimuladorInputs {
  valor: number;        // R$, e.g. 10000
  prazoMeses: number;   // months, e.g. 24
}

export interface ClassProjection {
  pct: number;                 // % of valor allocated to this class (e.g. 80)
  valor_alocado_brl: number;   // valor * pct / 100
  taxa_bruta_anual_pct: number; // gross annual rate (% a.a.) used for this class
  ir_rate_pct: number;          // IR applied (0 for acoes/fiis, 22.5/20/17.5/15 for RF by days)
  taxa_liquida_anual_pct: number; // net annual rate after IR
  retorno_nominal_pct: number;   // compound net return over prazoMeses (%)
  valor_final_brl: number;       // valor_alocado_brl * (1 + retorno_nominal_pct / 100)
}

export interface ScenarioResult {
  key: ScenarioKey;            // "conservador" | "moderado" | "arrojado"
  label: string;               // "Conservador" | "Moderado" | "Arrojado"
  allocation: ScenarioAllocation; // percentages per class
  rf: ClassProjection;
  acoes: ClassProjection;
  fiis: ClassProjection;
  total_investido_brl: number; // === inputs.valor (for convenience)
  total_projetado_brl: number; // rf.valor_final_brl + acoes.valor_final_brl + fiis.valor_final_brl
  retorno_total_pct: number;   // (total_projetado - total_investido) / total_investido * 100
}

export interface SimuladorResult {
  scenarios: [ScenarioResult, ScenarioResult, ScenarioResult]; // always length 3
  holdingDays: number;         // round(prazoMeses / 12 * 365), min 1
  cdiUsed: number;             // CDI % a.a. used for RF projection (0 if macro unavailable)
}

// Hardcoded allocations per D-01 (locked in CONTEXT / STATE.md v1.7 Architecture)
export const SCENARIO_ALLOCATIONS: Record<ScenarioKey, ScenarioAllocation> = {
  conservador: { rf_pct: 80, acoes_pct: 10, fiis_pct: 10 },
  moderado:    { rf_pct: 50, acoes_pct: 35, fiis_pct: 15 },
  arrojado:    { rf_pct: 20, acoes_pct: 65, fiis_pct: 15 },
};

// Hardcoded proxy gross annual rates for RV classes (no macro feed for these — Phase 28 scope).
// Documented in STATE.md "Projeção de retorno por classe":
//   - Ações: IBOV histórico anualizado ~12% a.a. nominal (no IR for PF held >1y, simplification)
//   - FIIs: DY médio ~8% a.a. nominal (no IR for PF investors)
export const ACOES_GROSS_ANNUAL_PCT = 12; // fixed — Phase 28 does not model equity risk
export const FIIS_GROSS_ANNUAL_PCT = 8;   // fixed — FII DY proxy
