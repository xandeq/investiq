"use client";
import type { SwingSignalItem } from "../types";

const SIGNAL_LABELS: Record<string, string> = {
  buy: "COMPRAR",
  sell: "VENDER",
  neutral: "NEUTRO",
};

const SIGNAL_CLASSES: Record<string, string> = {
  buy: "bg-green-100 text-green-700 border-green-200",
  sell: "bg-red-100 text-red-700 border-red-200",
  neutral: "bg-gray-100 text-gray-600 border-gray-200",
};

function fmt(n: number | null | undefined, decimals = 2): string {
  if (n == null) return "—";
  return n.toLocaleString("pt-BR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function SignalBadge({ signal }: { signal: string }) {
  const label = SIGNAL_LABELS[signal] ?? signal.toUpperCase();
  const cls = SIGNAL_CLASSES[signal] ?? SIGNAL_CLASSES.neutral;
  return (
    <span
      className={`inline-flex items-center text-xs px-2.5 py-1 rounded-full border font-semibold uppercase tracking-wide ${cls}`}
    >
      {label}
    </span>
  );
}

function SignalCard({ item }: { item: SwingSignalItem }) {
  const discountClass =
    item.discount_pct < 0 ? "text-red-600" : "text-green-600";

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="font-mono font-bold text-base text-gray-900">
            {item.ticker}
          </div>
          <div className="text-xs text-gray-500 mt-0.5 truncate max-w-[200px]">
            {item.name}
          </div>
          <div className="text-[11px] text-gray-400 mt-0.5">{item.sector}</div>
        </div>
        <SignalBadge signal={item.signal} />
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs">
        <div>
          <div className="text-gray-500">Preço atual</div>
          <div className="font-semibold text-gray-900 tabular-nums">
            R$ {fmt(item.current_price)}
          </div>
        </div>
        <div>
          <div className="text-gray-500">Topo 30d</div>
          <div className="font-semibold text-gray-900 tabular-nums">
            R$ {fmt(item.high_30d)}
          </div>
        </div>
        <div>
          <div className="text-gray-500">Desconto</div>
          <div className={`font-semibold tabular-nums ${discountClass}`}>
            {fmt(item.discount_pct)}%
          </div>
        </div>
        <div>
          <div className="text-gray-500">DY</div>
          <div className="font-semibold text-gray-900 tabular-nums">
            {item.dy != null ? `${fmt(item.dy)}%` : "—"}
          </div>
        </div>
      </div>

      {item.in_portfolio && item.quantity != null && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-500">Quantidade em carteira</span>
            <span className="font-semibold text-gray-900 tabular-nums">
              {fmt(item.quantity, 0)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export function SignalsSection({
  signals,
  isLoading,
}: {
  signals: SwingSignalItem[] | undefined;
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="rounded-lg border border-gray-200 bg-white p-4 h-40 animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (!signals || signals.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-200 bg-white p-12 text-center">
        <p className="text-sm text-gray-500">
          Nenhuma posição na carteira para gerar sinais.
        </p>
        <p className="text-xs text-gray-400 mt-1">
          Importe suas transações para ver sinais swing trade das suas ações.
        </p>
      </div>
    );
  }

  // Sort by signal_strength descending (biggest moves first)
  const sorted = [...signals].sort(
    (a, b) => b.signal_strength - a.signal_strength,
  );

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {sorted.map((item) => (
        <SignalCard key={item.ticker} item={item} />
      ))}
    </div>
  );
}
