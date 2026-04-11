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
      className={`inline-flex items-center text-[11px] px-2 py-0.5 rounded-full border font-semibold uppercase tracking-wide ${cls}`}
    >
      {label}
    </span>
  );
}

export function RadarSection({
  signals,
  isLoading,
}: {
  signals: SwingSignalItem[] | undefined;
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-8 bg-gray-100 rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!signals || signals.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-200 bg-white p-12 text-center">
        <p className="text-sm text-gray-500">
          Nenhuma ação com desconto significativo no momento.
        </p>
        <p className="text-xs text-gray-400 mt-1">
          O radar monitora o universo de ações de alta liquidez e destaca
          quedas maiores que 12% do topo de 30 dias.
        </p>
      </div>
    );
  }

  // Sort radar by discount (most negative first)
  const sorted = [...signals].sort((a, b) => a.discount_pct - b.discount_pct);

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">
                Ticker
              </th>
              <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">
                Nome
              </th>
              <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">
                Setor
              </th>
              <th className="text-right py-3 px-4 text-xs font-semibold text-gray-600">
                Preço
              </th>
              <th className="text-right py-3 px-4 text-xs font-semibold text-gray-600">
                Topo 30d
              </th>
              <th className="text-right py-3 px-4 text-xs font-semibold text-gray-600">
                Desconto
              </th>
              <th className="text-right py-3 px-4 text-xs font-semibold text-gray-600">
                DY
              </th>
              <th className="text-center py-3 px-4 text-xs font-semibold text-gray-600">
                Sinal
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((item) => {
              const rowBg =
                item.signal === "buy"
                  ? "bg-green-50 hover:bg-green-100"
                  : "hover:bg-gray-50";
              const discountClass =
                item.discount_pct < 0 ? "text-red-600" : "text-green-600";
              return (
                <tr
                  key={item.ticker}
                  className={`border-b border-gray-100 transition-colors ${rowBg}`}
                >
                  <td className="py-3 px-4">
                    <span className="font-mono font-bold text-sm">
                      {item.ticker}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-xs text-gray-700 max-w-[200px] truncate">
                    {item.name}
                  </td>
                  <td className="py-3 px-4 text-xs text-gray-500">
                    {item.sector}
                  </td>
                  <td className="py-3 px-4 text-right tabular-nums">
                    R$ {fmt(item.current_price)}
                  </td>
                  <td className="py-3 px-4 text-right tabular-nums text-gray-600">
                    R$ {fmt(item.high_30d)}
                  </td>
                  <td
                    className={`py-3 px-4 text-right tabular-nums font-semibold ${discountClass}`}
                  >
                    {fmt(item.discount_pct)}%
                  </td>
                  <td className="py-3 px-4 text-right tabular-nums text-gray-600">
                    {item.dy != null ? `${fmt(item.dy)}%` : "—"}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <SignalBadge signal={item.signal} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
