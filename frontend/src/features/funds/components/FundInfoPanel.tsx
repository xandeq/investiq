"use client";
import { motion } from "framer-motion";
import { X, Bank, Spinner } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { getFundInfo } from "../api";

interface Props {
  cnpj: string;
  onClose: () => void;
}

export function FundInfoPanel({ cnpj, onClose }: Props) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["fund-info", cnpj],
    queryFn: () => getFundInfo(cnpj),
    staleTime: 10 * 60 * 1000,
  });

  return (
    <motion.div
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 16 }}
      transition={{ duration: 0.2 }}
      className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm"
    >
      <div className="flex items-start justify-between gap-2 mb-4">
        <div className="flex items-center gap-2">
          <Bank size={16} className="text-blue-400 shrink-0" />
          <p className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">Detalhes do Fundo</p>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-md text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 active:scale-[0.97] transition-all duration-150"
        >
          <X size={14} />
        </button>
      </div>

      {isLoading && (
        <div className="flex items-center gap-2 text-zinc-400 text-xs">
          <Spinner size={14} className="animate-spin" />
          Carregando...
        </div>
      )}

      {isError && (
        <p className="text-xs text-red-500">Fundo não encontrado.</p>
      )}

      {data && (
        <dl className="space-y-3">
          {[
            { label: "Nome", value: data.name },
            { label: "CNPJ", value: data.cnpj, mono: true },
            { label: "Administrador", value: data.admin },
            { label: "Classe", value: data.fund_class },
            { label: "Status", value: data.status },
          ].map(({ label, value, mono }) =>
            value ? (
              <div key={label}>
                <dt className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">{label}</dt>
                <dd className={`text-xs text-zinc-800 mt-0.5 ${mono ? "font-mono" : ""}`}>{value}</dd>
              </div>
            ) : null
          )}
        </dl>
      )}
    </motion.div>
  );
}
