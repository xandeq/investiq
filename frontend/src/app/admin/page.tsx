"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Users, UserCheck, AlertTriangle, TrendingDown, ArrowRightLeft, XCircle } from "lucide-react";
import { AppNav } from "@/components/AppNav";
import { apiClient } from "@/lib/api-client";

interface MetricsResponse {
  free_users: number;
  pro_users: number;
  active_subscriptions: number;
  past_due_subscriptions: number;
  canceled_subscriptions: number;
  total_conversions: number;
  churn_rate_pct: number;
}

function MetricCard({
  label,
  value,
  sub,
  icon: Icon,
  color,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <div className="bg-[#1f2937] rounded-xl border border-white/10 p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">{label}</span>
        <div className={`p-2 rounded-lg ${color}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
    </div>
  );
}

const NAV_LINKS = [
  { href: "/admin", label: "Visão Geral" },
  { href: "/admin/subscribers", label: "Assinantes" },
  { href: "/admin/ai-usage", label: "Uso de IA" },
];

export default function AdminDashboardPage() {
  const { data, isLoading, error } = useQuery<MetricsResponse>({
    queryKey: ["admin-metrics"],
    queryFn: () => apiClient<MetricsResponse>("/billing/admin/metrics"),
    retry: false,
    staleTime: 60_000,
  });

  return (
    <main className="min-h-screen bg-[#111827] text-white">
      <AppNav />
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold">Admin Dashboard</h1>
          <p className="text-gray-400 text-sm mt-1">Métricas de assinantes e saúde da receita</p>
        </div>

        {/* Admin nav tabs */}
        <nav className="flex gap-1 mb-8 bg-white/5 rounded-lg p-1 w-fit">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="px-4 py-2 rounded-md text-sm font-medium transition-colors bg-white/10 text-white hover:bg-white/20"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        {/* Error state */}
        {error && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400 mb-6">
            Acesso negado ou erro ao carregar métricas. Verifique se seu email está em ADMIN_EMAILS.
          </div>
        )}

        {/* Loading skeleton */}
        {isLoading && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Array.from({ length: 7 }).map((_, i) => (
              <div key={i} className="bg-[#1f2937] rounded-xl border border-white/10 p-5 animate-pulse h-24" />
            ))}
          </div>
        )}

        {/* Metrics grid */}
        {data && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <MetricCard
                label="Usuários Free"
                value={data.free_users}
                icon={Users}
                color="bg-gray-500/20 text-gray-400"
              />
              <MetricCard
                label="Usuários Pro"
                value={data.pro_users}
                icon={UserCheck}
                color="bg-emerald-500/20 text-emerald-400"
              />
              <MetricCard
                label="Assinaturas Ativas"
                value={data.active_subscriptions}
                icon={UserCheck}
                color="bg-blue-500/20 text-blue-400"
              />
              <MetricCard
                label="Em Atraso"
                value={data.past_due_subscriptions}
                sub="past_due no Stripe"
                icon={AlertTriangle}
                color="bg-amber-500/20 text-amber-400"
              />
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
              <MetricCard
                label="Cancelados"
                value={data.canceled_subscriptions}
                sub="total histórico"
                icon={XCircle}
                color="bg-red-500/20 text-red-400"
              />
              <MetricCard
                label="Churn Rate"
                value={`${data.churn_rate_pct}%`}
                sub="cancelados / (ativos + cancelados)"
                icon={TrendingDown}
                color={data.churn_rate_pct > 10 ? "bg-red-500/20 text-red-400" : "bg-green-500/20 text-green-400"}
              />
              <MetricCard
                label="Conversões Totais"
                value={data.total_conversions}
                sub="checkout.session.completed"
                icon={ArrowRightLeft}
                color="bg-purple-500/20 text-purple-400"
              />
            </div>

            {/* Quick links to sub-pages */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Link
                href="/admin/subscribers"
                className="bg-[#1f2937] rounded-xl border border-white/10 p-5 hover:border-white/20 transition-colors group"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-white">Lista de Assinantes</p>
                    <p className="text-xs text-gray-400 mt-1">Ver todos os {data.pro_users} usuários pro com status Stripe</p>
                  </div>
                  <span className="text-gray-500 group-hover:text-white transition-colors">→</span>
                </div>
              </Link>
              <Link
                href="/admin/ai-usage"
                className="bg-[#1f2937] rounded-xl border border-white/10 p-5 hover:border-white/20 transition-colors group"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-white">Uso de IA</p>
                    <p className="text-xs text-gray-400 mt-1">Logs de chamadas LLM, taxa de sucesso, providers</p>
                  </div>
                  <span className="text-gray-500 group-hover:text-white transition-colors">→</span>
                </div>
              </Link>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
