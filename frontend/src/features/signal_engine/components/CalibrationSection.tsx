"use client";

import { motion } from "framer-motion";
import { ChartBar, Warning } from "@phosphor-icons/react";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import { useCalibration } from "../hooks/useCalibration";
import type { PatternWeight, GradeStats } from "../hooks/useCalibration";

function statusBadge(status: PatternWeight["status"]) {
  if (status === "boosted")
    return (
      <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-medium">
        Boost ×1.2
      </span>
    );
  if (status === "disabled")
    return (
      <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-medium">
        Desabilitado
      </span>
    );
  return (
    <span className="text-xs bg-zinc-100 text-zinc-500 px-2 py-0.5 rounded-full">
      Padrão
    </span>
  );
}

function gradeColor(grade: string) {
  if (grade === "A+") return "text-emerald-700 bg-emerald-50 border-emerald-200";
  if (grade === "A") return "text-blue-700 bg-blue-50 border-blue-200";
  if (grade === "B") return "text-amber-700 bg-amber-50 border-amber-200";
  return "text-zinc-600 bg-zinc-50 border-zinc-200";
}

function winrateColor(wr: number) {
  if (wr >= 0.6) return "text-emerald-600";
  if (wr >= 0.45) return "text-amber-600";
  return "text-red-500";
}

function avgRColor(r: number) {
  if (r > 0.3) return "text-emerald-600";
  if (r > 0) return "text-amber-600";
  return "text-red-500";
}

export function CalibrationSection() {
  const { data, isLoading, error } = useCalibration();

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[0, 1, 2].map((i) => (
          <ShimmerSkeleton key={i} className="h-16 rounded-xl" />
        ))}
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-sm text-red-500 py-6 text-center">
        Erro ao carregar dados de calibração.
      </div>
    );
  }

  const patterns = Object.entries(data.pattern_weights);
  const grades = Object.entries(data.grade_performance);
  const minToAdjust = data.thresholds.min_to_adjust;

  return (
    <div className="space-y-6">
      {!data.data_sufficient && (
        <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-xl p-3 text-sm text-amber-800">
          <Warning size={16} className="shrink-0 mt-0.5" weight="fill" />
          <span>
            Calibração automática requer {minToAdjust} operações fechadas.
            Atualmente: <strong>{data.total_outcomes}</strong>. Registre mais trades para ativar.
          </span>
        </div>
      )}

      {grades.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-zinc-700 mb-3">
            Performance por Grade
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {grades.map(([grade, stats]: [string, GradeStats], i) => (
              <motion.div
                key={grade}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className={`rounded-xl border p-3 ${gradeColor(grade)}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-sm">{grade === "unknown" ? "Sem grade" : grade}</span>
                  <span className="text-xs opacity-70">{stats.n} operações</span>
                </div>
                <div className="flex gap-4 text-xs">
                  <div>
                    <span className="opacity-60">Winrate</span>
                    <p className={`font-bold ${winrateColor(stats.winrate)}`}>
                      {(stats.winrate * 100).toFixed(0)}%
                    </p>
                  </div>
                  <div>
                    <span className="opacity-60">Avg-R</span>
                    <p className={`font-bold ${avgRColor(stats.avg_r)}`}>
                      {stats.avg_r > 0 ? "+" : ""}{stats.avg_r.toFixed(2)}R
                    </p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </section>
      )}

      <section>
        <div className="flex items-center gap-2 mb-3">
          <ChartBar size={16} className="text-zinc-500" weight="fill" />
          <h3 className="text-sm font-semibold text-zinc-700">
            Pesos dos Padrões
          </h3>
        </div>
        <div className="bg-white border border-zinc-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-100 bg-zinc-50">
                <th className="text-left py-2 px-3 text-xs font-medium text-zinc-500">Padrão</th>
                <th className="text-center py-2 px-3 text-xs font-medium text-zinc-500">Status</th>
                <th className="text-right py-2 px-3 text-xs font-medium text-zinc-500">N</th>
                <th className="text-right py-2 px-3 text-xs font-medium text-zinc-500">Expectativa</th>
                <th className="text-right py-2 px-3 text-xs font-medium text-zinc-500">Winrate</th>
              </tr>
            </thead>
            <tbody>
              {patterns.map(([pattern, pw]: [string, PatternWeight], i) => (
                <tr
                  key={pattern}
                  className={`border-b border-zinc-50 last:border-0 ${
                    pw.status === "disabled" ? "opacity-50" : ""
                  }`}
                >
                  <td className="py-2 px-3 font-mono text-xs text-zinc-700">{pattern}</td>
                  <td className="py-2 px-3 text-center">{statusBadge(pw.status)}</td>
                  <td className="py-2 px-3 text-right tabular-nums text-zinc-400 text-xs">{pw.n}</td>
                  <td className={`py-2 px-3 text-right tabular-nums font-mono text-xs ${
                    pw.expectancy === null
                      ? "text-zinc-300"
                      : avgRColor(pw.expectancy)
                  }`}>
                    {pw.expectancy === null
                      ? "—"
                      : `${pw.expectancy > 0 ? "+" : ""}${pw.expectancy.toFixed(2)}R`}
                  </td>
                  <td className={`py-2 px-3 text-right tabular-nums text-xs ${
                    pw.win_rate === null
                      ? "text-zinc-300"
                      : winrateColor(pw.win_rate)
                  }`}>
                    {pw.win_rate === null
                      ? "—"
                      : `${(pw.win_rate * 100).toFixed(0)}%`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-zinc-400 mt-2">
          Boost ativa com expectativa &gt; 0.5R e N ≥ {minToAdjust}.
          Desabilitado com expectativa &lt; 0 e N ≥ {data.thresholds.min_to_disable}.
        </p>
      </section>
    </div>
  );
}
