"use client";
import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MagnifyingGlass, Spinner, Bank } from "@phosphor-icons/react";
import { useFundSearch } from "../hooks/useFundSearch";
import type { FundSearchResult } from "../types";

interface Props {
  onSelect: (fund: FundSearchResult) => void;
}

export function FundSearchBar({ onSelect }: Props) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);

  const { data, isFetching } = useFundSearch(query);

  const handleSelect = useCallback(
    (fund: FundSearchResult) => {
      onSelect(fund);
      setQuery("");
      setOpen(false);
    },
    [onSelect]
  );

  const results = data ?? [];

  return (
    <div className="relative w-full max-w-xl">
      <div className="flex items-center gap-2 rounded-xl border border-zinc-200 bg-white px-4 py-2.5 shadow-sm focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-100 transition-all">
        <MagnifyingGlass size={16} className="shrink-0 text-zinc-400" />
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          placeholder="Buscar fundo por nome ou CNPJ..."
          className="flex-1 bg-transparent text-sm text-zinc-800 placeholder:text-zinc-400 outline-none"
        />
        {isFetching && (
          <Spinner size={14} className="shrink-0 text-zinc-400 animate-spin" />
        )}
      </div>

      <AnimatePresence>
        {open && query.trim().length >= 2 && (
          <motion.div
            key="dropdown"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
            className="absolute left-0 right-0 top-full mt-1 z-50 rounded-xl border border-zinc-200 bg-white shadow-xl overflow-hidden"
          >
            {results.length === 0 && !isFetching && (
              <p className="px-4 py-3 text-xs text-zinc-500">Nenhum fundo encontrado.</p>
            )}
            {results.map((fund) => (
              <button
                key={fund.cnpj}
                onMouseDown={() => handleSelect(fund)}
                className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-zinc-50 active:scale-[0.97] transition-all duration-150 border-b border-zinc-100 last:border-0"
              >
                <Bank size={16} className="shrink-0 mt-0.5 text-blue-400" />
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-zinc-800 truncate">{fund.name}</p>
                  <p className="text-[10px] text-zinc-400 font-mono">{fund.cnpj}</p>
                  {fund.fund_class && (
                    <p className="text-[10px] text-zinc-500">{fund.fund_class}</p>
                  )}
                </div>
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
