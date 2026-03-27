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

export function AdminSubscribersContent() {
  const { data, isLoading, error } = useQuery<Subscriber[]>({
    queryKey: ["admin-subscribers"],
    queryFn: () => apiClient<Subscriber[]>("/billing/admin/subscribers"),
    retry: false,
  });

  if (isLoading) {
    return <div className="text-muted-foreground text-sm">Carregando…</div>;
  }

  if (error) {
    return (
      <div className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
        Acesso negado ou erro ao carregar assinantes.
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <p className="text-muted-foreground text-sm">Nenhum assinante pago ainda.</p>
    );
  }

  return (
    <div className="rounded-xl border overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-muted/50">
          <tr>
            <th className="text-left px-4 py-3 font-medium text-muted-foreground">Email</th>
            <th className="text-left px-4 py-3 font-medium text-muted-foreground">Plano</th>
            <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
            <th className="text-left px-4 py-3 font-medium text-muted-foreground">Período até</th>
          </tr>
        </thead>
        <tbody>
          {data.map((s) => (
            <tr key={s.user_id} className="border-t hover:bg-muted/20">
              <td className="px-4 py-3 text-foreground">{s.email}</td>
              <td className="px-4 py-3 capitalize">{s.plan}</td>
              <td className="px-4 py-3 text-muted-foreground">
                {s.subscription_status ?? "—"}
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {s.subscription_current_period_end
                  ? new Date(s.subscription_current_period_end).toLocaleDateString("pt-BR")
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
