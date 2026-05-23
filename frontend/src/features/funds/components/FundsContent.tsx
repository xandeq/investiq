"use client";
import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { Bank, Info } from "@phosphor-icons/react";
import { FundSearchBar } from "./FundSearchBar";
import { FundPositionsTable } from "./FundPositionsTable";
import { FundInfoPanel } from "./FundInfoPanel";
import { useFundPositions } from "../hooks/useFundPositions";
import type { FundSearchResult } from "../types";

export function FundsContent() {
  const [selectedFund, setSelectedFund] = useState<FundSearchResult | null>(null);
  const { data: positions = [], isLoading } = useFundPositions();

  return (
    <div className="space-y-8">
      {/* Search section */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-zinc-700">Consultar Fundo</h2>
          <span className="text-[10px] text-zinc-400 border border-zinc-200 rounded px-1.5 py-0.5">CVM</span>
        </div>
        <p className="text-xs text-zinc-500">
          Busque fundos de investimento registrados na CVM por nome ou CNPJ.
        </p>
        <div className="flex gap-3 items-start flex-wrap">
          <FundSearchBar
            onSelect={(fund) => setSelectedFund(fund)}
          />
          {selectedFund && (
            <button
              onClick={() => setSelectedFund(null)}
              className="text-xs text-zinc-500 hover:text-zinc-700 underline pt-2.5 active:scale-[0.97] transition-all duration-150"
            >
              limpar
            </button>
          )}
        </div>

        <AnimatePresence>
          {selectedFund && (
            <FundInfoPanel
              key={selectedFund.cnpj}
              cnpj={selectedFund.cnpj}
              onClose={() => setSelectedFund(null)}
            />
          )}
        </AnimatePresence>
      </section>

      {/* Positions section */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-zinc-700">Minhas Posições em Fundos</h2>
          {positions.length > 0 && (
            <span className="text-[10px] text-zinc-400">
              {positions.length} {positions.length === 1 ? "fundo" : "fundos"}
            </span>
          )}
        </div>

        {!isLoading && positions.some((p) => p.nav_stale) && (
          <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
            <Info size={14} className="shrink-0 mt-0.5" />
            <span>
              Algumas cotas estão desatualizadas. O NAV é atualizado diariamente pelo job de sincronização.
            </span>
          </div>
        )}

        <FundPositionsTable positions={positions} isLoading={isLoading} />
      </section>
    </div>
  );
}
