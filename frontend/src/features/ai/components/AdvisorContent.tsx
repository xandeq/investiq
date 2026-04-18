"use client";
import { useState, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { startAdvisorAnalysis } from "@/features/advisor/api";
import { usePortfolioHealth } from "@/features/advisor/hooks/usePortfolioHealth";
import { useAdvisorJob } from "@/features/advisor/hooks/useAdvisorJob";
import { useSmartScreener } from "@/features/advisor/hooks/useSmartScreener";
import { PremiumGate } from "./PremiumGate";
import type { PortfolioHealth, AdvisorAnalysisResult, ComplementaryAsset } from "@/features/advisor/types";

// ── Health Score helpers ────────────────────────────────────────────────────

function scoreColor(score: number): string {
  if (score >= 80) return "text-emerald-600";
  if (score >= 60) return "text-amber-500";
  return "text-red-500";
}

function scoreLabel(score: number): string {
  if (score >= 80) return "Equilibrado";
  if (score >= 60) return "Atenção";
  return "Revisar";
}

function fmtBRL(value: string | null): string {
  if (!value) return "R$ 0,00";
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
    parseFloat(value)
  );
}

// ── Portfolio Health Section (Phase 23 — ADVI-01) ─────────────────────────

function HealthSection({
  health,
  isLoading,
  onRefresh,
}: {
  health: PortfolioHealth | undefined;
  isLoading: boolean;
  onRefresh: () => void;
}) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 animate-pulse">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-lg bg-gray-100 h-20" />
        ))}
      </div>
    );
  }

  if (!health) return null;

  if (!health.has_portfolio) {
    return (
      <div className="rounded-lg bg-gray-50 border border-gray-200 p-5 text-center">
        <p className="text-sm text-muted-foreground">
          Nenhuma transação encontrada. Importe sua carteira para ver o diagnóstico de saúde.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold uppercase tracking-wide text-muted-foreground">
          Saúde da Carteira
        </h2>
        <div className="flex items-center gap-3">
          {health.data_as_of && (
            <span className="text-[11px] text-muted-foreground">
              Dados de {new Date(health.data_as_of).toLocaleDateString("pt-BR")}
            </span>
          )}
          <button
            onClick={onRefresh}
            className="text-[11px] text-blue-500 hover:text-blue-400 transition-colors"
          >
            Atualizar
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {/* Score */}
        <div className="rounded-lg border border-gray-200 bg-white p-4 text-center">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground mb-1">Score</p>
          <p className={`text-3xl font-bold ${scoreColor(health.health_score)}`}>
            {health.health_score}
          </p>
          <p className={`text-[11px] font-medium mt-1 ${scoreColor(health.health_score)}`}>
            {scoreLabel(health.health_score)}
          </p>
        </div>

        {/* Risk */}
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground mb-1">
            Principal Risco
          </p>
          <p className="text-sm font-medium text-foreground leading-snug">
            {health.biggest_risk ?? "Nenhum identificado"}
          </p>
        </div>

        {/* Passive income */}
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground mb-1">
            Renda Mensal
          </p>
          <p className="text-xl font-bold text-emerald-600">
            {fmtBRL(health.passive_income_monthly_brl)}
          </p>
          <p className="text-[11px] text-muted-foreground mt-1">últ. 12 meses ÷ 12</p>
        </div>

        {/* Underperformers */}
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground mb-1">
            Queda &gt; 10% no ano
          </p>
          {health.underperformers.length === 0 ? (
            <p className="text-sm text-emerald-600 font-medium">Nenhum</p>
          ) : (
            <ul className="space-y-0.5">
              {health.underperformers.map((u) => (
                <li key={u} className="text-xs text-red-500 font-mono">
                  {u}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {health.biggest_risk && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
          <span className="font-semibold">Alerta: </span>
          {health.biggest_risk}
        </div>
      )}
    </div>
  );
}

// ── AI Diagnosis Section (Phase 24 — ADVI-02) ─────────────────────────────

function BulletCard({
  title,
  items,
  colorClass,
}: {
  title: string;
  items: string[];
  colorClass: string;
}) {
  if (!items || items.length === 0) return null;
  return (
    <div className={`rounded-lg p-5 ${colorClass}`}>
      <h3 className="text-sm font-bold mb-3">{title}</h3>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="text-sm flex gap-2">
            <span className="mt-0.5 shrink-0">•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function AIDiagnosisSection({ result }: { result: AdvisorAnalysisResult }) {
  return (
    <div className="space-y-4">
      <h2 className="text-sm font-bold uppercase tracking-wide text-muted-foreground">
        Diagnóstico IA
      </h2>

      {/* Main narrative */}
      <div className="rounded-lg bg-gray-50 border border-gray-200 p-5">
        <p className="text-sm text-foreground leading-relaxed">{result.diagnostico}</p>
      </div>

      {/* Positives + Concerns grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <BulletCard
          title="Pontos Positivos"
          items={result.pontos_positivos}
          colorClass="bg-emerald-50 border-l-4 border-emerald-500"
        />
        <BulletCard
          title="Pontos de Atenção"
          items={result.pontos_de_atencao}
          colorClass="bg-amber-50 border-l-4 border-amber-500"
        />
      </div>

      {/* Suggestions */}
      <BulletCard
        title="Sugestões"
        items={result.sugestoes}
        colorClass="bg-blue-50 border-l-4 border-blue-500"
      />

      {/* Next steps */}
      <BulletCard
        title="Próximos Passos"
        items={result.proximos_passos}
        colorClass="bg-gray-100 border-l-4 border-gray-400"
      />

      {result.disclaimer && (
        <p className="text-xs text-muted-foreground border-t border-gray-100 pt-3">
          {result.disclaimer}
        </p>
      )}
    </div>
  );
}

// ── Smart Screener Section (Phase 25 — ADVI-03) ───────────────────────────

function SmartScreenerSection({
  assets,
  isLoading,
}: {
  assets: ComplementaryAsset[];
  isLoading: boolean;
}) {
  const [filterSector, setFilterSector] = useState<string>("");

  const sectors = useMemo(
    () => Array.from(new Set(assets.map((a) => a.sector).filter(Boolean))) as string[],
    [assets]
  );

  const filtered = useMemo(
    () => assets.filter((a) => !filterSector || a.sector === filterSector),
    [assets, filterSector]
  );

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 p-6 space-y-3 animate-pulse">
        <div className="h-5 bg-gray-100 rounded w-48" />
        <div className="h-32 bg-gray-100 rounded" />
      </div>
    );
  }

  if (!assets.length) {
    return (
      <div className="rounded-lg border border-gray-200 p-5 text-center">
        <p className="text-sm text-muted-foreground">
          Nenhum ativo complementar encontrado. Importe sua carteira para ver sugestões
          personalizadas.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold uppercase tracking-wide text-muted-foreground">
          Smart Screener
        </h2>
        <p className="text-[11px] text-muted-foreground">
          Ativos de setores não presentes na sua carteira
        </p>
      </div>

      {/* Sector filter */}
      <div className="flex items-center gap-2">
        <select
          value={filterSector}
          onChange={(e) => setFilterSector(e.target.value)}
          className="text-sm px-3 py-1.5 border border-gray-200 rounded-md bg-white text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Todos os setores ({filtered.length})</option>
          {sectors.map((s) => (
            <option key={s} value={s}>
              {s} ({assets.filter((a) => a.sector === s).length})
            </option>
          ))}
        </select>
      </div>

      {/* Results table */}
      <div className="rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                Ticker
              </th>
              <th className="text-left px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                Setor
              </th>
              <th className="text-right px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                DY 12m
              </th>
              <th className="text-right px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                Var. 12m
              </th>
              <th className="text-right px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                Preço
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filtered.slice(0, 50).map((a) => {
              const dyPct = a.dy_12m_pct != null ? (a.dy_12m_pct * 100).toFixed(2) : null;
              const varPct =
                a.variacao_12m_pct != null ? (a.variacao_12m_pct * 100).toFixed(2) : null;
              const isPositive = (a.variacao_12m_pct ?? 0) >= 0;

              return (
                <tr key={a.ticker} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-2.5">
                    <a
                      href={`/stock/${a.ticker}`}
                      className="font-mono text-blue-600 hover:text-blue-500 hover:underline font-semibold"
                    >
                      {a.ticker}
                    </a>
                  </td>
                  <td className="px-4 py-2.5 text-xs text-muted-foreground">
                    {a.sector ?? "—"}
                  </td>
                  <td className="text-right px-4 py-2.5 text-xs font-medium text-emerald-600">
                    {dyPct != null ? `${dyPct}%` : "—"}
                  </td>
                  <td
                    className={`text-right px-4 py-2.5 text-xs font-medium ${
                      isPositive ? "text-emerald-600" : "text-red-500"
                    }`}
                  >
                    {varPct != null ? `${isPositive ? "+" : ""}${varPct}%` : "—"}
                  </td>
                  <td className="text-right px-4 py-2.5 text-xs">
                    {a.preco_atual != null
                      ? `R$ ${a.preco_atual.toFixed(2)}`
                      : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {filtered.length > 50 && (
          <div className="px-4 py-2.5 bg-gray-50 border-t border-gray-200 text-center">
            <p className="text-[11px] text-muted-foreground">
              Mostrando 50 de {filtered.length} resultados
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// ── In-Progress Indicator ─────────────────────────────────────────────────

function AnalysisInProgress() {
  return (
    <div className="rounded-lg bg-gray-100 p-6 space-y-3">
      <div className="flex items-center gap-3">
        <span className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-blue-500" />
        <span className="text-sm font-semibold">Análise em andamento...</span>
      </div>
      <p className="text-xs text-muted-foreground">
        Isso leva ~1-2 minutos. Você pode navegar para outras páginas — o resultado aparecerá aqui
        quando você voltar.
      </p>
      {["Carregando posições e P&L", "Buscando contexto macro", "Processando com IA", "Estruturando diagnóstico"].map(
        (step) => (
          <div
            key={step}
            className="h-3 bg-gray-200 rounded animate-pulse"
            style={{ width: `${60 + Math.random() * 30}%` }}
          />
        )
      )}
    </div>
  );
}

// ── Main Advisor Component ────────────────────────────────────────────────

function AdvisorMain() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: health, isLoading: healthLoading, refetch: refetchHealth } = usePortfolioHealth();
  const { data: job } = useAdvisorJob(jobId);
  const { data: screenerAssets, isLoading: screenerLoading } = useSmartScreener(
    health?.has_portfolio === true
  );

  const isRunning =
    isSubmitting || (!!jobId && (job?.status === "pending" || job?.status === "running"));

  const advisorResult: AdvisorAnalysisResult | null =
    job?.status === "completed" ? (job.result ?? null) : null;

  const jobFailed = !!jobId && job?.status === "failed";
  const failureMessage =
    job?.error_message || "A análise falhou. Tente novamente em alguns minutos.";

  async function handleAnalyze() {
    setError(null);
    setIsSubmitting(true);
    setJobId(null);
    try {
      const created = await startAdvisorAnalysis();
      setJobId(created.job_id);
      queryClient.invalidateQueries({ queryKey: ["advisor"] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao iniciar análise");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRefreshHealth() {
    queryClient.invalidateQueries({ queryKey: ["advisor", "health"] });
    refetchHealth();
  }

  return (
    <div className="space-y-8">
      {/* 1. Health Check Card — deterministic, loads immediately (Phase 23) */}
      <HealthSection health={health} isLoading={healthLoading} onRefresh={handleRefreshHealth} />

      {/* 2. AI Diagnosis — shows after analysis completes (Phase 24) */}
      {advisorResult && <AIDiagnosisSection result={advisorResult} />}

      {/* 3. Smart Screener — complementary assets (sectors not in portfolio) (Phase 25) */}
      {health?.has_portfolio && (
        <SmartScreenerSection
          assets={screenerAssets ?? []}
          isLoading={screenerLoading}
        />
      )}

      {/* In-progress state */}
      {isRunning && !advisorResult && <AnalysisInProgress />}

      {/* Analyze CTA */}
      {!advisorResult && (
        <div className="rounded-lg bg-[#111827] text-white p-8 text-center space-y-4">
          <div>
            <h2 className="text-lg font-bold tracking-tight">Análise completa da carteira</h2>
            <p className="text-sm text-gray-400 mt-1">
              A IA analisa suas posições, alocação, P&L e contexto macro para gerar um
              diagnóstico personalizado.
            </p>
          </div>
          <button
            onClick={handleAnalyze}
            disabled={isRunning}
            className="px-6 py-3 rounded-md bg-blue-500 text-white hover:bg-blue-400 hover:scale-105 disabled:opacity-50 transition-all duration-200 font-semibold"
          >
            {isRunning ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                Analisando sua carteira...
              </span>
            ) : (
              "Analisar minha carteira agora"
            )}
          </button>
          {error && <p className="text-sm text-red-400">{error}</p>}
          {jobFailed && !error && <p className="text-sm text-red-400">{failureMessage}</p>}
        </div>
      )}

      {/* Re-analyze button when result is shown */}
      {advisorResult && (
        <div className="text-center">
          <button
            onClick={handleAnalyze}
            disabled={isRunning}
            className="px-5 py-2.5 rounded-md bg-gray-100 text-sm font-medium hover:bg-gray-200 disabled:opacity-50 transition-colors"
          >
            {isRunning ? "Atualizando..." : "Atualizar diagnóstico"}
          </button>
        </div>
      )}
    </div>
  );
}

export function AdvisorContent() {
  return (
    <PremiumGate>
      <AdvisorMain />
    </PremiumGate>
  );
}
