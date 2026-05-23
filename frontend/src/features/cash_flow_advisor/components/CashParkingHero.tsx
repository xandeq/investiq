"use client";

import { ArrowRight, CalendarDots, ArrowClockwise, ShieldCheck, Wallet } from "@phosphor-icons/react";
import type { CashParkingResponse } from "../types";

function asNumber(value: string | number | null | undefined): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function formatBRL(value: string | number): string {
  return asNumber(value).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatPct(value: string | number): string {
  return `${asNumber(value).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}%`;
}

function formatDate(value: string): string {
  return new Date(`${value}T00:00:00`).toLocaleDateString("pt-BR");
}

function displayLabel(label: string): string {
  return label === "Poupanca" ? "Poupança" : label;
}

export function CashParkingHero({ data }: { data: CashParkingResponse }) {
  const top = data.rows[0];

  if (!top) {
    return (
      <section className="rounded-lg border border-amber-200 bg-amber-50 p-5">
        <div className="flex items-start gap-3">
          <Wallet className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" weight="fill" aria-hidden />
          <div>
            <h2 className="text-base font-semibold text-amber-950">Caixa abaixo do limite operacional</h2>
            <p className="mt-1 text-sm text-amber-800">Valor disponível: {formatBRL(data.amount)}.</p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-emerald-200 bg-emerald-50 p-5">
      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr] lg:items-center">
        <div>
          <div className="mb-3 flex items-center gap-2 text-sm font-medium text-emerald-700">
            <ShieldCheck className="h-4 w-4" weight="fill" aria-hidden />
            Melhor alternativa líquida para a janela atual
          </div>
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h2 className="text-2xl font-bold text-emerald-950">{displayLabel(top.label)}</h2>
            <span className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-200">
              rank #{top.rank}
            </span>
          </div>
          <p className="mt-2 max-w-2xl text-sm text-emerald-800">
            Para {formatBRL(data.amount)} por {data.holding_days} dias, rendimento líquido estimado de{" "}
            <strong>{formatBRL(top.net_value_brl)}</strong> ({formatPct(top.net_pct)}).
          </p>
          {data.next_big_outflow && (
            <div className="mt-4 inline-flex flex-wrap items-center gap-2 rounded-md bg-white px-3 py-2 text-sm text-emerald-900 ring-1 ring-emerald-200">
              <CalendarDots className="h-4 w-4 text-emerald-600" weight="fill" aria-hidden />
              Próxima saída: {formatBRL(data.next_big_outflow.amount)} em {formatDate(data.next_big_outflow.date)}
              <ArrowRight className="h-3.5 w-3.5 text-emerald-500" weight="bold" aria-hidden />
              {data.next_big_outflow.description}
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg bg-white p-4 ring-1 ring-emerald-200">
            <p className="text-xs font-medium uppercase text-emerald-700">IOF</p>
            <p className="mt-1 text-xl font-bold tabular-nums text-emerald-950">{formatPct(asNumber(top.iof_pct) * 100)}</p>
          </div>
          <div className="rounded-lg bg-white p-4 ring-1 ring-emerald-200">
            <p className="text-xs font-medium uppercase text-emerald-700">IR</p>
            <p className="mt-1 text-xl font-bold tabular-nums text-emerald-950">{formatPct(asNumber(top.ir_pct) * 100)}</p>
          </div>
          <div className="col-span-2 rounded-lg bg-white p-4 ring-1 ring-emerald-200">
            <p className="flex items-center gap-2 text-xs font-medium uppercase text-emerald-700">
              <ArrowClockwise className="h-3.5 w-3.5" aria-hidden />
              Atualizado
            </p>
            <p className="mt-1 text-sm font-semibold text-emerald-950">
              {new Date(data.generated_at).toLocaleString("pt-BR")}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
