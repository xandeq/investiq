"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { startScreener } from "../api";
import { useScreenerJob, useScreenerHistory } from "../hooks/useScreenerJob";
import { PremiumGate } from "@/features/ai/components/PremiumGate";
import { StockAnalysis, ScreenerRun } from "../types";

const SECTORS = [
  "Financeiro",
  "Energia",
  "Tecnologia",
  "Consumo",
  "Saúde",
  "Utilidades",
  "Materiais",
  "Indústria",
  "Comunicação",
  "Imobiliário",
];

// ── Risk badge color ──────────────────────────────────────────────────────────
function riskColor(score: number | null): string {
  if (!score) return "bg-gray-100 text-gray-600";
  if (score <= 3) return "bg-emerald-100 text-emerald-700";
  if (score <= 6) return "bg-amber-100 text-amber-700";
  return "bg-red-100 text-red-700";
}

function moatColor(rating: string | null): string {
  if (!rating) return "text-gray-500";
  if (rating === "forte") return "text-emerald-600";
  if (rating === "moderado") return "text-amber-600";
  return "text-red-500";
}

// ── Stock Card ────────────────────────────────────────────────────────────────
function StockCard({ stock }: { stock: StockAnalysis }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg bg-gray-100 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full text-left px-5 py-4 flex items-start justify-between gap-4 hover:bg-gray-200 transition-colors duration-150"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-sm font-mono tracking-wider">{stock.ticker}</span>
            <span className="text-xs text-muted-foreground truncate">{stock.company_name}</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 shrink-0">{stock.sector}</span>
          </div>
          {stock.thesis && (
            <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{stock.thesis}</p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {stock.risk_score && (
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${riskColor(stock.risk_score)}`}>
              Risco {stock.risk_score}/10
            </span>
          )}
          <span className="text-gray-400 text-xs">{expanded ? "▲" : "▼"}</span>
        </div>
      </button>

      {/* Expanded body */}
      {expanded && (
        <div className="px-5 pb-5 space-y-4 border-t border-gray-200">
          {/* Metrics grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-4">
            {stock.pe_ratio !== null && (
              <MetricCell label="P/L" value={stock.pe_ratio.toFixed(1)} sub={stock.pe_vs_sector} />
            )}
            {stock.dividend_yield !== null && (
              <MetricCell label="Div. Yield" value={`${stock.dividend_yield.toFixed(1)}%`} sub={stock.payout_score} />
            )}
            {stock.debt_to_equity !== null && (
              <MetricCell label="D/E" value={stock.debt_to_equity.toFixed(2)} sub={stock.debt_health} />
            )}
            {stock.revenue_growth_5y && (
              <MetricCell label="Crescimento 5a" value={stock.revenue_growth_5y} />
            )}
            {stock.bull_target !== null && (
              <MetricCell
                label="Target Bull/Bear"
                value={`R$ ${stock.bull_target.toFixed(2)} / ${stock.bear_target?.toFixed(2) ?? "—"}`}
                sub={stock.current_price_ref ? `Preço ref: R$ ${stock.current_price_ref.toFixed(2)}` : undefined}
              />
            )}
            {stock.moat_rating && (
              <MetricCell
                label="Moat"
                value={stock.moat_rating.charAt(0).toUpperCase() + stock.moat_rating.slice(1)}
                valueClassName={moatColor(stock.moat_rating)}
                sub={stock.moat_description}
              />
            )}
          </div>

          {/* Entry zone & stop */}
          {(stock.entry_zone || stock.stop_loss) && (
            <div className="flex gap-4 flex-wrap">
              {stock.entry_zone && (
                <div className="flex-1 min-w-[140px] rounded-md bg-emerald-50 border-l-4 border-emerald-500 px-3 py-2">
                  <p className="text-xs font-bold text-emerald-700">Zona de entrada</p>
                  <p className="text-sm font-semibold mt-0.5">{stock.entry_zone}</p>
                </div>
              )}
              {stock.stop_loss && (
                <div className="flex-1 min-w-[140px] rounded-md bg-red-50 border-l-4 border-red-400 px-3 py-2">
                  <p className="text-xs font-bold text-red-600">Stop loss</p>
                  <p className="text-sm font-semibold mt-0.5">{stock.stop_loss}</p>
                </div>
              )}
            </div>
          )}

          {/* Risk reasoning */}
          {stock.risk_reasoning && (
            <div className="rounded-md bg-amber-50 border-l-4 border-amber-400 px-3 py-2">
              <p className="text-xs font-bold text-amber-700">Análise de risco</p>
              <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{stock.risk_reasoning}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MetricCell({
  label,
  value,
  sub,
  valueClassName,
}: {
  label: string;
  value: string;
  sub?: string | null;
  valueClassName?: string;
}) {
  return (
    <div className="rounded-md bg-white px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`text-sm font-bold mt-0.5 ${valueClassName ?? ""}`}>{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-0.5 leading-tight">{sub}</p>}
    </div>
  );
}

// ── Screener Result View ──────────────────────────────────────────────────────
function ScreenerResultView({ run }: { run: ScreenerRun }) {
  const result = run.result!;
  return (
    <div className="space-y-5">
      {/* Summary */}
      <div className="rounded-lg bg-gray-100 p-5">
        <h3 className="text-sm font-bold mb-2">Sumário executivo</h3>
        <p className="text-sm text-muted-foreground leading-relaxed">{result.summary}</p>
      </div>

      {/* Stocks */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
          {result.stocks.length} ações selecionadas
        </h3>
        {result.stocks.map((stock) => (
          <StockCard key={stock.ticker} stock={stock} />
        ))}
      </div>

      {/* Disclaimer */}
      <p className="text-xs text-muted-foreground border-t border-gray-100 pt-3">{result.disclaimer}</p>
      <p className="text-xs text-muted-foreground">
        Gerado em {new Date(result.generated_at).toLocaleString("pt-BR")}
      </p>
    </div>
  );
}

// ── History ───────────────────────────────────────────────────────────────────
function ScreenerHistory({ onSelect }: { onSelect: (runId: string) => void }) {
  const { data: runs, isLoading } = useScreenerHistory();

  if (isLoading || !runs || runs.length === 0) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Triagens anteriores</h3>
      {runs.map((run) => (
        <button
          key={run.id}
          onClick={() => run.status === "completed" && onSelect(run.id)}
          disabled={run.status !== "completed"}
          className="w-full text-left rounded-md bg-gray-100 px-4 py-3 text-sm hover:bg-gray-200 transition-all duration-200 disabled:opacity-50"
        >
          <div className="flex items-center justify-between">
            <span className="font-semibold">
              {run.sector_filter ? `Setor: ${run.sector_filter}` : "Todos os setores"}
            </span>
            <span
              className={
                run.status === "completed"
                  ? "text-emerald-600 text-xs font-medium"
                  : run.status === "failed"
                  ? "text-red-500 text-xs font-medium"
                  : "text-amber-600 text-xs font-medium"
              }
            >
              {run.status === "completed" ? "Concluída" : run.status === "failed" ? "Falhou" : "Em andamento"}
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            {new Date(run.created_at).toLocaleDateString("pt-BR", {
              day: "2-digit",
              month: "2-digit",
              year: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        </button>
      ))}
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────
function ScreenerMain() {
  const [runId, setRunId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sectorFilter, setSectorFilter] = useState<string>("");
  const [customNotes, setCustomNotes] = useState<string>("");
  const queryClient = useQueryClient();

  const { data: run } = useScreenerJob(runId);

  const isRunning =
    isSubmitting || (!!runId && (run?.status === "pending" || run?.status === "running"));

  const hasResult = run?.status === "completed" && !!run.result;

  async function handleSubmit() {
    setError(null);
    setIsSubmitting(true);
    setRunId(null);
    try {
      const created = await startScreener(
        sectorFilter || null,
        customNotes.trim() || null
      );
      setRunId(created.id);
      queryClient.invalidateQueries({ queryKey: ["screener", "history"] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao iniciar triagem");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-8">
      {/* CTA block */}
      <div className="rounded-lg bg-[#111827] text-white p-8 space-y-5">
        <div>
          <h2 className="text-lg font-bold tracking-tight">Triagem Goldman Sachs</h2>
          <p className="text-sm text-gray-400 mt-1">
            A IA seleciona as melhores ações da B3 com base em valuation, moat, dividendos e contexto macro —
            metodologia inspirada na Goldman Sachs.
          </p>
        </div>

        {/* Filters */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Filtrar por setor (opcional)</label>
            <select
              value={sectorFilter}
              onChange={(e) => setSectorFilter(e.target.value)}
              disabled={isRunning}
              className="w-full rounded-md bg-white/10 border border-white/20 text-white text-sm px-3 py-2 focus:outline-none focus:border-blue-400 disabled:opacity-50"
            >
              <option value="">Todos os setores</option>
              {SECTORS.map((s) => (
                <option key={s} value={s} className="text-black">
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Notas adicionais (opcional)</label>
            <input
              type="text"
              value={customNotes}
              onChange={(e) => setCustomNotes(e.target.value)}
              disabled={isRunning}
              placeholder="Ex: foco em dividendos acima de 6%"
              className="w-full rounded-md bg-white/10 border border-white/20 text-white placeholder:text-gray-500 text-sm px-3 py-2 focus:outline-none focus:border-blue-400 disabled:opacity-50"
            />
          </div>
        </div>

        <button
          onClick={handleSubmit}
          disabled={isRunning}
          className="px-6 py-3 rounded-md bg-blue-500 text-white hover:bg-blue-400 hover:scale-105 disabled:opacity-50 transition-all duration-200 font-semibold"
        >
          {isRunning ? (
            <span className="flex items-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
              Triagem em andamento...
            </span>
          ) : (
            "Iniciar triagem agora"
          )}
        </button>
        {error && <p className="text-sm text-red-400">{error}</p>}
      </div>

      {/* In-progress indicator */}
      {isRunning && !hasResult && (
        <div className="rounded-lg bg-gray-100 p-6 space-y-3">
          <div className="flex items-center gap-3">
            <span className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-blue-500" />
            <span className="text-sm font-semibold">Triagem em andamento...</span>
          </div>
          {[
            "Coletando dados de mercado da B3",
            "Calculando métricas de valuation",
            "Avaliando qualidade e moat",
            "Filtrando com critérios Goldman Sachs",
            "Estruturando relatório final",
          ].map((step) => (
            <div
              key={step}
              className="h-3 bg-gray-200 rounded animate-pulse"
              style={{ width: `${55 + Math.random() * 35}%` }}
            />
          ))}
        </div>
      )}

      {/* Result */}
      {hasResult && run && <ScreenerResultView run={run} />}

      {/* History */}
      {!isRunning && <ScreenerHistory onSelect={setRunId} />}
    </div>
  );
}

export function ScreenerContent() {
  return (
    <PremiumGate>
      <ScreenerMain />
    </PremiumGate>
  );
}
