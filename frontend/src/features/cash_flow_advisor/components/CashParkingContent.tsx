"use client";

import { AlertCircle, RefreshCw, WalletCards } from "lucide-react";
import { useCashParking } from "../hooks/useCashParking";
import { CashParkingHero } from "./CashParkingHero";
import { CashParkingTable } from "./CashParkingTable";

export function CashParkingContent() {
  const { data, isLoading, isFetching, error, refetch } = useCashParking();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-40 rounded-lg bg-gray-100 animate-pulse" />
        <div className="h-64 rounded-lg bg-gray-100 animate-pulse" />
      </div>
    );
  }

  if (error || !data) {
    const message = error instanceof Error ? error.message : "Erro ao carregar recomendação de caixa.";
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-5">
        <div className="flex items-start gap-3">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" aria-hidden />
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-amber-950">Caixa indisponível</h2>
            <p className="mt-1 text-sm text-amber-800">{message}</p>
            <button
              onClick={() => refetch()}
              className="mt-3 inline-flex items-center gap-2 rounded-md bg-amber-600 px-3 py-2 text-sm font-semibold text-white hover:bg-amber-700 disabled:opacity-50"
              disabled={isFetching}
            >
              <RefreshCw className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`} aria-hidden />
              Atualizar
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
        Análise informativa - não constitui recomendação de investimento. Valores estimados dependem de DIAX,
        CDI/SELIC em cache e regras tributárias vigentes.
      </div>

      <CashParkingHero data={data} />

      {data.warnings.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-gray-900">
            <WalletCards className="h-4 w-4 text-gray-500" aria-hidden />
            Avisos
          </div>
          <ul className="space-y-1 text-sm text-gray-600">
            {data.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      <CashParkingTable rows={data.rows} />

      <p className="text-center text-xs text-gray-400">
        IOF incide sobre rendimento em resgates até 29 dias. IR regressivo aplicado conforme prazo.
      </p>
    </div>
  );
}
