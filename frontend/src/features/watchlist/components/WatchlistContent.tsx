"use client";
import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { CheckCircle, Bell, BellSlash } from "@phosphor-icons/react";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import { tickerPath } from "@/lib/formatters";
import { useSortedData } from "@/hooks/useSort";
import { SortableHeader } from "@/components/ui/SortableHeader";
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

function dyColor(v: string | null): string {
  if (!v) return "text-zinc-400";
  const n = parseFloat(v);
  if (isNaN(n)) return "text-zinc-400";
  if (n >= 8) return "text-emerald-600 font-medium";
  if (n >= 5) return "text-emerald-500";
  if (n >= 3) return "text-zinc-600";
  return "text-zinc-400";
}

function plColor(v: string | null): string {
  if (!v) return "text-zinc-400";
  const n = parseFloat(v);
  if (isNaN(n) || n <= 0) return "text-zinc-400";
  if (n < 15) return "text-emerald-600 font-medium";
  if (n < 25) return "text-zinc-600";
  return "text-amber-600";
}

function pvpColor(v: string | null): string {
  if (!v) return "text-zinc-400";
  const n = parseFloat(v);
  if (isNaN(n) || n <= 0) return "text-zinc-400";
  if (n <= 1) return "text-emerald-600 font-medium";
  if (n <= 1.5) return "text-zinc-600";
  return "text-amber-600";
}

function changeBadge(v: string | null) {
  if (!v) return <span className="text-zinc-400 text-xs">—</span>;
  const n = parseFloat(v);
  if (isNaN(n)) return <span className="text-zinc-400 text-xs">—</span>;
  const color = n >= 0 ? "text-emerald-600" : "text-red-500";
  return <span className={`text-xs font-semibold tabular-nums ${color}`}>{n >= 0 ? "+" : ""}{n.toFixed(2)}%</span>;
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
        className="bg-zinc-100 text-zinc-900 rounded-md px-3 py-2 text-sm w-40 font-mono uppercase border-2 border-transparent focus:outline-none focus:bg-white focus:border-blue-500 transition-all duration-200"
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
        className="text-xs text-zinc-400 hover:text-zinc-700 active:scale-[0.97] transition-all duration-150"
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
        className="w-24 bg-zinc-100 rounded px-2 py-1 text-xs border-2 border-transparent focus:outline-none focus:bg-white focus:border-blue-500 transition-all duration-200"
        autoFocus
      />
      <button
        onClick={async () => {
          await updateMut.mutateAsync({ ticker, data: { price_alert_target: val ? parseFloat(val) : null } });
          setEditing(false);
        }}
        disabled={updateMut.isPending}
        className="text-xs text-emerald-600 font-semibold hover:text-emerald-700 active:scale-[0.97] transition-all duration-150"
      >
        Ok
      </button>
      <button
        onClick={() => setEditing(false)}
        className="text-xs text-zinc-400 hover:text-zinc-700 active:scale-[0.97] transition-all duration-150"
      >
        ×
      </button>
    </div>
  );
}

function AlertBadge({ item }: { item: WatchlistQuote }) {
  if (!item.price_alert_target) return null;

  if (item.alert_triggered_at) {
    const firedAt = new Date(item.alert_triggered_at);
    const hoursAgo = (Date.now() - firedAt.getTime()) / 3_600_000;
    if (hoursAgo < 25) {
      const day = firedAt.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
      const time = firedAt.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
      return (
        <span
          title="Email de alerta enviado"
          className="inline-flex items-center gap-1 text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold px-2 py-0.5 rounded-full whitespace-nowrap"
        >
          <CheckCircle size={11} weight="fill" />
          Disparado em {day} {time}
        </span>
      );
    }
  }

  if (item.price && Number(item.price_alert_target) > 0) {
    const diff = Math.abs(Number(item.price) - Number(item.price_alert_target)) / Number(item.price_alert_target);
    if (diff <= 0.02) {
      return (
        <span
          title="Preco proximo do alvo — email sera enviado no proximo ciclo (15 min)"
          className="inline-flex items-center gap-1 text-xs bg-amber-50 text-amber-700 border border-amber-300 font-bold px-2 py-0.5 rounded-full animate-pulse"
        >
          <Bell size={11} weight="fill" />
          Alerta ativo
        </span>
      );
    }
  }

  return (
    <span
      title={`Monitorando R$ ${Number(item.price_alert_target).toFixed(2)}`}
      className="inline-flex items-center gap-1 text-xs bg-blue-50 text-blue-400 border border-blue-100 px-2 py-0.5 rounded-full"
    >
      <BellSlash size={11} />
      Aguardando
    </span>
  );
}

function WatchlistRow({ item, index }: { item: WatchlistQuote; index: number }) {
  const removeMut = useRemoveFromWatchlist();

  return (
    <motion.tr
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1], delay: index * 0.04 }}
      className="hover:bg-zinc-50/60 transition-colors"
    >
      <td className="px-4 py-3">
        <div className="flex items-center gap-2 flex-wrap">
          <Link href={tickerPath(item.ticker)} className="font-mono font-semibold hover:text-blue-600 transition-colors">
            {item.ticker}
          </Link>
          {item.price_alert_target && <AlertBadge item={item} />}
        </div>
        {item.notes && <p className="text-xs text-zinc-400 mt-0.5">{item.notes}</p>}
      </td>
      <td className="px-4 py-3 text-right tabular-nums font-medium">
        {item.data_stale ? <span className="text-xs text-zinc-400">N/D</span> : fmtBRL(item.price)}
      </td>
      <td className="px-4 py-3 text-right">
        {item.data_stale ? <span className="text-zinc-400 text-xs">—</span> : changeBadge(item.change_pct)}
      </td>
      <td className={`px-4 py-3 text-right tabular-nums text-sm ${dyColor(item.dy)}`}>{fmtPct(item.dy)}</td>
      <td className={`px-4 py-3 text-right tabular-nums text-sm ${plColor(item.pl)}`}>{item.pl != null ? `${parseFloat(item.pl).toFixed(1)}x` : "—"}</td>
      <td className={`px-4 py-3 text-right tabular-nums text-sm ${pvpColor(item.pvp)}`}>{item.pvp != null ? `${parseFloat(item.pvp).toFixed(2)}x` : "—"}</td>
      <td className="px-4 py-3 text-right">
        <AlertInline ticker={item.ticker} current={item.price_alert_target} />
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1 justify-end">
          <Link
            href={tickerPath(item.ticker)}
            className="text-xs text-zinc-400 hover:text-blue-500 px-2 py-1 rounded-md hover:bg-blue-50 transition-all duration-200"
          >
            Ver
          </Link>
          <Link
            href={`/ai?ticker=${item.ticker}`}
            className="text-xs text-zinc-400 hover:text-blue-500 px-2 py-1 rounded-md hover:bg-blue-50 transition-all duration-200"
          >
            IA
          </Link>
          <button
            onClick={() => removeMut.mutate(item.ticker)}
            disabled={removeMut.isPending}
            className="text-xs text-zinc-400 hover:text-red-500 px-2 py-1 rounded-md hover:bg-red-50 transition-all duration-200"
          >
            Remover
          </button>
        </div>
      </td>
    </motion.tr>
  );
}

export function WatchlistContent() {
  const { data: quotes = [], isLoading } = useWatchlistQuotes();
  const { sorted, col, dir, toggle } = useSortedData(quotes, "ticker", "asc");

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Watchlist</h2>
          <p className="text-sm text-zinc-400">Acompanhe ativos que você monitora</p>
        </div>
        <AddForm />
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-zinc-100">
              <tr>
                <SortableHeader col="ticker" label="Ticker" activeCol={col} dir={dir} onSort={toggle} className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wider text-zinc-400" />
                <SortableHeader col="price" label="Preço" activeCol={col} dir={dir} onSort={toggle} className="text-right px-4 py-3 text-xs font-bold uppercase tracking-wider text-zinc-400" align="right" />
                <SortableHeader col="change_pct" label="Var." activeCol={col} dir={dir} onSort={toggle} className="text-right px-4 py-3 text-xs font-bold uppercase tracking-wider text-zinc-400" align="right" />
                <SortableHeader col="dy" label="DY" activeCol={col} dir={dir} onSort={toggle} className="text-right px-4 py-3 text-xs font-bold uppercase tracking-wider text-zinc-400" align="right" />
                <SortableHeader col="pl" label="P/L" activeCol={col} dir={dir} onSort={toggle} className="text-right px-4 py-3 text-xs font-bold uppercase tracking-wider text-zinc-400" align="right" />
                <SortableHeader col="pvp" label="P/VP" activeCol={col} dir={dir} onSort={toggle} className="text-right px-4 py-3 text-xs font-bold uppercase tracking-wider text-zinc-400" align="right" />
                <th className="text-right px-4 py-3 text-xs font-bold uppercase tracking-wider text-zinc-400">Alerta</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-50">
              {isLoading && (
                <tr>
                  <td colSpan={8} className="px-4 py-4">
                    <div className="space-y-2">
                      {[0,1,2].map((n) => <ShimmerSkeleton key={n} className="h-8 w-full rounded-md" />)}
                    </div>
                  </td>
                </tr>
              )}
              {!isLoading && quotes.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-zinc-400 text-sm">
                    Sua watchlist está vazia. Adicione um ticker acima.
                  </td>
                </tr>
              )}
              {sorted.map((q, i) => (
                <WatchlistRow key={q.ticker} item={q} index={i} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
