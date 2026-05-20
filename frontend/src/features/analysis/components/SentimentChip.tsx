"use client";
import { useSentiment } from "@/hooks/useSentiment";

interface Props {
  ticker: string;
}

export function SentimentChip({ ticker }: Props) {
  const { data } = useSentiment(ticker);
  if (!data || data.score === null || data.mention_count === 0) return null;

  const score = data.score;
  const isPositive = score > 0.1;
  const isNegative = score < -0.1;

  const label = isPositive ? "Positivo" : isNegative ? "Negativo" : "Neutro";
  const colorClass = isPositive
    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
    : isNegative
    ? "bg-red-50 text-red-700 border-red-200"
    : "bg-zinc-50 text-zinc-600 border-zinc-200";
  const icon = isPositive ? "↑" : isNegative ? "↓" : "—";

  return (
    <span
      title={`Sentimento social: ${label} (${data.mention_count} menções nas últimas 24h)`}
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${colorClass}`}
    >
      <span className="font-bold">{icon}</span>
      {label}
      <span className="opacity-60">({data.mention_count})</span>
    </span>
  );
}
