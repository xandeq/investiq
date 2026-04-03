"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { AlertTriangle, TrendingDown, Info, CheckCircle2, RefreshCw } from "lucide-react";

interface Insight {
  id: string;
  type: string;
  title: string;
  body: string;
  severity: string;
  ticker: string | null;
  seen: boolean;
  created_at: string | null;
}

const SEV: Record<string, { bg: string; bar: string; icon: React.ElementType; iconColor: string; label: string }> = {
  alert:   { bg: "bg-red-50",    bar: "bg-red-500",    icon: AlertTriangle, iconColor: "text-red-500",    label: "Alerta" },
  warning: { bg: "bg-amber-50",  bar: "bg-amber-500",  icon: TrendingDown,  iconColor: "text-amber-500",  label: "Atenção" },
  info:    { bg: "bg-blue-50",   bar: "bg-blue-500",   icon: Info,          iconColor: "text-blue-500",   label: "Info" },
};

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (diff < 1) return "agora";
  if (diff < 60) return `${diff}min atrás`;
  if (diff < 1440) return `${Math.floor(diff / 60)}h atrás`;
  return `${Math.floor(diff / 1440)}d atrás`;
}

export function OpportunityAlerts() {
  const qc = useQueryClient();

  const { data: insights = [], isLoading, isFetching, refetch } = useQuery<Insight[]>({
    queryKey: ["insights"],
    queryFn: () => apiClient("/insights"),
    staleTime: 60_000,
    refetchInterval: 15 * 60 * 1000, // auto-refresh every 15 min (aligned with celery-beat)
  });

  const seenMut = useMutation({
    mutationFn: (id: string) => apiClient(`/insights/${id}/seen`, { method: "PATCH" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insights"] }),
  });

  const unseen = insights.filter((i) => !i.seen);
  const recent = insights.slice(0, 6); // show up to 6 (seen + unseen)

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-gray-900">Oportunidades Detectadas</h3>
          {unseen.length > 0 && (
            <span className="inline-flex items-center justify-center rounded-full bg-blue-500 text-white text-xs font-bold w-5 h-5">
              {unseen.length}
            </span>
          )}
          <span className="text-xs text-muted-foreground">• atualiza a cada 15min</span>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="p-1.5 rounded-md hover:bg-gray-100 text-muted-foreground transition-colors disabled:opacity-40"
          title="Atualizar"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Loading skeleton */}
      {isLoading && (
        <div className="space-y-2">
          {[1, 2, 3].map((n) => (
            <div key={n} className="h-16 rounded-lg bg-gray-100 animate-pulse" />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && recent.length === 0 && (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <CheckCircle2 className="h-8 w-8 text-green-400 mb-2" />
          <p className="text-sm text-muted-foreground">Nenhuma oportunidade detectada ainda.</p>
          <p className="text-xs text-muted-foreground mt-1">O scanner roda a cada 15 minutos.</p>
        </div>
      )}

      {/* Alerts list */}
      {!isLoading && recent.length > 0 && (
        <div className="space-y-2">
          {recent.map((insight) => {
            const cfg = SEV[insight.severity] ?? SEV.info;
            const Icon = cfg.icon;
            return (
              <div
                key={insight.id}
                className={`relative flex items-start gap-3 rounded-lg px-3 py-3 overflow-hidden transition-opacity ${cfg.bg} ${insight.seen ? "opacity-60" : ""}`}
              >
                {/* Left accent bar */}
                <div className={`absolute left-0 top-0 bottom-0 w-1 rounded-l-lg ${cfg.bar}`} />

                <Icon className={`mt-0.5 h-4 w-4 flex-shrink-0 ${cfg.iconColor}`} />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-gray-900 leading-tight">{insight.title}</span>
                    {insight.ticker && (
                      <span className="text-xs font-mono bg-white/70 border border-gray-200 rounded px-1.5 py-0.5 text-gray-600">
                        {insight.ticker}
                      </span>
                    )}
                    <span className="text-xs text-muted-foreground ml-auto">{timeAgo(insight.created_at)}</span>
                  </div>
                  <p className="text-xs text-gray-600 mt-0.5 line-clamp-2">{insight.body}</p>
                </div>

                {/* Mark as seen */}
                {!insight.seen && (
                  <button
                    onClick={() => seenMut.mutate(insight.id)}
                    disabled={seenMut.isPending}
                    className="flex-shrink-0 p-1 rounded hover:bg-white/50 text-muted-foreground hover:text-gray-700 transition-colors"
                    title="Marcar como visto"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Footer link */}
      {insights.length > 6 && (
        <div className="mt-3 text-center">
          <a href="/insights" className="text-xs text-blue-500 hover:text-blue-600 font-medium">
            Ver todos os {insights.length} alertas →
          </a>
        </div>
      )}
    </div>
  );
}
