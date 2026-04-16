"use client";
import { useState } from "react";
import Link from "next/link";
import { useWatchlistQuotes, useAddToWatchlist, useRemoveFromWatchlist, useUpdateWatchlistItem } from "../hooks/useWatchlist";
import type { WatchlistQuote } from "../types";

function fmtBRL(v: string | null) {
  if (!v) return "—";
  return Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function fmtPct(v: string | null) {
  if (!v) return "—";
  return `${Number(v).toFixed(2)}%`;
}

function AddForm() {
  const [ticker, setTicker] = useState("");
  const addMut = useAddToWatchlist();
  const [error, setError] = useState("");

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticker.trim()) return;
    setError("");
    try {
      await addMut.mutateAsync({ ticker: ticker.trim().toUpperCase() });
      setTicker("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao adicionar");
    }
  };

  return (
    <form onSubmit={handleAdd} className="flex gap-2">
      <input
        value={ticker}
        onChange={(e) => setTicker(e.target.value)}
        placeholder="Ticker (ex: VALE3)"
        maxLength={10}
        className="bg-gray-100 text-gray-900 rounded-md px-3 py-2 text-sm w-40 font-mono uppercase border-2 border-transparent focus:outline-none focus:bg-white focus:border-blue-500 transition-all duration-200"
      />
      <button
        type="submit"
        disabled={addMut.isPending || !ticker.trim()}
        className="px-4 py-2 text-sm rounded-md bg-blue-500 text-white font-semibold hover:bg-blue-600 hover:scale-105 disabled:opacity-60 transition-all duration-200"
      >
        {addMut.isPending ? "..." : "+ Adicionar"}
      </button>
      {error && <span className="text-xs text-red-500 self-center">{error}</span>}
    </form>
  );
}

function AlertInline({ ticker, current }: { ticker: string; current: string | null }) {
  const updateMut = useUpdateWatchlistItem();
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(current ?? "");

  if (!editing) {
    return (
      <button
        onClick={() => setEditing(true)}
        className="text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        {current ? fmtBRL(current) : "—"}
      </button>
    );
  }

  return (
    <div className="flex items-center gap-1">
      <input
        type="number"
        step="any"
        value={val}
        onChange={(e) => setVal(e.target.value)}
        placeholder="0.00"
        className="w-24 bg-gray-100 rounded px-2 py-1 text-xs border-2 border-transparent focus:outline-none focus:bg-white focus:border-blue-500 transition-all duration-200"
        autoFocus
      />
      <button
        onClick={async () => {
          await updateMut.mutateAsync({ ticker, data: { price_alert_target: val ? parseFloat(val) : null } });
          setEditing(false);
        }}
        disabled={updateMut.isPending}
        className="text-xs text-emerald-600 font-semibold hover:text-emerald-700 transition-colors"
      >
        Ok
      </button>
      <button
        onClick={() => setEditing(false)}
        className="text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        ×
      </button>
    </div>
  );
}

function AlertBadge({ item }: { item: WatchlistQuote }) {
  if (!item.price_alert_target) return null;

  // ✅ Alert fired within last 25h (covers 23h dedup window + buffer)
  if (item.alert_triggered_at) {
    const firedAt = new Date(item.alert_triggered_at);
    const hoursAgo = (Date.now() - firedAt.getTime()) / 3_600_000;
    if (hoursAgo < 25) {
      const day = firedAt.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
      const time = firedAt.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
      return (
        <span
          title="Email de alerta enviado"
          className="text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold px-2 py-0.5 rounded-full whitespace-nowrap"
        >
          ✅ Disparado em {day} {time}
        </span>
      );
    }
  }

  // 🔔 Price is within ±2% of target right now
  if (item.price && Number(item.price_alert_target) > 0) {
    const diff = Math.abs(Number(item.price) - Number(item.price_alert_target)) / Number(item.price_alert_target);
    if (diff <= 0.02) {
      return (
        <span
          title="Preco proximo do alvo — email sera enviado no proximo ciclo (15 min)"
          className="text-xs bg-amber-50 text-amber-700 border border-amber-300 font-bold px-2 py-0.5 rounded-full animate-pulse"
        >
          🔔 Alerta ativo
        </span>
      );
    }
  }

  // Silent monitoring (configured, not yet triggered)
  return (
    <span
      title={`Monitorando R$ ${Number(item.price_alert_target).toFixed(2)}`}
      className="text-xs bg-blue-50 text-blue-400 border border-blue-100 px-2 py-0.5 rounded-full"
    >
      🔕 Aguardando
    </span>
  );
}

function WatchlistRow({ item }: { item: WatchlistQuote }) {
  const removeMut = useRemoveFromWatchlist();

  return (
    <tr className="hover:bg-gray-50/50 transition-colors">
      <td className="px-4 py-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono font-semibold">{item.ticker}</span>
          {item.price_alert_target && <AlertBadge item={item} />}
        </div>
        {item.notes && <p className="text-xs text-muted-foreground mt-0.5">{item.notes}</p>}
      </td>
      <td className="px-4 py-3 text-right tabular-nums font-medium">
        {item.data_stale ? <span className="text-xs text-muted-foreground">N/D</span> : fmtBRL(item.price)}
      </td>
      <td className="px-4 py-3 text-right tabular-nums text-muted-foreground">{fmtPct(item.dy)}</td>
      <td className="px-4 py-3 text-right tabular-nums text-muted-foreground">{item.pl ?? "—"}</td>
      <td className="px-4 py-3 text-right tabular-nums text-muted-foreground">{item.pvp ?? "—"}</td>
      <td className="px-4 py-3 text-right">
        <AlertInline ticker={item.ticker} current={item.price_alert_target} />
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1 justify-end">
          <Link
            href={`/ai?ticker=${item.ticker}`}
            className="text-xs text-muted-foreground hover:text-blue-500 px-2 py-1 rounded-md hover:bg-blue-50 transition-all duration-200"
          >
            Analisar
          </Link>
          <button
            onClick={() => removeMut.mutate(item.ticker)}
            disabled={removeMut.isPending}
            className="text-xs text-muted-foreground hover:text-red-500 px-2 py-1 rounded-md hover:bg-red-50 transition-all duration-200"
          >
            Remover
          </button>
        </div>
      </td>
    </tr>
  );
}

export function WatchlistContent() {
  const { data: quotes = [], isLoading } = useWatchlistQuotes();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Watchlist</h2>
          <p className="text-sm text-muted-foreground">Acompanhe ativos que você monitora</p>
        </div>
        <AddForm />
      </div>

      <div className="rounded-lg bg-white overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted-foreground">Ticker</th>
                <th className="text-right px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted-foreground">Preço</th>
                <th className="text-right px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted-foreground">DY</th>
                <th className="text-right px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted-foreground">P/L</th>
                <th className="text-right px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted-foreground">P/VP</th>
                <th className="text-right px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted-foreground">Alerta</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {isLoading && (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-muted-foreground text-sm">Carregando...</td></tr>
              )}
              {!isLoading && quotes.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-muted-foreground text-sm">
                    Sua watchlist está vazia. Adicione um ticker acima.
                  </td>
                </tr>
              )}
              {quotes.map((q) => (
                <WatchlistRow key={q.ticker} item={q} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
