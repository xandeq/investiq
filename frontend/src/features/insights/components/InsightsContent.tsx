"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { AlertTriangle, Info, Bell, Check } from "lucide-react";

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

const SEV_CONFIG: Record<string, { bg: string; border: string; icon: React.ElementType; iconColor: string }> = {
  alert: { bg: "bg-red-50", border: "border-l-4 border-red-500", icon: AlertTriangle, iconColor: "text-red-500" },
  warning: { bg: "bg-amber-50", border: "border-l-4 border-amber-500", icon: AlertTriangle, iconColor: "text-amber-500" },
  info: { bg: "bg-blue-50", border: "border-l-4 border-blue-500", icon: Info, iconColor: "text-blue-500" },
};

export function InsightsContent() {
  const qc = useQueryClient();
  const { data: insights = [], isLoading } = useQuery<Insight[]>({
    queryKey: ["insights"],
    queryFn: () => apiClient("/insights"),
    staleTime: 60_000,
  });
  const seenMut = useMutation({
    mutationFn: (id: string) => apiClient(`/insights/${id}/seen`, { method: "PATCH" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insights"] }),
  });

  const unseen = insights.filter((i) => !i.seen);
  const seen = insights.filter((i) => i.seen);

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Insights do Copiloto</h2>
        <p className="text-sm text-muted-foreground mt-1">Alertas e oportunidades identificadas automaticamente</p>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((n) => <div key={n} className="h-20 rounded-lg bg-gray-100 animate-pulse" />)}
        </div>
      )}

      {!isLoading && insights.length === 0 && (
        <div className="rounded-lg bg-gray-100 p-12 text-center">
          <Bell className="h-8 w-8 text-gray-400 mx-auto mb-3" />
          <p className="font-semibold text-gray-900">Nenhum insight ainda</p>
          <p className="text-sm text-muted-foreground mt-1">Os alertas são gerados automaticamente todos os dias às 8h.</p>
        </div>
      )}

      {unseen.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Novos — {unseen.length}
          </h3>
          {unseen.map((i) => {
            const cfg = SEV_CONFIG[i.severity] ?? SEV_CONFIG.info;
            const Icon = cfg.icon;
            return (
              <div key={i.id} className={`rounded-lg ${cfg.bg} ${cfg.border} p-4`}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <Icon className={`h-5 w-5 mt-0.5 shrink-0 ${cfg.iconColor}`} strokeWidth={2} />
                    <div>
                      <p className="text-sm font-semibold">{i.title}</p>
                      <p className="text-sm text-muted-foreground mt-0.5">{i.body}</p>
                      {i.ticker && (
                        <span className="inline-block mt-2 text-xs font-bold bg-white px-2 py-0.5 rounded-md text-gray-600">
                          {i.ticker}
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => seenMut.mutate(i.id)}
                    disabled={seenMut.isPending}
                    className="shrink-0 flex items-center gap-1 text-xs font-semibold text-muted-foreground hover:text-foreground bg-white px-3 py-1.5 rounded-md transition-all duration-200 hover:scale-105"
                  >
                    <Check className="h-3.5 w-3.5" />
                    Lido
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {seen.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Anteriores</h3>
          <div className="opacity-50 space-y-2">
            {seen.slice(0, 10).map((i) => (
              <div key={i.id} className="rounded-lg bg-gray-100 p-4">
                <p className="text-sm font-semibold">{i.title}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{i.body}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
