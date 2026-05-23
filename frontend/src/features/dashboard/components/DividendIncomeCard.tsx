"use client";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { apiClient } from "@/lib/api-client";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";

interface DividendMonth {
  month: string;
  dividend: string;
  jscp: string;
  amortization: string;
  total: string;
}

interface DividendIncomeSummary {
  months: DividendMonth[];
  total_12m: string;
  monthly_avg_12m: string;
  ytd_total: string;
  biggest_month_brl: string;
  biggest_month_label: string;
  data_available: boolean;
}

function fmtBrl(v: string | number) {
  const n = typeof v === "string" ? parseFloat(v) : v;
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(n);
}

function shortMonth(yyyyMM: string) {
  const [yr, mo] = yyyyMM.split("-");
  const abbr = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
  return `${abbr[parseInt(mo) - 1]}/${yr.slice(2)}`;
}

export function DividendIncomeCard() {
  const { data, isLoading } = useQuery({
    queryKey: ["portfolio", "dividend-income"],
    queryFn: () => apiClient<DividendIncomeSummary>("/portfolio/dividend-income?months=24"),
    staleTime: 30 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="rounded-xl border border-zinc-100 bg-white p-4 space-y-3">
        <ShimmerSkeleton className="h-3 w-32" />
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <ShimmerSkeleton key={i} className="h-12 rounded-lg" />
          ))}
        </div>
        <ShimmerSkeleton className="h-40 rounded-lg" />
      </div>
    );
  }

  if (!data || !data.data_available) {
    return (
      <div className="rounded-xl border border-zinc-200 bg-white p-5">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 mb-4">
          Proventos Recebidos
        </p>
        <div className="flex flex-col items-center gap-3 py-5 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-50 border border-emerald-100">
            <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5 text-emerald-400" aria-hidden>
              <path d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <p className="text-sm font-medium text-zinc-700">Nenhum provento registrado</p>
            <p className="text-xs text-zinc-400 mt-0.5">Adicione transações do tipo Dividendo, JCP ou Amortização</p>
          </div>
        </div>
      </div>
    );
  }

  const chartData = data.months.slice(-18).map((m) => ({
    name: shortMonth(m.month),
    Dividendo: parseFloat(m.dividend),
    JCP: parseFloat(m.jscp),
    Amortização: parseFloat(m.amortization),
    total: parseFloat(m.total),
  }));

  const summaryCards = [
    { label: "Total 12 meses", value: fmtBrl(data.total_12m), color: "text-emerald-700" },
    { label: "Média mensal", value: fmtBrl(data.monthly_avg_12m), color: "text-blue-700" },
    { label: "YTD", value: fmtBrl(data.ytd_total), color: "text-violet-700" },
    {
      label: `Maior mês (${data.biggest_month_label})`,
      value: fmtBrl(data.biggest_month_brl),
      color: "text-amber-700",
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-xl border border-zinc-200 bg-white p-4 space-y-4"
    >
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
          Proventos Recebidos
        </p>
        <span className="text-[11px] text-zinc-300">últimos 24 meses</span>
      </div>

      {/* Summary chips */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {summaryCards.map(({ label, value, color }, i) => (
          <motion.div
            key={label}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1], delay: i * 0.05 }}
            className="rounded-lg bg-zinc-50 border border-zinc-100 px-3 py-2"
          >
            <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide">{label}</p>
            <p className={`text-sm font-extrabold mt-0.5 tabular-nums ${color}`}>{value}</p>
          </motion.div>
        ))}
      </div>

      {/* Bar chart */}
      {chartData.length > 0 && (
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={chartData} margin={{ top: 0, right: 0, left: 0, bottom: 0 }} barSize={12}>
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10, fill: "#9ca3af" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 10, fill: "#9ca3af" }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `R$${v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}`}
              width={42}
            />
            <Tooltip
              formatter={(value: number, name: string) => [fmtBrl(value), name]}
              contentStyle={{ fontSize: 11, borderRadius: 8 }}
            />
            <Legend iconType="square" iconSize={8} wrapperStyle={{ fontSize: 10 }} />
            <Bar dataKey="Dividendo" stackId="a" fill="#10b981" radius={[0, 0, 0, 0]} />
            <Bar dataKey="JCP" stackId="a" fill="#3b82f6" />
            <Bar dataKey="Amortização" stackId="a" fill="#8b5cf6" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </motion.div>
  );
}
