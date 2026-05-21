"use client";
import { useSignalEval } from "@/hooks/useSignalEval";
import { useSentiment } from "@/hooks/useSentiment";

interface Props {
  ticker: string;
}

type Confidence = "alta" | "média" | "baixa";

function confidenceLevel(rr: number, sentimentScore: number): Confidence {
  if (sentimentScore > 0.5 && rr >= 3) return "alta";
  if (sentimentScore > 0.2 && rr >= 2) return "média";
  return "baixa";
}

function ConfidenceBadge({ level }: { level: Confidence }) {
  const map = {
    alta: "bg-emerald-100 text-emerald-700 border-emerald-300",
    média: "bg-amber-100 text-amber-700 border-amber-300",
    baixa: "bg-zinc-100 text-zinc-500 border-zinc-300",
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${map[level]}`}>
      Confiança {level}
    </span>
  );
}

function PriceRow({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-zinc-100 last:border-0">
      <span className="text-xs text-zinc-500">{label}</span>
      <span className={`text-sm font-semibold tabular-nums ${color ?? "text-zinc-900"}`}>
        {value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
      </span>
    </div>
  );
}

export function CopilotPickCard({ ticker }: Props) {
  const { data: signal, isLoading: signalLoading } = useSignalEval(ticker);
  const { data: sentiment, isLoading: sentimentLoading } = useSentiment(ticker);

  if (signalLoading || sentimentLoading) return null;
  if (!signal) return null;

  const sentimentScore = sentiment?.score ?? 0;
  const isAPlus = signal.is_a_plus;
  const setup = signal.setup;
  const hasPositiveSentiment = sentimentScore > 0.2;

  // Strong bullish: A+ setup AND positive sentiment alignment
  if (isAPlus && setup && hasPositiveSentiment) {
    const rr = Number(setup.rr);
    const entry = Number(setup.entry);
    const stop = Number(setup.stop);
    const target1 = Number(setup.target_1);
    const confidence = confidenceLevel(rr, sentimentScore);
    const entryLow = entry * 0.995;
    const entryHigh = entry * 1.005;

    return (
      <div className="rounded-xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-white p-4">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-zinc-800">Visão do Copilot</span>
            <span className="inline-flex items-center gap-1 rounded-full border border-emerald-300 bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
              Setup Favorável
            </span>
            <ConfidenceBadge level={confidence} />
          </div>
        </div>

        <p className="text-xs text-zinc-500 mb-3 leading-relaxed">
          Setup técnico A+ ({setup.pattern}) alinhado com sentimento{" "}
          <span className="font-medium text-emerald-700">positivo</span> nas redes sociais.
          Condições técnicas e de mercado convergem.
        </p>

        <div className="grid grid-cols-2 gap-x-4 mb-3">
          <div>
            <p className="text-[10px] uppercase tracking-wide text-zinc-400 mb-1">Zona de entrada</p>
            <p className="text-sm font-semibold tabular-nums text-zinc-900">
              {entryLow.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
              {" – "}
              {entryHigh.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
            </p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wide text-zinc-400 mb-1">Risco / Retorno</p>
            <p className="text-sm font-semibold tabular-nums text-zinc-900">{setup.rr.toFixed(1)}x</p>
          </div>
        </div>

        <div className="rounded-lg border border-zinc-100 bg-white/60 px-3 py-1">
          <PriceRow label="Stop" value={stop} color="text-red-600" />
          <PriceRow label="Alvo 1" value={target1} color="text-emerald-600" />
        </div>

        <p className="mt-3 text-[10px] text-zinc-400 leading-snug">
          Análise técnica automatizada. Não constitui recomendação de investimento.
          Gerencie sempre o risco com stop definido.
        </p>
      </div>
    );
  }

  // Technical setup confirmed but sentiment not aligned
  if (isAPlus && setup) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-4">
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          <span className="text-sm font-semibold text-zinc-800">Visão do Copilot</span>
          <span className="inline-flex items-center rounded-full border border-amber-300 bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-700">
            Setup parcial
          </span>
        </div>
        <p className="text-xs text-zinc-600 leading-relaxed">
          Setup técnico A+ confirmado ({setup.pattern}), mas o sentimento nas redes
          {sentimentScore < -0.1
            ? " está negativo — atenção à assimetria entre técnico e mercado."
            : " está neutro — aguardar confluência antes de entrar."}
        </p>
        <div className="mt-3 flex items-center justify-between text-xs text-zinc-500">
          <span>Stop: <span className="font-semibold tabular-nums text-red-600">
            {Number(setup.stop).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
          </span></span>
          <span>Alvo: <span className="font-semibold tabular-nums text-emerald-600">
            {Number(setup.target_1).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
          </span></span>
          <span>R/R: <span className="font-semibold">{Number(setup.rr).toFixed(1)}x</span></span>
        </div>
      </div>
    );
  }

  // No active setup
  return (
    <div className="rounded-xl border border-zinc-200 bg-zinc-50/50 p-4">
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-sm font-semibold text-zinc-700">Visão do Copilot</span>
        <span className="inline-flex items-center rounded-full border border-zinc-200 bg-white px-2.5 py-0.5 text-xs font-medium text-zinc-500">
          Sem setup
        </span>
      </div>
      <p className="text-xs text-zinc-400 leading-relaxed">
        {signal.passed_gates === 0
          ? "Nenhuma condição técnica satisfeita no momento. Aguardar formação de setup."
          : `${signal.passed_gates} de ${signal.total_gates} condições técnicas satisfeitas — setup ainda incompleto.`}
      </p>
    </div>
  );
}
