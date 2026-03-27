"use client";
import { useState } from "react";
import { useWizard } from "../hooks/useWizard";
import type { PrazoLabel, PerfilLabel, WizardDeltaItem, WizardAllocation } from "../types";

const PRAZOS: PrazoLabel[] = ["6m", "1a", "2a", "5a"];
const PRAZO_LABELS: Record<PrazoLabel, string> = {
  "6m": "6 meses",
  "1a": "1 ano",
  "2a": "2 anos",
  "5a": "5 anos",
};

const PERFIS: { key: PerfilLabel; label: string; desc: string; color: string }[] = [
  { key: "conservador", label: "Conservador", desc: "Prioridade em preservação de capital", color: "emerald" },
  { key: "moderado",    label: "Moderado",    desc: "Equilíbrio entre segurança e crescimento", color: "blue" },
  { key: "arrojado",   label: "Arrojado",    desc: "Foco em crescimento com maior risco", color: "purple" },
];

const AC_COLORS: Record<string, string> = {
  acoes:      "bg-purple-500",
  fiis:       "bg-blue-500",
  renda_fixa: "bg-emerald-500",
  caixa:      "bg-gray-400",
};

const AC_LABELS: Record<string, string> = {
  acoes:      "Ações",
  fiis:       "FIIs",
  renda_fixa: "Renda Fixa",
  caixa:      "Caixa / DI",
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

function fmtBRL(val: number | null | undefined): string {
  if (val === null || val === undefined) return "—";
  return `R$ ${val.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function AllocationBar({ allocation }: { allocation: WizardAllocation }) {
  const slices = [
    { key: "acoes",      pct: allocation.acoes_pct },
    { key: "fiis",       pct: allocation.fiis_pct },
    { key: "renda_fixa", pct: allocation.renda_fixa_pct },
    { key: "caixa",      pct: allocation.caixa_pct },
  ];
  return (
    <div className="w-full">
      <div className="flex h-4 rounded-full overflow-hidden gap-px">
        {slices.map(({ key, pct }) =>
          pct > 0 ? (
            <div
              key={key}
              className={`${AC_COLORS[key]} transition-all`}
              style={{ width: `${pct}%` }}
              title={`${AC_LABELS[key]}: ${pct}%`}
            />
          ) : null
        )}
      </div>
      <div className="flex flex-wrap gap-3 mt-2">
        {slices.map(({ key, pct }) =>
          pct > 0 ? (
            <div key={key} className="flex items-center gap-1.5 text-xs text-gray-600">
              <span className={`inline-block w-2.5 h-2.5 rounded-sm ${AC_COLORS[key]}`} />
              <span>{AC_LABELS[key]}</span>
              <strong>{pct}%</strong>
            </div>
          ) : null
        )}
      </div>
    </div>
  );
}

function DeltaRow({ item }: { item: WizardDeltaItem }) {
  const actionClass = ACTION_COLORS[item.action] ?? "text-gray-500";
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
      <div className="flex items-center gap-2">
        <span className={`w-2.5 h-2.5 rounded-sm ${AC_COLORS[item.asset_class]}`} />
        <span className="text-sm font-medium text-gray-700">{item.label}</span>
      </div>
      <div className="flex items-center gap-4 text-sm">
        <span className="text-gray-400 w-16 text-right">{item.current_pct.toFixed(1)}% atual</span>
        <span className="text-gray-600 font-medium w-16 text-right">→ {item.suggested_pct.toFixed(1)}%</span>
        <span className={`font-semibold w-32 text-right ${actionClass}`}>
          {ACTION_LABELS[item.action]}
          {item.action !== "manter" && item.valor_delta !== 0 && (
            <span className="ml-1">{fmtBRL(Math.abs(item.valor_delta))}</span>
          )}
        </span>
      </div>
    </div>
  );
}

function StepIndicator({ current, total }: { current: number; total: number }) {
  const STEP_LABELS = ["Valor", "Prazo", "Perfil"];
  return (
    <div className="flex items-center gap-2 mb-6">
      {Array.from({ length: total }, (_, i) => i + 1).map((n) => (
        <div key={n} className="flex items-center">
          <div className="flex flex-col items-center">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-colors ${
              n < current ? "bg-blue-500 text-white" :
              n === current ? "bg-blue-500 text-white ring-4 ring-blue-100" :
              "bg-gray-200 text-gray-500"
            }`}>{n}</div>
            <span className="text-xs text-gray-500 mt-1">{STEP_LABELS[n - 1]}</span>
          </div>
          {n < total && (
            <div className={`h-0.5 w-8 mx-1 mb-5 ${n < current ? "bg-blue-500" : "bg-gray-200"}`} />
          )}
        </div>
      ))}
    </div>
  );
}

export function WizardContent() {
  const [valorInput, setValorInput] = useState("10000");
  const [prazo, setPrazo] = useState<PrazoLabel>("1a");
  const [perfil, setPerfil] = useState<PerfilLabel>("moderado");
  const [step, setStep] = useState<1 | 2 | 3>(1);

  const { submit, job, status, isStarting, error, reset } = useWizard();

  const isIdle = !status;
  const isProcessing = status === "pending" || status === "running" || isStarting;
  const isDone = status === "completed";
  const isFailed = status === "failed";

  function handleSubmit() {
    const v = parseFloat(valorInput);
    if (!v || v < 100) return;
    submit(perfil, prazo, v);
  }

  return (
    <div className="space-y-6">
      {/* Disclaimer CVM — always visible, MUST be first child */}
      <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
        <strong>Análise informativa</strong> — não constitui recomendação de investimento (CVM Res. 19/2021).
        Resultados dependem de condições de mercado e podem variar.
      </div>

      {/* Multi-step Form */}
      {(isIdle || isFailed) && (
        <>
          <StepIndicator current={step} total={3} />
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-5">

            {/* Step 1: Valor disponivel */}
            {step === 1 && (
              <div>
                <h2 className="text-sm font-bold text-gray-800 mb-3">Quanto voce quer investir?</h2>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5">
                  Valor disponivel para investir (R$)
                </label>
                <input
                  type="number"
                  min={100}
                  value={valorInput}
                  onChange={(e) => setValorInput(e.target.value)}
                  placeholder="Ex: 10000"
                  className="w-44 rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
                />
                <p className="text-xs text-gray-400 mt-1">Minimo: R$ 100</p>
                <div className="flex justify-end mt-4">
                  <button
                    onClick={() => setStep(2)}
                    disabled={!valorInput || parseFloat(valorInput) < 100}
                    className="px-6 py-2.5 rounded-lg bg-blue-500 text-white text-sm font-semibold hover:bg-blue-600 disabled:opacity-50 transition-colors"
                  >
                    Proximo
                  </button>
                </div>
              </div>
            )}

            {/* Step 2: Prazo (horizonte) */}
            {step === 2 && (
              <div>
                <h2 className="text-sm font-bold text-gray-800 mb-3">Qual o prazo do investimento?</h2>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5">Horizonte de investimento</label>
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
                <div className="flex justify-between mt-4">
                  <button
                    onClick={() => setStep(1)}
                    className="px-6 py-2.5 rounded-lg border border-gray-200 text-gray-600 text-sm font-semibold hover:bg-gray-50 transition-colors"
                  >
                    Voltar
                  </button>
                  <button
                    onClick={() => setStep(3)}
                    className="px-6 py-2.5 rounded-lg bg-blue-500 text-white text-sm font-semibold hover:bg-blue-600 transition-colors"
                  >
                    Proximo
                  </button>
                </div>
              </div>
            )}

            {/* Step 3: Perfil de risco + submit */}
            {step === 3 && (
              <div>
                <h2 className="text-sm font-bold text-gray-800 mb-3">Qual o seu perfil de risco?</h2>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5">Perfil de risco</label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {PERFIS.map((p) => {
                    const isSelected = perfil === p.key;
                    const borderMap: Record<string, string> = {
                      emerald: isSelected ? "border-emerald-500 bg-emerald-50" : "border-gray-200 hover:border-emerald-300",
                      blue:    isSelected ? "border-blue-500 bg-blue-50"       : "border-gray-200 hover:border-blue-300",
                      purple:  isSelected ? "border-purple-500 bg-purple-50"   : "border-gray-200 hover:border-purple-300",
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
                <div className="flex justify-between mt-4">
                  <button
                    onClick={() => setStep(2)}
                    className="px-6 py-2.5 rounded-lg border border-gray-200 text-gray-600 text-sm font-semibold hover:bg-gray-50 transition-colors"
                  >
                    Voltar
                  </button>
                  <button
                    onClick={handleSubmit}
                    disabled={!valorInput || parseFloat(valorInput) < 100}
                    className="px-6 py-2.5 rounded-lg bg-blue-500 text-white text-sm font-semibold hover:bg-blue-600 disabled:opacity-50 transition-colors"
                  >
                    Analisar onde investir
                  </button>
                </div>

                {isFailed && (
                  <p className="text-sm text-red-600 mt-3">
                    {job?.error_message ?? error ?? "Erro ao processar recomendacao. Tente novamente."}
                  </p>
                )}
              </div>
            )}
          </div>
        </>
      )}

      {/* Error (hook-level) */}
      {error && isIdle && (
        <div className="rounded-lg bg-red-50 border border-red-100 px-4 py-3 text-sm text-red-600">{error}</div>
      )}

      {/* Loading */}
      {isProcessing && (
        <div className="rounded-xl border border-gray-200 bg-white p-8 flex flex-col items-center gap-4 text-center">
          <div className="h-10 w-10 rounded-full border-4 border-blue-500 border-t-transparent animate-spin" />
          <div>
            <p className="text-sm font-semibold text-gray-700">Analisando seu perfil…</p>
            <p className="text-xs text-gray-400 mt-1">
              A IA está consultando dados de mercado e gerando sua recomendação
            </p>
          </div>
          <div className="flex gap-3 mt-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
              Perfil: <strong className="capitalize">{perfil}</strong>
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600">
              Prazo: <strong>{PRAZO_LABELS[prazo]}</strong>
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600">
              {fmtBRL(parseFloat(valorInput))}
            </span>
          </div>
        </div>
      )}

      {/* Results */}
      {isDone && job?.result && (
        <>
          {/* Full disclaimer from API */}
          {job.disclaimer && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800 leading-relaxed">
              {job.disclaimer}
            </div>
          )}

          {/* Macro context */}
          {job.result.macro && Object.keys(job.result.macro).length > 0 && (
            <div className="flex flex-wrap gap-2">
              {Object.entries(job.result.macro).map(([k, v]) => (
                <span
                  key={k}
                  className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700"
                >
                  <span className="uppercase font-semibold text-gray-500">{k}</span>
                  <span>{v}</span>
                </span>
              ))}
            </div>
          )}

          {/* Allocation breakdown */}
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-gray-800">
                Alocação sugerida —{" "}
                <span className="capitalize text-blue-600">{job.perfil}</span>
                {" · "}
                <span className="text-gray-500">{PRAZO_LABELS[job.prazo as PrazoLabel] ?? job.prazo}</span>
              </h2>
              <span className="text-xs text-gray-400">{fmtBRL(job.valor)}</span>
            </div>

            <AllocationBar allocation={job.result.allocation} />

            <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
              {(
                [
                  { key: "acoes",      pct: job.result.allocation.acoes_pct },
                  { key: "fiis",       pct: job.result.allocation.fiis_pct },
                  { key: "renda_fixa", pct: job.result.allocation.renda_fixa_pct },
                  { key: "caixa",      pct: job.result.allocation.caixa_pct },
                ] as const
              ).map(({ key, pct }) => (
                <div key={key} className="bg-gray-50 rounded-lg p-3">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className={`w-2.5 h-2.5 rounded-sm ${AC_COLORS[key]}`} />
                    <span className="text-xs text-gray-500">{AC_LABELS[key]}</span>
                  </div>
                  <p className="text-lg font-bold text-gray-800">{pct}%</p>
                  <p className="text-xs text-gray-400">{fmtBRL((job.valor * pct) / 100)}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Rationale */}
          {job.result.allocation.rationale && (
            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <h2 className="text-sm font-bold text-gray-800 mb-2">Justificativa</h2>
              <p className="text-sm text-gray-600 leading-relaxed">{job.result.allocation.rationale}</p>
            </div>
          )}

          {/* Portfolio delta */}
          {job.result.delta && job.result.delta.length > 0 && (
            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <h2 className="text-sm font-bold text-gray-800 mb-1">
                Delta: sua carteira vs alocação sugerida
              </h2>
              <p className="text-xs text-gray-400 mb-4">
                Ajustes necessários para atingir a alocação ideal
              </p>
              <div className="space-y-1">
                {job.result.delta.map((item) => (
                  <DeltaRow key={item.asset_class} item={item} />
                ))}
              </div>
              <p className="text-xs text-gray-400 mt-3">
                Consulte um assessor de investimentos antes de rebalancear sua carteira.
              </p>
            </div>
          )}

          {/* Reset */}
          <button
            onClick={() => { reset(); setStep(1); }}
            className="text-sm text-blue-500 hover:text-blue-700 underline underline-offset-2"
          >
            Nova análise
          </button>
        </>
      )}
    </div>
  );
}
