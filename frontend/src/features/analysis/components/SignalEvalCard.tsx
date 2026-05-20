"use client";
import { useSignalEval } from "@/hooks/useSignalEval";

interface Props {
  ticker: string;
}

function GradeChip({ grade, isAPlus }: { grade: string; isAPlus: boolean }) {
  const base = "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold border";
  if (isAPlus)
    return (
      <span className={`${base} bg-emerald-50 text-emerald-700 border-emerald-300`}>
        A+ Setup
      </span>
    );
  if (grade === "B")
    return (
      <span className={`${base} bg-amber-50 text-amber-700 border-amber-300`}>
        Grau B
      </span>
    );
  return (
    <span className={`${base} bg-zinc-100 text-zinc-500 border-zinc-200`}>
      Sem setup
    </span>
  );
}

function GateBar({ passed, total }: { passed: number; total: number }) {
  const pct = total > 0 ? (passed / total) * 100 : 0;
  const color = pct >= 70 ? "bg-emerald-500" : pct >= 40 ? "bg-amber-400" : "bg-zinc-300";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-zinc-100 overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs tabular-nums text-zinc-400">
        {passed}/{total}
      </span>
    </div>
  );
}

export function SignalEvalCard({ ticker }: Props) {
  const { data, isLoading } = useSignalEval(ticker);

  if (isLoading) return null;
  if (!data) return null;

  const { is_a_plus, grade, passed_gates, total_gates, setup } = data;

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-zinc-800">Análise Técnica</span>
          <GradeChip grade={grade} isAPlus={is_a_plus} />
        </div>
        <span className="text-xs text-zinc-400">10 gates</span>
      </div>

      <GateBar passed={passed_gates} total={total_gates} />

      {is_a_plus && setup && (
        <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          <div>
            <span className="text-zinc-400">Padrão</span>{" "}
            <span className="font-medium text-zinc-800">{setup.pattern}</span>
          </div>
          <div>
            <span className="text-zinc-400">Direção</span>{" "}
            <span className="font-medium text-zinc-800 capitalize">{setup.direction}</span>
          </div>
          <div>
            <span className="text-zinc-400">Entrada</span>{" "}
            <span className="font-semibold text-zinc-900 tabular-nums">
              R$ {Number(setup.entry).toFixed(2)}
            </span>
          </div>
          <div>
            <span className="text-zinc-400">Stop</span>{" "}
            <span className="font-semibold text-red-600 tabular-nums">
              R$ {Number(setup.stop).toFixed(2)}
            </span>
          </div>
          <div>
            <span className="text-zinc-400">Alvo 1</span>{" "}
            <span className="font-semibold text-emerald-600 tabular-nums">
              R$ {Number(setup.target_1).toFixed(2)}
            </span>
          </div>
          <div>
            <span className="text-zinc-400">R/R</span>{" "}
            <span className="font-semibold text-zinc-800 tabular-nums">{Number(setup.rr).toFixed(1)}x</span>
          </div>
        </div>
      )}

      {!is_a_plus && (
        <p className="mt-2 text-xs text-zinc-400">
          {passed_gates === 0
            ? "Nenhum gate técnico atingido no momento."
            : `${passed_gates} de ${total_gates} condições técnicas satisfeitas.`}
        </p>
      )}
    </div>
  );
}
