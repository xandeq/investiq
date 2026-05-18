"use client";
import { motion } from "framer-motion";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Warning, TrendDown, Info, CheckCircle, ArrowClockwise } from "@phosphor-icons/react";
import { apiClient } from "@/lib/api-client";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

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

const SEV: Record<string, { bg: string; bar: string; icon: React.ElementType; iconColor: string }> = {
  alert:   { bg: "bg-red-50",   bar: "bg-red-500",   icon: Warning,      iconColor: "text-red-500"   },
  warning: { bg: "bg-amber-50", bar: "bg-amber-500", icon: TrendDown,     iconColor: "text-amber-500" },
  info:    { bg: "bg-blue-50",  bar: "bg-blue-500",  icon: Info,          iconColor: "text-blue-500"  },
};

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (diff < 1) return "agora";
  if (diff < 60) return `${diff}min`;
  if (diff < 1440) return `${Math.floor(diff / 60)}h`;
  return `${Math.floor(diff / 1440)}d`;
}

export function OpportunityAlerts() {
  const qc = useQueryClient();

  const { data: insights = [], isLoading, isFetching, refetch } = useQuery<Insight[]>({
    queryKey: ["insights"],
    queryFn: () => apiClient("/insights"),
    staleTime: 60_000,
    refetchInterval: 15 * 60 * 1000,
  });

  const seenMut = useMutation({
    mutationFn: (id: string) => apiClient(`/insights/${id}/seen`, { method: "PATCH" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insights"] }),
  });

  const unseen = insights.filter((i) => !i.seen);
  const recent = insights.slice(0, 6);

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-zinc-900">Oportunidades Detectadas</h3>
          {unseen.length > 0 && (
            <span className="inline-flex items-center justify-center rounded-full bg-blue-500 text-white text-xs font-bold w-5 h-5">
              {unseen.length}
            </span>
          )}
          <span className="text-xs text-zinc-400">• atualiza a cada 15min</span>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="p-1.5 rounded-md hover:bg-zinc-100 text-zinc-400 transition-colors disabled:opacity-40"
          title="Atualizar"
          aria-label="Atualizar oportunidades"
        >
          <ArrowClockwise className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
        </button>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {[0, 1, 2].map((n) => (
            <motion.div
              key={n}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: n * 0.06 }}
            >
              <ShimmerSkeleton className="h-16 rounded-lg" />
            </motion.div>
          ))}
        </div>
      )}

      {!isLoading && recent.length === 0 && (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <CheckCircle className="h-8 w-8 text-emerald-300 mb-2" weight="fill" />
          <p className="text-sm text-zinc-400">Nenhuma oportunidade detectada ainda.</p>
          <p className="text-xs text-zinc-300 mt-1">O scanner roda a cada 15 minutos.</p>
        </div>
      )}

      {!isLoading && recent.length > 0 && (
        <div className="space-y-2">
          {recent.map((insight, i) => {
            const cfg = SEV[insight.severity] ?? SEV.info;
            const Icon = cfg.icon;
            return (
              <motion.div
                key={insight.id}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1], delay: i * 0.05 }}
                className={`relative flex items-start gap-3 rounded-lg px-3 py-3 overflow-hidden transition-opacity ${cfg.bg} ${insight.seen ? "opacity-60" : ""}`}
              >
                <div className={`absolute left-0 top-0 bottom-0 w-1 rounded-l-lg ${cfg.bar}`} />
                <Icon className={`mt-0.5 h-4 w-4 flex-shrink-0 ${cfg.iconColor}`} weight="fill" aria-hidden />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-zinc-900 leading-tight">{insight.title}</span>
                    {insight.ticker && (
                      <span className="text-xs font-mono bg-white/70 border border-zinc-200 rounded px-1.5 py-0.5 text-zinc-600">
                        {insight.ticker}
                      </span>
                    )}
                    <span className="text-xs text-zinc-400 ml-auto">{timeAgo(insight.created_at)}</span>
                  </div>
                  <p className="text-xs text-zinc-500 mt-0.5 line-clamp-2">{insight.body}</p>
                </div>
                {!insight.seen && (
                  <button
                    onClick={() => seenMut.mutate(insight.id)}
                    disabled={seenMut.isPending}
                    className="flex-shrink-0 p-1 rounded hover:bg-white/50 text-zinc-400 hover:text-zinc-700 transition-colors"
                    title="Marcar como visto"
                    aria-label="Marcar como visto"
                  >
                    <CheckCircle className="h-4 w-4" />
                  </button>
                )}
              </motion.div>
            );
          })}
        </div>
      )}

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
