"use client";

import { motion } from "framer-motion";
import { PieChart, Pie, Cell, Tooltip } from "recharts";
import { ChartContainer } from "@/components/ui/chart";
import { AnimatedNumber } from "@/components/ui/AnimatedNumber";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import { useCryptoAllocation } from "@/features/dashboard/hooks/useCryptoAllocation";
import type { CryptoHolding } from "@/features/dashboard/types";

// Bitcoin orange palette — top 3 holdings cycle through these
const CRYPTO_COLORS = ["#f7931a", "#627eea", "#14b8a6"] as const;

const TICKER_LABELS: Record<string, string> = {
  BTC: "Bitcoin",
  ETH: "Ethereum",
  SOL: "Solana",
  BNB: "BNB",
  ADA: "Cardano",
  AVAX: "Avalanche",
  DOT: "Polkadot",
  MATIC: "Polygon",
  LINK: "Chainlink",
  XRP: "Ripple",
};

const pctFormatter = (v: number) =>
  v.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }) + "%";

const brlFormatter = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

function HoldingRow({
  holding,
  index,
  totalCryptoPct,
}: {
  holding: CryptoHolding;
  index: number;
  totalCryptoPct: number;
}) {
  const pct = parseFloat(holding.pct_of_crypto);
  const value = parseFloat(holding.value);
  const color = CRYPTO_COLORS[index % CRYPTO_COLORS.length];
  const barWidth = Math.min(100, (pct / Math.max(totalCryptoPct, 1)) * 100);
  const label = TICKER_LABELS[holding.ticker.toUpperCase()] ?? holding.ticker;

  return (
    <motion.div
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{
        duration: 0.3,
        ease: [0.16, 1, 0.3, 1],
        delay: 0.1 + index * 0.06,
      }}
      className="flex items-center gap-3"
    >
      {/* Color dot */}
      <span
        className="h-2 w-2 rounded-full shrink-0"
        style={{ backgroundColor: color }}
        aria-hidden
      />

      {/* Ticker + label */}
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline justify-between gap-2 mb-0.5">
          <span className="font-mono font-bold text-xs text-white/90">
            {holding.ticker}
          </span>
          <span className="text-[10px] text-white/40 truncate hidden sm:block">
            {label}
          </span>
          <span className="text-xs font-semibold tabular-nums text-white/80 ml-auto">
            {pct.toFixed(1)}%
          </span>
        </div>
        {/* Progress bar */}
        <div className="h-0.5 w-full rounded-full bg-white/10 overflow-hidden">
          <motion.div
            className="h-full rounded-full"
            style={{ backgroundColor: color }}
            initial={{ width: 0 }}
            animate={{ width: `${barWidth}%` }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay: 0.15 + index * 0.06 }}
          />
        </div>
        <div className="text-[10px] tabular-nums text-white/40 mt-0.5">
          {brlFormatter(value)}
        </div>
      </div>
    </motion.div>
  );
}

function CryptoAllocationSkeleton() {
  return (
    <div className="rounded-2xl p-5 space-y-4 bg-zinc-900 border border-zinc-800">
      <ShimmerSkeleton className="h-3 w-32 bg-zinc-700" />
      <ShimmerSkeleton className="h-12 w-24 bg-zinc-700" />
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="space-y-1">
            <ShimmerSkeleton className="h-2.5 w-full bg-zinc-700" />
            <ShimmerSkeleton className="h-0.5 w-full bg-zinc-800" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function CryptoAllocationCard() {
  const { data, isLoading } = useCryptoAllocation();

  if (isLoading) return <CryptoAllocationSkeleton />;

  // No crypto positions — render nothing (caller can gate on data_available)
  if (!data?.data_available) return null;

  const portfolioPct = parseFloat(data.portfolio_pct);
  const totalValue = parseFloat(data.total_value);

  // Build donut data: top 3 + "Outros" remainder
  const topSum = data.top_holdings.reduce(
    (acc, h) => acc + parseFloat(h.pct_of_crypto),
    0
  );
  const othersRemainder = Math.max(0, 100 - topSum);

  const chartData = [
    ...data.top_holdings.map((h, i) => ({
      name: h.ticker,
      value: parseFloat(h.pct_of_crypto),
      fill: CRYPTO_COLORS[i % CRYPTO_COLORS.length],
    })),
    ...(othersRemainder > 0.5
      ? [{ name: "Outros", value: othersRemainder, fill: "#3f3f46" }]
      : []),
  ];

  const chartConfig = Object.fromEntries(
    chartData.map((d) => [d.name, { label: d.name }])
  );

  // Max pct_of_crypto among top 3 for bar scaling
  const maxPct = data.top_holdings.reduce(
    (m, h) => Math.max(m, parseFloat(h.pct_of_crypto)),
    0
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-2xl p-5 relative overflow-hidden"
      style={{
        background:
          "linear-gradient(135deg, rgba(24,24,27,0.98) 0%, rgba(20,20,23,0.98) 100%)",
        border: "1px solid rgba(247,147,26,0.18)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
      }}
      role="region"
      aria-label="Alocacao em Criptomoedas"
    >
      {/* Decorative glow orbs */}
      <div
        className="absolute -right-10 -top-10 h-44 w-44 rounded-full pointer-events-none"
        style={{
          background:
            "radial-gradient(circle, rgba(247,147,26,0.12) 0%, transparent 70%)",
        }}
        aria-hidden
      />
      <div
        className="absolute left-0 bottom-0 h-28 w-28 rounded-full pointer-events-none"
        style={{
          background:
            "radial-gradient(circle, rgba(98,126,234,0.08) 0%, transparent 70%)",
        }}
        aria-hidden
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-4 relative z-10">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-white/40">
          Crypto
        </h3>
        {/* Bitcoin icon badge */}
        <span
          className="flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-bold"
          style={{ background: "rgba(247,147,26,0.15)", color: "#f7931a" }}
          aria-hidden
        >
          &#8383;
        </span>
      </div>

      {/* Main metric — % of portfolio with animated counter */}
      <div className="relative z-10 mb-5">
        <p className="text-4xl font-extrabold tracking-tight tabular-nums text-white">
          <AnimatedNumber
            value={portfolioPct}
            formatter={pctFormatter}
          />
        </p>
        <p className="text-xs text-white/40 mt-0.5">
          da carteira{" "}
          <span className="text-white/60 tabular-nums">
            ({brlFormatter(totalValue)})
          </span>
        </p>
      </div>

      {/* Grid: donut chart + holdings list */}
      <div className="relative z-10 grid grid-cols-1 gap-4 sm:grid-cols-[auto_1fr]">
        {/* Donut chart */}
        <div className="flex items-center justify-center sm:justify-start">
          <ChartContainer config={chartConfig} className="h-28 w-28">
            <PieChart>
              <Pie
                data={chartData}
                dataKey="value"
                innerRadius={28}
                outerRadius={44}
                paddingAngle={2}
                startAngle={90}
                endAngle={-270}
                animationBegin={80}
                animationDuration={650}
              >
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.[0]) return null;
                  const d = payload[0].payload as {
                    name: string;
                    value: number;
                  };
                  return (
                    <div
                      className="rounded-lg px-2.5 py-1.5 text-xs shadow-lg"
                      style={{
                        background: "rgba(24,24,27,0.97)",
                        border: "1px solid rgba(255,255,255,0.1)",
                      }}
                    >
                      <p className="font-semibold text-white/90 mb-0.5">
                        {d.name}
                      </p>
                      <p className="text-white/50">{d.value.toFixed(1)}%</p>
                    </div>
                  );
                }}
              />
            </PieChart>
          </ChartContainer>
        </div>

        {/* Top 3 holdings */}
        <div className="flex flex-col justify-center gap-3">
          {data.top_holdings.map((holding, i) => (
            <HoldingRow
              key={holding.ticker}
              holding={holding}
              index={i}
              totalCryptoPct={maxPct}
            />
          ))}
        </div>
      </div>
    </motion.div>
  );
}
