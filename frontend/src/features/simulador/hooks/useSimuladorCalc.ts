"use client";
import { useMemo } from "react";
import type {
  ScenarioKey,
  ScenarioResult,
  SimuladorInputs,
  SimuladorResult,
  ClassProjection,
} from "../types";
import {
  SCENARIO_ALLOCATIONS,
  ACOES_GROSS_ANNUAL_PCT,
  FIIS_GROSS_ANNUAL_PCT,
} from "../types";
import type { MacroRatesResponse } from "@/features/screener_v2/types";

// ── IR + annualize helpers (replicated from useComparadorCalc — keep simulador self-contained)

/** IR regressivo brackets per CVM / Receita Federal, applied to gross RF rate. */
function irRatePctByDays(days: number, isExempt: boolean): number {
  if (isExempt) return 0;
  if (days <= 180) return 22.5;
  if (days <= 360) return 20;
  if (days <= 720) return 17.5;
  return 15;
}

/** Annualize a rate over a holding window (compound). */
function annualizeRate(annualPct: number, holdingDays: number): number {
  return ((1 + annualPct / 100) ** (holdingDays / 365) - 1) * 100;
}

/** Apply IR to gross annual rate (approximation standard for market tools). */
function netAnnualRate(grossPct: number, days: number, isExempt: boolean): number {
  const ir = irRatePctByDays(days, isExempt);
  return grossPct * (1 - ir / 100);
}

// ── Projection builders

function projectClass(
  pct: number,
  valor: number,
  grossAnnualPct: number,
  days: number,
  isExempt: boolean,
): ClassProjection {
  const valor_alocado_brl = (valor * pct) / 100;
  const ir = irRatePctByDays(days, isExempt);
  const taxa_liquida = netAnnualRate(grossAnnualPct, days, isExempt);
  const retorno_nominal_pct = annualizeRate(taxa_liquida, days);
  const valor_final_brl = valor_alocado_brl * (1 + retorno_nominal_pct / 100);
  return {
    pct,
    valor_alocado_brl,
    taxa_bruta_anual_pct: grossAnnualPct,
    ir_rate_pct: ir,
    taxa_liquida_anual_pct: taxa_liquida,
    retorno_nominal_pct,
    valor_final_brl,
  };
}

const SCENARIO_LABELS: Record<ScenarioKey, string> = {
  conservador: "Conservador",
  moderado: "Moderado",
  arrojado: "Arrojado",
};

function buildScenario(
  key: ScenarioKey,
  valor: number,
  days: number,
  cdiPct: number,
): ScenarioResult {
  const allocation = SCENARIO_ALLOCATIONS[key];
  // RF uses CDI as gross rate proxy + IR regressivo by holding days (not isento).
  const rf = projectClass(allocation.rf_pct, valor, cdiPct, days, false);
  // Ações: fixed 12% gross, no IR (Phase 28 simplification — PF holding >1y).
  const acoes = projectClass(allocation.acoes_pct, valor, ACOES_GROSS_ANNUAL_PCT, days, true);
  // FIIs: fixed 8% gross, no IR (PF isento em rendimentos de FII).
  const fiis = projectClass(allocation.fiis_pct, valor, FIIS_GROSS_ANNUAL_PCT, days, true);
  const total_projetado_brl =
    rf.valor_final_brl + acoes.valor_final_brl + fiis.valor_final_brl;
  const retorno_total_pct = valor > 0
    ? ((total_projetado_brl - valor) / valor) * 100
    : 0;
  return {
    key,
    label: SCENARIO_LABELS[key],
    allocation,
    rf,
    acoes,
    fiis,
    total_investido_brl: valor,
    total_projetado_brl,
    retorno_total_pct,
  };
}

/**
 * Phase 28 — Simulador de Alocação client-side calculator.
 *
 * Given `valor` (R$) and `prazoMeses`, returns 3 scenarios (conservador / moderado / arrojado)
 * each with RF / ações / FIIs projections. RF uses CDI from macro rates with IR regressivo.
 * Ações/FIIs use fixed proxy rates (no IR for PF) — see types.ts constants.
 *
 * Defensive: when `macro` is undefined or `macro.cdi` is null, cdiPct falls back to 0 (so
 * RF projection yields 0% but the hook still returns 3 well-formed scenarios).
 */
export function useSimuladorCalc(
  inputs: SimuladorInputs,
  macro: MacroRatesResponse | undefined,
): SimuladorResult {
  return useMemo(() => {
    const days = Math.max(1, Math.round((inputs.prazoMeses / 12) * 365));
    const cdiPct = macro?.cdi ? parseFloat(macro.cdi) : 0;
    const cdiUsed = Number.isFinite(cdiPct) ? cdiPct : 0;

    const scenarios: [ScenarioResult, ScenarioResult, ScenarioResult] = [
      buildScenario("conservador", inputs.valor, days, cdiUsed),
      buildScenario("moderado", inputs.valor, days, cdiUsed),
      buildScenario("arrojado", inputs.valor, days, cdiUsed),
    ];

    return { scenarios, holdingDays: days, cdiUsed };
  }, [inputs.valor, inputs.prazoMeses, macro?.cdi]);
}
