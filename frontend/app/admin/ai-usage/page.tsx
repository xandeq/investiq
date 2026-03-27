"use client";

import { AppNav } from "@/components/AppNav";
import { useState, useEffect, useCallback } from "react";
import { CheckCircle2, XCircle, Zap, BarChart3, Clock, Activity } from "lucide-react";

interface ProviderStat { provider: string; calls: number; success_rate: number; avg_duration_ms: number; }
interface TierStat { tier: string; calls: number; success_rate: number; }
interface UsageStats {
  total_calls: number; successful_calls: number; failed_calls: number;
  success_rate: number; avg_duration_ms: number;
  by_provider: ProviderStat[]; by_tier: TierStat[]; period_days: number;
}
interface LogEntry {
  id: string; created_at: string; tenant_id: string | null; job_id: string | null;
  tier: string; provider: string; model: string; duration_ms: number; success: boolean; error: string | null;
}

const PERIOD_OPTIONS = [
  { label: "7 dias", value: 7 },
  { label: "30 dias", value: 30 },
  { label: "90 dias", value: 90 },
];

const PROVIDER_COLORS: Record<string, string> = {
  openai: "bg-green-500/20 text-green-400 border-green-500/30",
  openrouter: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  groq: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  cerebras: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  gemini: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
};

const TIER_COLORS: Record<string, string> = {
  free: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  paid: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  admin: "bg-amber-500/20 text-amber-400 border-amber-500/30",
};

function Badge({ value, colorMap }: { value: string; colorMap: Record<string, string> }) {
  const cls = colorMap[value] ?? "bg-white/10 text-white border-white/20";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium border ${cls}`}>
      {value}
    </span>
  );
}

function StatCard({ label, value, sub, icon: Icon, color }: { label: string; value: string | number; sub?: string; icon: React.ElementType; color: string }) {
  return (
    <div className="bg-[#1f2937] rounded-xl border border-white/10 p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-gray-400 font-medium">{label}</span>
        <div className={`p-2 rounded-lg ${color}`}><Icon className="h-4 w-4" /></div>
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
    </div>
  );
}

function AIUsageContent() {
  const [days, setDays] = useState(7);
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (d: number) => {
    setLoading(true);
    try {
      const [s, l] = await Promise.all([
        fetch(`/api/admin/ai-usage/stats?days=${d}`, { credentials: "include" }).then(r => r.json()),
        fetch(`/api/admin/ai-usage/logs?days=${d}&limit=100`, { credentials: "include" }).then(r => r.json()),
      ]);
      setStats(s);
      setLogs(Array.isArray(l) ? l : []);
    } catch { /* ignore */ } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(days); }, [days, load]);

  const fmt = (ms: number) => ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
  const fmtDate = (s: string) => new Date(s).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Activity className="h-6 w-6 text-amber-400" /> AI Usage
          </h1>
          <p className="text-sm text-gray-400 mt-1">Monitoramento de chamadas LLM por provider e tier</p>
        </div>
        <div className="flex items-center gap-1 bg-[#1f2937] rounded-lg border border-white/10 p-1">
          {PERIOD_OPTIONS.map(o => (
            <button key={o.value} onClick={() => setDays(o.value)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${days === o.value ? "bg-amber-500 text-white" : "text-gray-400 hover:text-white"}`}>
              {o.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-400" />
        </div>
      ) : stats ? (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard label="Total de Chamadas" value={stats.total_calls} icon={Zap} color="bg-amber-500/20 text-amber-400" />
            <StatCard label="Taxa de Sucesso" value={`${stats.success_rate}%`} sub={`${stats.successful_calls} sucessos`} icon={CheckCircle2} color="bg-emerald-500/20 text-emerald-400" />
            <StatCard label="Duração Média" value={fmt(stats.avg_duration_ms)} icon={Clock} color="bg-blue-500/20 text-blue-400" />
            <StatCard label="Falhas" value={stats.failed_calls} icon={XCircle} color={stats.failed_calls > 0 ? "bg-red-500/20 text-red-400" : "bg-gray-500/20 text-gray-400"} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div className="bg-[#1f2937] rounded-xl border border-white/10 p-5">
              <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-amber-400" /> Por Provider
              </h2>
              {stats.by_provider.length === 0 ? (
                <p className="text-xs text-gray-500">Nenhum dado</p>
              ) : (
                <div className="space-y-3">
                  {stats.by_provider.map(p => (
                    <div key={p.provider}>
                      <div className="flex items-center justify-between mb-1">
                        <Badge value={p.provider} colorMap={PROVIDER_COLORS} />
                        <span className="text-xs text-gray-400">{p.calls} calls · {p.success_rate}% ok · {fmt(p.avg_duration_ms)}</span>
                      </div>
                      <div className="w-full bg-white/5 rounded-full h-1.5">
                        <div className="bg-amber-500 h-1.5 rounded-full" style={{ width: `${(p.calls / stats.total_calls) * 100}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="bg-[#1f2937] rounded-xl border border-white/10 p-5">
              <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-amber-400" /> Por Tier
              </h2>
              {stats.by_tier.length === 0 ? (
                <p className="text-xs text-gray-500">Nenhum dado</p>
              ) : (
                <div className="space-y-3">
                  {stats.by_tier.map(t => (
                    <div key={t.tier}>
                      <div className="flex items-center justify-between mb-1">
                        <Badge value={t.tier} colorMap={TIER_COLORS} />
                        <span className="text-xs text-gray-400">{t.calls} calls · {t.success_rate}% ok</span>
                      </div>
                      <div className="w-full bg-white/5 rounded-full h-1.5">
                        <div className="bg-amber-500 h-1.5 rounded-full" style={{ width: `${(t.calls / stats.total_calls) * 100}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="bg-[#1f2937] rounded-xl border border-white/10 overflow-hidden">
            <div className="px-5 py-4 border-b border-white/10">
              <h2 className="text-sm font-semibold text-white">Chamadas Recentes</h2>
              <p className="text-xs text-gray-400 mt-0.5">{logs.length} registros nos últimos {days} dias</p>
            </div>
            {logs.length === 0 ? (
              <div className="px-5 py-12 text-center text-sm text-gray-500">Nenhuma chamada registrada neste período.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="bg-white/5">
                    <tr>
                      {["Hora", "Tier", "Provider", "Modelo", "Duração", "Status"].map(h => (
                        <th key={h} className="px-4 py-3 text-left text-gray-400 font-medium whitespace-nowrap">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {logs.map(l => (
                      <tr key={l.id} className="hover:bg-white/5 transition-colors">
                        <td className="px-4 py-3 text-gray-400 whitespace-nowrap">{fmtDate(l.created_at)}</td>
                        <td className="px-4 py-3"><Badge value={l.tier} colorMap={TIER_COLORS} /></td>
                        <td className="px-4 py-3"><Badge value={l.provider} colorMap={PROVIDER_COLORS} /></td>
                        <td className="px-4 py-3 text-gray-300 font-mono max-w-[200px] truncate" title={l.model}>{l.model}</td>
                        <td className="px-4 py-3 text-gray-300 whitespace-nowrap">{fmt(l.duration_ms)}</td>
                        <td className="px-4 py-3">
                          {l.success ? (
                            <span className="flex items-center gap-1 text-emerald-400"><CheckCircle2 className="h-3.5 w-3.5" /> ok</span>
                          ) : (
                            <span className="flex items-center gap-1 text-red-400" title={l.error ?? ""}><XCircle className="h-3.5 w-3.5" /> erro</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="text-center text-gray-500 py-16">Erro ao carregar dados de uso.</div>
      )}
    </div>
  );
}

export default function AdminAIUsagePage() {
  return (
    <main className="min-h-screen bg-[#111827] text-white">
      <AppNav />
      <AIUsageContent />
    </main>
  );
}
