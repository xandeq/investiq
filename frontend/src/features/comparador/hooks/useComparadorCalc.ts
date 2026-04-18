"use client";
import { useMemo } from "react";
import type {
  ComparadorInputs,
  ComparadorResult,
  ComparadorRow,
  ProjectionPoint,
  TipoRF,
} from "../types";
import type {
  MacroRatesResponse,
  FixedIncomeCatalogResponse,
} from "@/features/screener_v2/types";

// IR regressivo (CVM / Receita Federal) — applied to fixed-income yields by holding period.
function irRatePctByDays(days: number, isExempt: boolean): number {
  if (isExempt) return 0;
  if (days <= 180) return 22.5;
  if (days <= 360) return 20;
  if (days <= 720) return 17.5;
  return 15;
}

// Annualize a rate over a holding window (compound). Copied from RendaFixaContent.tsx.
function annualizeRate(annualPct: number, holdingDays: number): number {
  return ((1 + annualPct / 100) ** (holdingDays / 365) - 1) * 100;
}

function tipoRfIsExempt(tipo: TipoRF): boolean {
  return tipo === "LCI" || tipo === "LCA";
}

function tipoRfLabel(tipo: TipoRF): string {
  switch (tipo) {
    case "CDB": return "CDB";
    case "LCI": return "LCI";
    case "LCA": return "LCA";
    case "TESOURO_SELIC": return "Tesouro Selic";
    case "TESOURO_IPCA": return "Tesouro IPCA+";
  }
}

// Given a gross annual rate (%) and holding days, return the net annual rate (%) after IR.
// IR is applied to the GROSS RATE (not the return) — an approximation that's standard for
// market-facing comparison tools where precision below 0.1% is not required.
function netAnnualRate(grossPct: number, days: number, isExempt: boolean): number {
  const ir = irRatePctByDays(days, isExempt);
  return grossPct * (1 - ir / 100);
}

// Build a row for one alternative.
function buildRow(
  label: string,
  category: ComparadorRow["category"],
  grossAnnualPct: number,
  days: number,
  isExempt: boolean,
  valor: number,
  ipcaNominalPct: number | null,
): ComparadorRow {
  const ir = irRatePctByDays(days, isExempt);
  const netAnnual = netAnnualRate(grossAnnualPct, days, isExempt);
  const retornoNominalPct = annualizeRate(netAnnual, days);
  const retornoRealPct =
    ipcaNominalPct === null || !Number.isFinite(ipcaNominalPct)
      ? Number.NaN
      : ((1 + retornoNominalPct / 100) / (1 + ipcaNominalPct / 100) - 1) * 100;
  const totalAcumuladoBRL = valor * (1 + retornoNominalPct / 100);
  return {
    label,
    category,
    taxaBrutaAnualPct: grossAnnualPct,
    taxaLiquidaAnualPct: netAnnual,
    isExempt,
    irRateAnualPct: ir,
    retornoNominalPct,
    retornoRealPct,
    totalAcumuladoBRL,
  };
}

// Fallback to a sensible representative rate for the tipo_rf from the catalog, used as
// the default value for the editable taxa input.
export function getDefaultRateForTipo(
  tipo: TipoRF,
  catalog: FixedIncomeCatalogResponse | undefined,
  macro: MacroRatesResponse | undefined,
): number {
  // CDB/LCI/LCA: use catalog midpoint for the matching instrument_type
  if (tipo === "CDB" || tipo === "LCI" || tipo === "LCA") {
    const row = catalog?.results.find((r) => r.instrument_type === tipo);
    if (row) {
      const min = parseFloat(row.min_rate_pct);
      const max = row.max_rate_pct ? parseFloat(row.max_rate_pct) : min;
      const mid = (min + max) / 2;
      // CDB rates in the catalog are expressed as "% of CDI" (e.g. 105 meaning 105% CDI)
      // LCI/LCA are absolute annual rates. Use catalog `indexer` to disambiguate.
      if (row.indexer === "CDI") {
        const cdi = macro?.cdi ? parseFloat(macro.cdi) : 0;
        return (mid / 100) * cdi;
      }
      return mid;
    }
    // Fallback: if no catalog row, use CDI as a conservative default
    return macro?.cdi ? parseFloat(macro.cdi) : 10;
  }
  if (tipo === "TESOURO_SELIC") {
    return macro?.selic ? parseFloat(macro.selic) : 14.75;
  }
  // TESOURO_IPCA: taxa = 0 (base rate unused — spread is added separately)
  return 0;
}

export function useComparadorCalc(
  inputs: ComparadorInputs,
  macro: MacroRatesResponse | undefined,
  catalog: FixedIncomeCatalogResponse | undefined,
): ComparadorResult {
  return useMemo(() => {
    const days = Math.max(1, Math.round((inputs.prazoMeses / 12) * 365));
    const ipca = macro?.ipca ? parseFloat(macro.ipca) : null;
    const cdi = macro?.cdi ? parseFloat(macro.cdi) : 0;
    const selic = macro?.selic ? parseFloat(macro.selic) : 0;
    const ipcaAvailable = ipca !== null && Number.isFinite(ipca);

    // ── produto RF gross rate ─────────────────────────────────────────────
    let produtoGross = inputs.taxaPct;
    if (inputs.tipoRF === "TESOURO_IPCA") {
      produtoGross = (ipca ?? 0) + inputs.spreadPct;
    }
    const produtoExempt = tipoRfIsExempt(inputs.tipoRF);

    // ipcaNominalPct for real return calculation: annualized IPCA return over holding period
    const ipcaNominalForReal = ipcaAvailable
      ? annualizeRate(ipca!, days)
      : null;

    const rows: ComparadorRow[] = [
      buildRow(tipoRfLabel(inputs.tipoRF), "produto_rf", produtoGross, days, produtoExempt, inputs.valor, ipcaNominalForReal),
      buildRow("CDI", "cdi", cdi, days, false, inputs.valor, ipcaNominalForReal),
      buildRow("SELIC", "selic", selic, days, false, inputs.valor, ipcaNominalForReal),
      buildRow("IPCA+", "ipca", ipca ?? 0, days, false, inputs.valor, ipcaNominalForReal),
    ];

    // ── Month-by-month projection (compound) ──────────────────────────────
    const projection: ProjectionPoint[] = [];
    const monthlyRate = (annualNetPct: number) =>
      (1 + annualNetPct / 100) ** (1 / 12) - 1;
    const r = {
      produto_rf: monthlyRate(rows[0].taxaLiquidaAnualPct),
      cdi: monthlyRate(rows[1].taxaLiquidaAnualPct),
      selic: monthlyRate(rows[2].taxaLiquidaAnualPct),
      ipca: monthlyRate(rows[3].taxaLiquidaAnualPct),
    };
    for (let m = 0; m <= inputs.prazoMeses; m++) {
      projection.push({
        mes: m,
        produto_rf: inputs.valor * (1 + r.produto_rf) ** m,
        cdi: inputs.valor * (1 + r.cdi) ** m,
        selic: inputs.valor * (1 + r.selic) ** m,
        ipca: inputs.valor * (1 + r.ipca) ** m,
      });
    }

    return { rows, projection, ipcaAvailable };
  }, [inputs.valor, inputs.prazoMeses, inputs.tipoRF, inputs.taxaPct, inputs.spreadPct, macro?.cdi, macro?.ipca, macro?.selic, catalog]);
}
