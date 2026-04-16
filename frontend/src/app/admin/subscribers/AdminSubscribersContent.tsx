"use client";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

interface Subscriber {
  user_id: string;
  email: string;
  plan: string;
  subscription_status: string | null;
  stripe_customer_id: string | null;
  subscription_current_period_end: string | null;
  created_at: string;
}

const STATUS_STYLES: Record<string, string> = {
  active: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  past_due: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  canceled: "bg-red-500/20 text-red-400 border-red-500/30",
  trialing: "bg-blue-500/20 text-blue-400 border-blue-500/30",
};

function StatusBadge({ value }: { value: string | null }) {
  if (!value) return <span className="text-gray-600">—</span>;
  const cls = STATUS_STYLES[value] ?? "bg-white/10 text-white border-white/20";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium border ${cls}`}>
      {value}
    </span>
  );
}

export function AdminSubscribersContent() {
  const { data, isLoading, error } = useQuery<Subscriber[]>({
    queryKey: ["admin-subscribers"],
    queryFn: () => apiClient<Subscriber[]>("/billing/admin/subscribers"),
    retry: false,
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="bg-[#1f2937] rounded-lg h-12 animate-pulse border border-white/10" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400">
        Acesso negado ou erro ao carregar assinantes.
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <p className="text-gray-500 text-sm">Nenhum assinante pago ainda.</p>
    );
  }

  return (
    <div className="rounded-xl border border-white/10 overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-white/5 border-b border-white/10">
          <tr>
            <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wide">Email</th>
            <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wide">Plano</th>
            <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wide">Status</th>
            <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wide">Período até</th>
            <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wide">Desde</th>
          </tr>
        </thead>
        <tbody>
          {data.map((s, i) => (
            <tr
              key={s.user_id}
              className={`border-t border-white/5 hover:bg-white/5 transition-colors ${i % 2 === 0 ? "" : "bg-white/[0.02]"}`}
            >
              <td className="px-4 py-3 text-white font-mono text-xs">{s.email}</td>
              <td className="px-4 py-3 capitalize text-gray-300">{s.plan}</td>
              <td className="px-4 py-3">
                <StatusBadge value={s.subscription_status} />
              </td>
              <td className="px-4 py-3 text-gray-400 text-xs">
                {s.subscription_current_period_end
                  ? new Date(s.subscription_current_period_end).toLocaleDateString("pt-BR")
                  : "—"}
              </td>
              <td className="px-4 py-3 text-gray-500 text-xs">
                {new Date(s.created_at).toLocaleDateString("pt-BR")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="px-4 py-2 border-t border-white/10 text-xs text-gray-600">
        {data.length} assinante{data.length !== 1 ? "s" : ""} pagantes
      </div>
    </div>
  );
}
