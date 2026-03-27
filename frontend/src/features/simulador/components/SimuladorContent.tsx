"use client";
import { useState } from "react";
import { useSimulador } from "../hooks/useSimulador";
import type { Cenario, PrazoLabel, PerfilLabel, RebalancingItem } from "../types";

const PRAZOS: PrazoLabel[] = ["6m", "1a", "2a", "5a"];
const PRAZO_LABELS: Record<PrazoLabel, string> = {
  "6m": "6 meses",
  "1a": "1 ano",
  "2a": "2 anos",
  "5a": "5 anos",
};

const PERFIS: { key: PerfilLabel; label: string; desc: string; color: string }[] = [
  {
    key: "conservador",
    label: "Conservador",
    desc: "80% Renda Fixa · 10% Caixa · 10% RV",
    color: "emerald",
  },
  {
    key: "moderado",
    label: "Moderado",
    desc: "55% Renda Fixa · 35% RV · 10% Caixa",
    color: "blue",
  },
  {
    key: "arrojado",
    label: "Arrojado",
    desc: "70% Renda Variável · 25% RF · 5% Caixa",
    color: "purple",
  },
];

const CENARIO_COLORS: Record<string, { ring: string; badge: string; value: string }> = {
  pessimista: {
    ring: "border-red-300",
    badge: "bg-red-100 text-red-700",
    value: "text-red-600",
  },
  base: {
    ring: "border-blue-300",
    badge: "bg-blue-100 text-blue-700",
    value: "text-blue-700",
  },
  otimista: {
    ring: "border-emerald-300",
    badge: "bg-emerald-100 text-emerald-700",
    value: "text-emerald-700",
  },
};

const AC_COLORS: Record<string, string> = {
  acoes:     "bg-purple-500",
  fiis:      "bg-blue-500",
  renda_fixa: "bg-emerald-500",
  caixa:     "bg-gray-400",
};

const ACTION_COLORS: Record<string, string> = {
  adicionar: "text-emerald-600",
  reduzir:   "text-red-500",
  manter:    "text-gray-500",
};

const ACTION_LABELS: Record<string, string> = {
  adicionar: "▲ Adicionar",
  reduzir:   "▼ Reduzir",
  manter:    "● Manter",
};

function fmt(val: string | number | null, dec = 2): string {
  if (val === null || val === undefined) return "—";
  const n = typeof val === "string" ? parseFloat(val) : val;
  return isNaN(n) ? "—" : n.toFixed(dec);
}

function fmtBRL(val: string | null): string {
  if (!val) return "—";
  const n = parseFloat(val);
  if (isNaN(n)) return "—";
  return `R$ ${n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function AllocationBar({ allocation }: { allocation: Record<string, { pct: string }> }) {
  const classes = ["acoes", "fiis", "renda_fixa", "caixa"];
  return (
    <div className="w-full">
      <div className="flex h-4 rounded-full overflow-hidden gap-px">
        {classes.map((ac) => {
          const pct = parseFloat(allocation[ac]?.pct ?? "0");
          if (pct <= 0) return null;
          return (
            <div
              key={ac}
              className={`${AC_COLORS[ac]} transition-all`}
              style={{ width: `${pct}%` }}
              title={`${ac}: ${pct}%`}
            />
          );
        })}
      </div>
      <div className="flex flex-wrap gap-3 mt-2">
        {classes.map((ac) => {
          const pct = parseFloat(allocation[ac]?.pct ?? "0");
          if (pct <= 0) return null;
          return (
            <div key={ac} className="flex items-center gap-1.5 text-xs text-gray-600">
              <span className={`inline-block w-2.5 h-2.5 rounded-sm ${AC_COLORS[ac]}`} />
              <span className="capitalize">{ac === "renda_fixa" ? "Renda Fixa" : ac === "acoes" ? "Ações" : ac === "fiis" ? "FIIs" : "Caixa"}</span>
              <strong>{pct}%</strong>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function CenarioCard({ cenario, valor }: { cenario: Cenario; valor: number }) {
  const colors = CENARIO_COLORS[cenario.key];
  const retornoPct = parseFloat(cenario.retorno_liquido_pct);
  const isNeg = retornoPct < 0;

  return (
    <div className={`rounded-xl border-2 ${colors.ring} bg-white p-5`}>
      <div className="flex items-center justify-between mb-4">
        <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${colors.badge}`}>
          {cenario.nome}
        </span>
        <div className="text-right">
          <p className="text-xs text-gray-400">Retorno líquido</p>
          <p className={`text-xl font-bold ${isNeg ? "text-red-500" : colors.value}`}>
            {isNeg ? "" : "+"}{fmt(cenario.retorno_liquido_pct)}%
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between mb-4 p-3 bg-gray-50 rounded-lg">
        <div>
          <p className="text-xs text-gray-500">Valor final</p>
          <p className="text-base font-bold text-gray-800">{fmtBRL(cenario.total_liquido)}</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-500">Ganho líquido</p>
          <p className={`text-sm font-semibold ${isNeg ? "text-red-500" : "text-emerald-600"}`}>
            {isNeg ? "-" : "+"}{fmtBRL(String(parseFloat(cenario.total_liquido) - valor))}
          </p>
        </div>
      </div>

      <div className="space-y-2">
        {cenario.classes
          .filter((c) => parseFloat(c.pct_alocado) > 0)
          .map((cl) => {
            const liq = parseFloat(cl.retorno_liquido_pct);
            return (
              <div key={cl.asset_class} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5">
                  <span className={`w-2 h-2 rounded-sm ${AC_COLORS[cl.asset_class]}`} />
                  <span className="text-gray-600">{cl.label}</span>
                  {cl.is_exempt && (
                    <span className="text-green-600 text-[10px]">(isento)</span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-gray-400">{cl.pct_alocado}%</span>
                  <span className={`font-medium ${liq < 0 ? "text-red-500" : "text-gray-700"}`}>
                    {liq >= 0 ? "+" : ""}{fmt(cl.retorno_liquido_pct)}%
                  </span>
                  <span className="text-gray-500 w-20 text-right">{fmtBRL(cl.valor_final)}</span>
                </div>
              </div>
            );
          })}
      </div>
    </div>
  );
}

function RebalancingRow({ item }: { item: RebalancingItem }) {
  const actionClass = ACTION_COLORS[item.action] ?? "text-gray-500";
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
      <div className="flex items-center gap-2">
        <span className={`w-2.5 h-2.5 rounded-sm ${AC_COLORS[item.asset_class]}`} />
        <span className="text-sm font-medium text-gray-700">{item.label}</span>
      </div>
      <div className="flex items-center gap-4 text-sm">
        <span className="text-gray-400 w-14 text-right">{fmt(item.current_pct)}% atual</span>
        <span className="text-gray-600 font-medium w-14 text-right">→ {fmt(item.ideal_pct)}% ideal</span>
        <span className={`font-semibold w-28 text-right ${actionClass}`}>
          {ACTION_LABELS[item.action]}{" "}
          {item.action !== "manter" && (
            <span>{fmtBRL(item.valor_delta)}</span>
          )}
        </span>
      </div>
    </div>
  );
}

export function SimuladorContent() {
  const [valorInput, setValorInput] = useState("10000");
  const [prazo, setPrazo] = useState<PrazoLabel>("1a");
  const [perfil, setPerfil] = useState<PerfilLabel>("moderado");

  const { data, isLoading, error, setParams } = useSimulador();

  function handleSimulate() {
    const v = parseFloat(valorInput);
    if (!v || v <= 0) return;
    setParams({ valor: v, prazo, perfil });
  }

  const baseScenario = data?.cenarios.find((c) => c.key === "base");

  return (
    <div className="space-y-6">
      {/* Disclaimer */}
      <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
        <strong>Análise informativa</strong> — não constitui recomendação de investimento (CVM Res. 19/2021).
        Retornos projetados não garantem resultados futuros.
      </div>

      {/* Controls */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-5">
        {/* Valor */}
        <div>
          <label className="block text-xs font-semibold text-gray-600 mb-1.5">
            Valor disponível para investir (R$)
          </label>
          <div className="flex gap-2">
            <input
              type="number"
              min={100}
              value={valorInput}
              onChange={(e) => setValorInput(e.target.value)}
              placeholder="Ex: 10000"
              className="w-44 rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            />
          </div>
        </div>

        {/* Prazo */}
        <div>
          <label className="block text-xs font-semibold text-gray-600 mb-1.5">Prazo</label>
          <div className="flex rounded-lg border border-gray-200 overflow-hidden w-fit">
            {PRAZOS.map((p) => (
              <button
                key={p}
                onClick={() => setPrazo(p)}
                className={`px-5 py-2 text-sm font-medium transition-colors ${
                  prazo === p
                    ? "bg-blue-500 text-white"
                    : "bg-white text-gray-600 hover:bg-gray-50"
                }`}
              >
                {PRAZO_LABELS[p]}
              </button>
            ))}
          </div>
        </div>

        {/* Perfil */}
        <div>
          <label className="block text-xs font-semibold text-gray-600 mb-1.5">Perfil de risco</label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {PERFIS.map((p) => {
              const isSelected = perfil === p.key;
              const borderMap: Record<string, string> = {
                emerald: isSelected ? "border-emerald-500 bg-emerald-50" : "border-gray-200 hover:border-emerald-300",
                blue:    isSelected ? "border-blue-500 bg-blue-50"    : "border-gray-200 hover:border-blue-300",
                purple:  isSelected ? "border-purple-500 bg-purple-50" : "border-gray-200 hover:border-purple-300",
              };
              const textMap: Record<string, string> = {
                emerald: isSelected ? "text-emerald-700" : "text-gray-700",
                blue:    isSelected ? "text-blue-700"    : "text-gray-700",
                purple:  isSelected ? "text-purple-700"  : "text-gray-700",
              };
              return (
                <button
                  key={p.key}
                  onClick={() => setPerfil(p.key)}
                  className={`border-2 rounded-xl p-4 text-left transition-all ${borderMap[p.color]}`}
                >
                  <p className={`text-sm font-bold ${textMap[p.color]}`}>{p.label}</p>
                  <p className="text-xs text-gray-500 mt-1">{p.desc}</p>
                </button>
              );
            })}
          </div>
        </div>

        {/* Submit */}
        <button
          onClick={handleSimulate}
          disabled={isLoading || !valorInput || parseFloat(valorInput) <= 0}
          className="px-6 py-2.5 rounded-lg bg-blue-500 text-white text-sm font-semibold hover:bg-blue-600 disabled:opacity-50 transition-colors"
        >
          {isLoading ? "Calculando…" : "Simular Alocação"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-100 px-4 py-3 text-sm text-red-600">
          {error instanceof Error ? error.message : "Erro ao calcular simulação"}
        </div>
      )}

      {/* Loading skeleton */}
      {isLoading && (
        <div className="space-y-4">
          <div className="h-20 rounded-xl bg-gray-100 animate-pulse" />
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-56 rounded-xl bg-gray-100 animate-pulse" />
            ))}
          </div>
        </div>
      )}

      {/* Results */}
      {!isLoading && data && (
        <>
          {/* SIM-01: Allocation breakdown */}
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-gray-800">
                Alocação sugerida —{" "}
                <span className="text-blue-600 capitalize">{data.perfil}</span>
                {" · "}
                <span className="text-gray-500">{PRAZO_LABELS[data.prazo as PrazoLabel]}</span>
              </h2>
              {data.cdi_annual_pct && (
                <span className="text-xs text-gray-400">
                  CDI: <strong>{parseFloat(data.cdi_annual_pct).toFixed(2)}% a.a.</strong>
                </span>
              )}
            </div>
            <AllocationBar
              allocation={{
                acoes:     { pct: data.allocation.acoes.pct },
                fiis:      { pct: data.allocation.fiis.pct },
                renda_fixa:{ pct: data.allocation.renda_fixa.pct },
                caixa:     { pct: data.allocation.caixa.pct },
              }}
            />
            <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
              {(
                [
                  { key: "acoes",     label: "Ações" },
                  { key: "fiis",      label: "FIIs" },
                  { key: "renda_fixa",label: "Renda Fixa" },
                  { key: "caixa",     label: "Caixa / DI" },
                ] as const
              ).map(({ key, label }) => {
                const ac = data.allocation[key];
                return (
                  <div key={key} className="bg-gray-50 rounded-lg p-3">
                    <div className="flex items-center gap-1.5 mb-1">
                      <span className={`w-2.5 h-2.5 rounded-sm ${AC_COLORS[key]}`} />
                      <span className="text-xs text-gray-500">{label}</span>
                    </div>
                    <p className="text-lg font-bold text-gray-800">{ac.pct}%</p>
                    <p className="text-xs text-gray-400">{fmtBRL(ac.valor)}</p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* SIM-02: 3 scenarios */}
          <section>
            <h2 className="text-sm font-bold uppercase tracking-wider text-gray-500 mb-3">
              Projeções por cenário (líquido de IR)
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {data.cenarios.map((c) => (
                <CenarioCard key={c.key} cenario={c} valor={parseFloat(data.valor_inicial)} />
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-2">
              Ações: IR 15% sobre ganhos · FIIs: Isento para PF ·
              Renda Fixa / Caixa: IR regressivo (22,5% → 15%)
            </p>
          </section>

          {/* SIM-03: Portfolio delta */}
          {data.portfolio_delta && (
            <section className="rounded-xl border border-gray-200 bg-white p-5">
              <h2 className="text-sm font-bold text-gray-800 mb-1">
                Delta: sua carteira atual vs alocação ideal
              </h2>
              <p className="text-xs text-gray-400 mb-4">
                Carteira atual: <strong>{fmtBRL(data.portfolio_delta.total_portfolio)}</strong> investidos
              </p>
              <div className="space-y-1">
                {data.portfolio_delta.rebalancing.map((item) => (
                  <RebalancingRow key={item.asset_class} item={item} />
                ))}
              </div>
              <p className="text-xs text-gray-400 mt-3">
                Valores baseados no custo de aquisição das posições abertas. Consulte um assessor antes de rebalancear.
              </p>
            </section>
          )}
        </>
      )}
    </div>
  );
}
