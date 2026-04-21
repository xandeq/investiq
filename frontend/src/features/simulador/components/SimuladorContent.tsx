"use client";
import { useState } from "react";
import { useMacroRates } from "@/features/screener_v2/hooks/useRendaFixa";
import { useSimuladorCalc } from "../hooks/useSimuladorCalc";
import { useSimuladorPortfolio } from "../hooks/useSimuladorPortfolio";
import type { ScenarioKey, ScenarioResult } from "../types";

// ── Local formatting utilities ───────────────────────────────────────────────

function fmtBRL(n: number): string {
  if (!Number.isFinite(n)) return "—";
  return "R$ " + n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtPct(n: number, decimals = 2): string {
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(decimals) + "%";
}

// ── Scenario card sub-component ──────────────────────────────────────────────

interface ScenarioCardProps {
  scenario: ScenarioResult;
  isSelected: boolean;
  prazoMeses: number;
  onClick: () => void;
}

function ScenarioCard({ scenario, isSelected, prazoMeses, onClick }: ScenarioCardProps) {
  const cardClass = isSelected
    ? "rounded-xl border-2 border-blue-500 bg-blue-50 p-5 text-left w-full"
    : "rounded-xl border-2 border-gray-200 bg-white hover:border-blue-300 p-5 text-left w-full";

  const { rf_pct, acoes_pct, fiis_pct } = scenario.allocation;

  // scenario.key is one of:
  //   "conservador" — 80% RF, 10% Ações, 10% FIIs (perfil conservador)
  //   "moderado"    — 50% RF, 35% Ações, 15% FIIs (perfil moderado)
  //   "arrojado"    — 20% RF, 65% Ações, 15% FIIs (perfil arrojado)
  return (
    <button className={cardClass} onClick={onClick} data-testid={`scenario-${scenario.key}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-bold text-gray-800">{scenario.label}</span>
        <span className="text-xs text-gray-500">
          RF {rf_pct}% · Ações {acoes_pct}% · FIIs {fiis_pct}%
        </span>
      </div>

      {/* Big total */}
      <div className="text-2xl font-bold text-emerald-600">
        {fmtBRL(scenario.total_projetado_brl)}
      </div>
      <div className="text-xs text-gray-500 mb-3">
        Total em {prazoMeses} meses · {fmtPct(scenario.retorno_total_pct)}
      </div>

      {/* Per-class breakdown */}
      <div>
        {/* RF row */}
        <div className="flex items-center justify-between text-xs py-1 border-t border-gray-100">
          <span className="flex items-center">
            <span className="w-2 h-2 rounded-sm bg-emerald-500 inline-block mr-1.5" />
            RF · {rf_pct}%
          </span>
          <div className="text-right">
            <span className="font-medium text-gray-700">{fmtBRL(scenario.rf.valor_final_brl)}</span>
            <div className="text-gray-400 text-[10px]">
              {fmtPct(scenario.rf.retorno_nominal_pct)} (IR {fmtPct(scenario.rf.ir_rate_pct, 1)})
            </div>
          </div>
        </div>

        {/* Ações row */}
        <div className="flex items-center justify-between text-xs py-1 border-t border-gray-100">
          <span className="flex items-center">
            <span className="w-2 h-2 rounded-sm bg-purple-500 inline-block mr-1.5" />
            Ações · {acoes_pct}%
          </span>
          <div className="text-right">
            <span className="font-medium text-gray-700">{fmtBRL(scenario.acoes.valor_final_brl)}</span>
            <div className="text-gray-400 text-[10px]">
              {fmtPct(scenario.acoes.retorno_nominal_pct)} (IR {fmtPct(scenario.acoes.ir_rate_pct, 1)})
            </div>
          </div>
        </div>

        {/* FIIs row */}
        <div className="flex items-center justify-between text-xs py-1 border-t border-gray-100">
          <span className="flex items-center">
            <span className="w-2 h-2 rounded-sm bg-blue-500 inline-block mr-1.5" />
            FIIs · {fiis_pct}%
          </span>
          <div className="text-right">
            <span className="font-medium text-gray-700">{fmtBRL(scenario.fiis.valor_final_brl)}</span>
            <div className="text-gray-400 text-[10px]">
              {fmtPct(scenario.fiis.retorno_nominal_pct)} (IR {fmtPct(scenario.fiis.ir_rate_pct, 1)})
            </div>
          </div>
        </div>
      </div>
    </button>
  );
}

// ── Delta section ─────────────────────────────────────────────────────────────

interface DeltaRowData {
  key: string;
  label: string;
  dotColor: string;
  target: number;
  current: number;
}

interface DeltaSectionProps {
  selected: ScenarioResult;
  hasPortfolio: boolean;
  loadingPortfolio: boolean;
  portfolioTotalBRL: number;
  valor: number;
  currentAllocation: { rf_brl: number; acoes_brl: number; fiis_brl: number };
}

function DeltaSection({
  selected,
  hasPortfolio,
  loadingPortfolio,
  portfolioTotalBRL,
  valor,
  currentAllocation,
}: DeltaSectionProps) {
  const rows: DeltaRowData[] = [
    {
      key: "rf",
      label: "Renda Fixa",
      dotColor: "bg-emerald-500",
      target: selected.rf.valor_alocado_brl,
      current: currentAllocation.rf_brl,
    },
    {
      key: "acoes",
      label: "Ações",
      dotColor: "bg-purple-500",
      target: selected.acoes.valor_alocado_brl,
      current: currentAllocation.acoes_brl,
    },
    {
      key: "fiis",
      label: "FIIs",
      dotColor: "bg-blue-500",
      target: selected.fiis.valor_alocado_brl,
      current: currentAllocation.fiis_brl,
    },
  ];

  return (
    <div className="space-y-3">
      <h2 className="text-base font-bold text-gray-800">
        Delta vs carteira atual — {selected.label}
      </h2>

      {loadingPortfolio ? (
        <div className="h-24 rounded-lg bg-gray-100 animate-pulse" />
      ) : !hasPortfolio ? (
        <div className="rounded-lg border border-gray-200 bg-white p-5 text-center">
          <p className="text-sm text-gray-700 mb-3">
            Cadastre suas transações para ver o <strong>Delta de Alocação</strong> — quanto comprar
            ou reduzir em cada classe para chegar no cenário selecionado.
          </p>
          <a
            href="/portfolio/transactions"
            className="inline-block rounded-md bg-blue-500 text-white px-5 py-2 text-sm font-medium hover:bg-blue-600 transition-colors"
          >
            Cadastrar transações
          </a>
        </div>
      ) : (
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          {/* Header row */}
          <div className="grid grid-cols-4 gap-2 text-xs font-semibold text-gray-500 uppercase tracking-wide pb-2 border-b border-gray-200">
            <span>Classe</span>
            <span>Atual</span>
            <span>Alvo</span>
            <span>Ação</span>
          </div>

          {/* Data rows */}
          {rows.map((row) => {
            const delta = row.target - row.current;
            let actionCell: React.ReactNode;
            if (delta > 0.01) {
              actionCell = (
                <span className="text-emerald-600 font-semibold">Comprar +{fmtBRL(delta)}</span>
              );
            } else if (delta < -0.01) {
              actionCell = (
                <span className="text-red-600 font-semibold">Reduzir -{fmtBRL(Math.abs(delta))}</span>
              );
            } else {
              actionCell = <span className="text-gray-500">Manter</span>;
            }

            return (
              <div key={row.key} className="grid grid-cols-4 gap-2 items-center py-2 text-sm border-t border-gray-100 first:border-t-0">
                <span className="flex items-center gap-1.5">
                  <span className={`w-2 h-2 rounded-sm inline-block ${row.dotColor}`} />
                  {row.label}
                </span>
                <span>{fmtBRL(row.current)}</span>
                <span>{fmtBRL(row.target)}</span>
                <span>{actionCell}</span>
              </div>
            );
          })}

          {/* Footer */}
          <p className="text-xs text-gray-400 mt-2">
            Carteira atual: <strong>{fmtBRL(portfolioTotalBRL)}</strong> · Simulação baseada em{" "}
            <strong>{fmtBRL(valor)}</strong>
          </p>
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function SimuladorContent() {
  const [valor, setValor] = useState<number>(10000);
  const [prazoMeses, setPrazoMeses] = useState<number>(24);
  const [selectedKey, setSelectedKey] = useState<ScenarioKey>("moderado");

  const { data: macro, isLoading: loadingMacro } = useMacroRates();
  const {
    hasPortfolio,
    isLoading: loadingPortfolio,
    portfolioTotalBRL,
    currentAllocation,
  } = useSimuladorPortfolio();
  const result = useSimuladorCalc({ valor, prazoMeses }, macro);

  const selected = result.scenarios.find((s) => s.key === selectedKey)!;

  return (
    <div className="space-y-6">
      {/* CVM Disclaimer */}
      <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
        Análise informativa — não constitui recomendação de investimento (CVM Res. 19/2021).
      </div>

      {/* Form card */}
      <div className="rounded-lg border border-gray-200 bg-white p-4 flex flex-wrap gap-4 items-end">
        {/* Valor */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Valor (R$)</label>
          <input
            type="number"
            min="0"
            value={valor}
            onChange={(e) => setValor(parseFloat(e.target.value) || 0)}
            className="w-36 rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
          />
        </div>

        {/* Prazo */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Prazo (meses)</label>
          <input
            type="number"
            min="1"
            max="360"
            value={prazoMeses}
            onChange={(e) => setPrazoMeses(parseInt(e.target.value, 10) || 1)}
            className="w-28 rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
          />
        </div>

        {/* CDI indicator */}
        <div className="ml-auto text-xs text-gray-500 self-center">
          CDI:{" "}
          <strong>
            {macro?.cdi ? `${parseFloat(macro.cdi).toFixed(2)}% a.a.` : "—"}
          </strong>
        </div>
      </div>

      {/* Loading skeleton */}
      {loadingMacro && <div className="h-40 rounded-lg bg-gray-100 animate-pulse" />}

      {/* Scenario cards */}
      {!loadingMacro && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {result.scenarios.map((scenario) => (
            <ScenarioCard
              key={scenario.key}
              scenario={scenario}
              isSelected={scenario.key === selectedKey}
              prazoMeses={prazoMeses}
              onClick={() => setSelectedKey(scenario.key)}
            />
          ))}
        </div>
      )}

      {/* Delta section */}
      {!loadingMacro && selected && (
        <DeltaSection
          selected={selected}
          hasPortfolio={hasPortfolio}
          loadingPortfolio={loadingPortfolio}
          portfolioTotalBRL={portfolioTotalBRL}
          valor={valor}
          currentAllocation={currentAllocation}
        />
      )}

      {/* Footer disclaimer */}
      <p className="text-center text-xs text-gray-400">
        Taxas macro atualizadas via BCB (6h) — valores indicativos. Ações: 12% a.a. fixo (proxy
        IBOV); FIIs: 8% a.a. fixo (DY médio, PF isento).
      </p>
    </div>
  );
}
