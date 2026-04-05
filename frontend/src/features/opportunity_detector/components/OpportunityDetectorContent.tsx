"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useOpportunityHistory } from "../hooks/useOpportunityHistory";
import { markAsFollowed } from "../api";
import type { OpportunityRow } from "../types";

const RISK_COLORS: Record<string, string> = {
  baixo: "bg-green-100 text-green-700",
  medio: "bg-yellow-100 text-yellow-700",
  alto: "bg-red-100 text-red-700",
  evitar: "bg-gray-900 text-white",
};

const ASSET_TYPE_LABELS: Record<string, string> = {
  acao: "Ação",
  crypto: "Crypto",
  renda_fixa: "Renda Fixa",
};

function fmt(n: number | null, decimals = 2): string {
  if (n == null) return "—";
  return n.toLocaleString("pt-BR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  return (
    d.toLocaleDateString("pt-BR") +
    " " +
    d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
  );
}

function RiskBadge({ level }: { level: string | null }) {
  if (!level) return <span className="text-gray-400">—</span>;
  const cls = RISK_COLORS[level.toLowerCase()] ?? "bg-gray-100 text-gray-600";
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>
      {level}
    </span>
  );
}

function FollowButton({ row }: { row: OpportunityRow }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => markAsFollowed(row.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["opportunity-history"] });
    },
  });

  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        mutation.mutate();
      }}
      disabled={mutation.isPending}
      className="text-lg transition-opacity hover:opacity-70 disabled:opacity-40"
      title={row.followed ? "Seguindo — clique para remover" : "Clique para seguir"}
    >
      {row.followed ? "★" : "☆"}
    </button>
  );
}

function ExpandedDetail({ row }: { row: OpportunityRow }) {
  return (
    <tr>
      <td colSpan={8} className="px-6 pb-4 pt-0 bg-gray-50 border-b border-gray-100">
        <div className="space-y-3 pt-3">
          {row.cause_explanation && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                Causa
              </p>
              <p className="text-sm text-gray-700">{row.cause_explanation}</p>
            </div>
          )}
          {row.risk_rationale && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                Racional de Risco
              </p>
              <p className="text-sm text-gray-700">{row.risk_rationale}</p>
            </div>
          )}
          {(row.recommended_amount_brl != null || row.target_upside_pct != null) && (
            <div className="flex gap-6 text-sm">
              {row.recommended_amount_brl != null && (
                <div>
                  <span className="text-gray-500">Aporte sugerido: </span>
                  <span className="font-medium">R$ {fmt(row.recommended_amount_brl)}</span>
                </div>
              )}
              {row.target_upside_pct != null && (
                <div>
                  <span className="text-gray-500">Upside alvo: </span>
                  <span className="font-medium">{fmt(row.target_upside_pct)}%</span>
                </div>
              )}
            </div>
          )}
          {row.telegram_message && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                Mensagem Telegram
              </p>
              <pre className="bg-gray-50 rounded p-3 font-mono text-xs text-gray-700 whitespace-pre-wrap border border-gray-200 overflow-x-auto">
                {row.telegram_message}
              </pre>
            </div>
          )}
        </div>
      </td>
    </tr>
  );
}

function OpportunityTableRow({
  row,
  expanded,
  onToggle,
}: {
  row: OpportunityRow;
  expanded: boolean;
  onToggle: () => void;
}) {
  const dropDisplay =
    row.asset_type === "renda_fixa"
      ? row.cause_explanation ?? "—"
      : `${fmt(row.drop_pct)}%`;

  const priceDisplay =
    row.currency === "USD"
      ? `US$ ${fmt(row.current_price)}`
      : `R$ ${fmt(row.current_price)}`;

  return (
    <>
      <tr
        onClick={onToggle}
        className="border-b border-gray-100 hover:bg-gray-50 transition-colors cursor-pointer"
      >
        <td className="py-3 px-4 text-xs text-gray-500 tabular-nums whitespace-nowrap">
          {fmtDate(row.detected_at)}
        </td>
        <td className="py-3 px-4">
          <span className="font-mono font-bold text-sm">{row.ticker}</span>
        </td>
        <td className="py-3 px-4 text-sm text-gray-600">
          {ASSET_TYPE_LABELS[row.asset_type] ?? row.asset_type}
        </td>
        <td className="py-3 px-4 text-sm">
          {row.asset_type === "renda_fixa" ? (
            <span className="text-gray-500 text-xs truncate max-w-[120px] block">
              {row.cause_explanation ?? "—"}
            </span>
          ) : (
            <span
              className={
                row.drop_pct != null && row.drop_pct < 0
                  ? "text-red-600 font-medium"
                  : "text-green-600 font-medium"
              }
            >
              {fmt(row.drop_pct)}%
            </span>
          )}
        </td>
        <td className="py-3 px-4 text-sm tabular-nums">{priceDisplay}</td>
        <td className="py-3 px-4">
          <RiskBadge level={row.risk_level} />
        </td>
        <td className="py-3 px-4 text-center text-base">
          {row.is_opportunity ? (
            <span className="text-green-600" title="É oportunidade">✓</span>
          ) : (
            <span className="text-red-500" title="Não é oportunidade">✗</span>
          )}
        </td>
        <td className="py-3 px-4 text-center">
          <FollowButton row={row} />
        </td>
      </tr>
      {expanded && <ExpandedDetail row={row} />}
    </>
  );
}

export function OpportunityDetectorContent() {
  const [assetTypeFilter, setAssetTypeFilter] = useState<string>("");
  const [daysFilter, setDaysFilter] = useState<number>(30);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data, isLoading, error } = useOpportunityHistory({
    asset_type: assetTypeFilter || undefined,
    days: daysFilter,
  });

  function clearFilters() {
    setAssetTypeFilter("");
    setDaysFilter(30);
  }

  function toggleExpanded(id: string) {
    setExpandedId((prev) => (prev === id ? null : id));
  }

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Tipo de Ativo
            </label>
            <select
              value={assetTypeFilter}
              onChange={(e) => setAssetTypeFilter(e.target.value)}
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            >
              <option value="">Todos</option>
              <option value="acao">Ações</option>
              <option value="crypto">Crypto</option>
              <option value="renda_fixa">Renda Fixa</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Período
            </label>
            <select
              value={daysFilter}
              onChange={(e) => setDaysFilter(Number(e.target.value))}
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            >
              <option value={7}>7 dias</option>
              <option value={30}>30 dias</option>
              <option value={90}>90 dias</option>
              <option value={365}>1 ano</option>
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={clearFilters}
              className="px-4 py-2 rounded-md text-sm text-gray-600 border border-gray-200 hover:bg-gray-50 transition-colors w-full sm:w-auto"
            >
              Limpar filtros
            </button>
          </div>
        </div>
      </div>

      {/* Status bar */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>
          {isLoading
            ? "Carregando..."
            : `${data?.total ?? 0} oportunidade${(data?.total ?? 0) !== 1 ? "s" : ""} encontrada${(data?.total ?? 0) !== 1 ? "s" : ""}`}
        </span>
        {data && data.results.length > 0 && (
          <span className="text-gray-400">
            Clique em uma linha para ver detalhes
          </span>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-100 px-4 py-3 text-sm text-red-600">
          {error instanceof Error ? error.message : "Erro ao carregar dados"}
        </div>
      )}

      {/* Table */}
      {!error && (
        <div className="rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600 whitespace-nowrap">
                    Data
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">
                    Ticker
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">
                    Tipo
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">
                    Queda
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">
                    Preço
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">
                    Risco
                  </th>
                  <th className="text-center py-3 px-4 text-xs font-semibold text-gray-600">
                    Oportun.?
                  </th>
                  <th className="text-center py-3 px-4 text-xs font-semibold text-gray-600">
                    Ação
                  </th>
                </tr>
              </thead>
              <tbody>
                {isLoading
                  ? Array.from({ length: 8 }).map((_, i) => (
                      <tr key={i} className="border-b border-gray-100">
                        {Array.from({ length: 8 }).map((_, j) => (
                          <td key={j} className="py-3 px-4">
                            <div className="h-4 bg-gray-100 rounded animate-pulse" />
                          </td>
                        ))}
                      </tr>
                    ))
                  : data?.results.map((row) => (
                      <OpportunityTableRow
                        key={row.id}
                        row={row}
                        expanded={expandedId === row.id}
                        onToggle={() => toggleExpanded(row.id)}
                      />
                    ))}
                {!isLoading && data && data.results.length === 0 && (
                  <tr>
                    <td
                      colSpan={8}
                      className="py-12 text-center text-sm text-gray-500"
                    >
                      Nenhuma oportunidade detectada no período selecionado
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
