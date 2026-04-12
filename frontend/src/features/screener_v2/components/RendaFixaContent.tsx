"use client";
import { useState, useMemo } from "react";
import { useFixedIncomeCatalog, useTesouroRates, useMacroRates } from "../hooks/useRendaFixa";
import type { FixedIncomeCatalogRow, TesouroRateRow, MacroRatesResponse } from "../types";

function fmt(val: string | null, decimals = 2, suffix = ""): string {
  if (val === null || val === undefined) return "—";
  const n = parseFloat(val);
  if (isNaN(n)) return "—";
  return n.toFixed(decimals) + suffix;
}

function annualizeRate(annualPct: number, holdingDays: number): number {
  return ((1 + annualPct / 100) ** (holdingDays / 365) - 1) * 100;
}

function typeBadge(type: string) {
  const colors: Record<string, string> = {
    CDB: "bg-blue-100 text-blue-700",
    LCI: "bg-green-100 text-green-700",
    LCA: "bg-emerald-100 text-emerald-700",
  };
  const cls = colors[type] ?? "bg-gray-100 text-gray-600";
  return <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${cls}`}>{type}</span>;
}

function IRBadge({ is_exempt, ir_rate_pct }: { is_exempt: boolean; ir_rate_pct: string }) {
  if (is_exempt) {
    return <span className="text-xs text-green-600 font-semibold">Isento</span>;
  }
  return <span className="text-xs text-gray-600">{fmt(ir_rate_pct)}%</span>;
}

function CatalogRow({ row, macroRates }: { row: FixedIncomeCatalogRow; macroRates?: MacroRatesResponse | null }) {
  const periods = ["6m", "1a", "2a", "5a"];
  const byPeriod = Object.fromEntries(row.ir_breakdowns.map((b) => [b.period_label, b]));

  const rateStr = row.max_rate_pct
    ? `${fmt(row.min_rate_pct)}% – ${fmt(row.max_rate_pct)}% ${row.indexer}`
    : `${fmt(row.min_rate_pct)}% ${row.indexer}`;

  const tenorStr = row.max_months
    ? `${row.min_months}–${row.max_months} meses`
    : `${row.min_months}+ meses`;

  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
      <td className="py-3 px-4">
        <div className="flex items-center gap-2">
          {typeBadge(row.instrument_type)}
          <span className="text-xs text-gray-500">{tenorStr}</span>
        </div>
        <div className="text-xs text-gray-500 mt-0.5">{row.label}</div>
      </td>
      <td className="py-3 px-4 text-sm font-semibold">{rateStr}</td>
      {periods.map((p) => {
        const bd = byPeriod[p];
        if (!bd) return <td key={p} className="py-3 px-4 text-gray-400 text-xs">—</td>;

        const cdiAnnual = macroRates?.cdi ? parseFloat(macroRates.cdi) : null;
        const ipcaAnnual = macroRates?.ipca ? parseFloat(macroRates.ipca) : null;
        const netVal = parseFloat(bd.net_pct);
        const cdiForPeriod = cdiAnnual !== null ? annualizeRate(cdiAnnual, bd.holding_days) : null;
        const ipcaForPeriod = ipcaAnnual !== null ? annualizeRate(ipcaAnnual, bd.holding_days) : null;
        const beatsCDI = cdiForPeriod !== null && netVal > cdiForPeriod;
        const beatsIPCA = ipcaForPeriod !== null && netVal > ipcaForPeriod;

        return (
          <td key={p} className="py-3 px-4">
            <div className={`text-sm font-semibold ${bd.is_exempt ? "text-green-600" : "text-gray-800"}`}>
              {fmt(bd.net_pct)}%
            </div>
            <div className="text-xs text-gray-400 flex items-center gap-1">
              IR: <IRBadge is_exempt={bd.is_exempt} ir_rate_pct={bd.ir_rate_pct} />
            </div>
            {(cdiForPeriod !== null || ipcaForPeriod !== null) && (
              <div className="text-xs mt-0.5">
                {beatsCDI ? (
                  <span className="text-green-600 font-medium">&#10003; CDI</span>
                ) : beatsIPCA ? (
                  <span className="text-amber-500 font-medium">~ IPCA</span>
                ) : (
                  <span className="text-gray-400">— abaixo</span>
                )}
              </div>
            )}
          </td>
        );
      })}
    </tr>
  );
}

function TesouroRow({ row }: { row: TesouroRateRow }) {
  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
      <td className="py-3 px-4">
        <div className="text-sm font-semibold">{row.tipo_titulo}</div>
      </td>
      <td className="py-3 px-4 text-sm">{row.vencimento}</td>
      <td className="py-3 px-4 text-sm font-bold text-blue-600">
        {row.taxa_indicativa ? `${fmt(row.taxa_indicativa, 2)}%` : "—"}
      </td>
      <td className="py-3 px-4 text-sm">
        {row.pu ? `R$ ${parseFloat(row.pu).toFixed(2)}` : "—"}
      </td>
      <td className="py-3 px-4 text-xs text-gray-400">{row.data_base}</td>
      <td className="py-3 px-4">
        <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">{row.source}</span>
      </td>
    </tr>
  );
}

export function RendaFixaContent() {
  type InstrumentType = "" | "Tesouro" | "CDB" | "LCI" | "LCA";
  const [typeFilter, setTypeFilter] = useState<InstrumentType>("");
  const [minMonths, setMinMonths] = useState("");
  const [selectedPrazo, setSelectedPrazo] = useState<"6m" | "1a" | "2a" | "5a">("1a");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const { data: catalog, isLoading: loadingCatalog, error: errorCatalog } = useFixedIncomeCatalog();
  const { data: tesouro, isLoading: loadingTesouro, error: errorTesouro } = useTesouroRates();
  const { data: macroRates } = useMacroRates();

  const filteredCatalog = useMemo(() => {
    let rows = catalog?.results ?? [];
    // Type filter for CDB/LCI/LCA (per D-02)
    if (typeFilter === "CDB" || typeFilter === "LCI" || typeFilter === "LCA") {
      rows = rows.filter(r => r.instrument_type === typeFilter);
    }
    // Min months filter (per D-03)
    if (minMonths) {
      const m = parseInt(minMonths, 10);
      if (!isNaN(m) && m > 0) {
        rows = rows.filter(r => r.min_months >= m);
      }
    }
    // Sort by net_pct for selectedPrazo (per D-05, D-06)
    rows = [...rows].sort((a, b) => {
      const aBd = a.ir_breakdowns.find(bd => bd.period_label === selectedPrazo);
      const bBd = b.ir_breakdowns.find(bd => bd.period_label === selectedPrazo);
      const aVal = aBd ? parseFloat(aBd.net_pct) : -Infinity;
      const bVal = bBd ? parseFloat(bBd.net_pct) : -Infinity;
      return sortDir === "desc" ? bVal - aVal : aVal - bVal;
    });
    return rows;
  }, [catalog, typeFilter, minMonths, selectedPrazo, sortDir]);

  const typeOptions: { label: string; value: InstrumentType }[] = [
    { label: "Todos", value: "" },
    { label: "Tesouro", value: "Tesouro" },
    { label: "CDB", value: "CDB" },
    { label: "LCI", value: "LCI" },
    { label: "LCA", value: "LCA" },
  ];

  return (
    <div className="space-y-8">
      {/* Disclaimer */}
      <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3">
        <p className="text-sm text-amber-800">
          <strong>Análise informativa</strong> — não constitui recomendação de investimento (CVM Res. 19/2021).
          As taxas exibidas são <strong>referências de mercado</strong>, não ofertas ao vivo.
        </p>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3">
        {typeOptions.map(({ label, value }) => (
          <button
            key={label}
            onClick={() => setTypeFilter(value)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium border transition-colors ${
              typeFilter === value
                ? "bg-blue-500 text-white border-blue-500"
                : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
            }`}
          >
            {label}
          </button>
        ))}

        {typeFilter !== "Tesouro" && (
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-500">Prazo min (meses):</label>
            <input
              type="number"
              value={minMonths}
              onChange={(e) => setMinMonths(e.target.value)}
              placeholder="ex: 12"
              className="w-20 px-2 py-1.5 rounded-md border border-gray-200 text-xs"
              min="0"
            />
          </div>
        )}

        {typeFilter !== "Tesouro" && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Ordenar por retorno:</span>
            {(["6m", "1a", "2a", "5a"] as const).map(p => (
              <button
                key={p}
                onClick={() => {
                  if (selectedPrazo === p) setSortDir(d => d === "desc" ? "asc" : "desc");
                  else { setSelectedPrazo(p); setSortDir("desc"); }
                }}
                className={`px-2 py-1 rounded text-xs font-medium border transition-colors ${
                  selectedPrazo === p
                    ? "bg-indigo-500 text-white border-indigo-500"
                    : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
                }`}
              >
                {p} {selectedPrazo === p ? (sortDir === "desc" ? "↓" : "↑") : ""}
              </button>
            ))}
          </div>
        )}

        {typeFilter !== "Tesouro" && (
          <span className="text-xs text-gray-400">{filteredCatalog.length} produto(s)</span>
        )}
      </div>

      {/* Tesouro Direto */}
      {(typeFilter === "" || typeFilter === "Tesouro") && (
        <section>
          <div className="mb-3">
            <h2 className="text-base font-bold">Tesouro Direto</h2>
            <p className="text-xs text-gray-500">Taxas indicativas atualizadas a cada 6h via ANBIMA</p>
          </div>

          {errorTesouro && (
            <div className="rounded-lg bg-red-50 border border-red-100 px-4 py-3 text-sm text-red-600">
              {errorTesouro instanceof Error ? errorTesouro.message : "Erro ao carregar Tesouro Direto"}
            </div>
          )}

          {!errorTesouro && (
            <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">Título</th>
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">Vencimento</th>
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">Taxa</th>
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">PU</th>
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">Data base</th>
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">Fonte</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loadingTesouro
                      ? Array.from({ length: 4 }).map((_, i) => (
                          <tr key={i} className="border-b border-gray-100">
                            {Array.from({ length: 6 }).map((_, j) => (
                              <td key={j} className="py-3 px-4">
                                <div className="h-4 bg-gray-100 rounded animate-pulse" />
                              </td>
                            ))}
                          </tr>
                        ))
                      : tesouro?.results.map((row) => (
                          <TesouroRow key={`${row.tipo_titulo}-${row.vencimento}`} row={row} />
                        ))}
                    {!loadingTesouro && (!tesouro?.results.length) && (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-sm text-gray-500">
                          Dados do Tesouro ainda não disponíveis — o pipeline roda a cada 6h
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>
      )}

      {/* CDB / LCI / LCA catalog */}
      {typeFilter !== "Tesouro" && (
        <section>
          <div className="mb-3">
            <h2 className="text-base font-bold">CDB · LCI · LCA</h2>
            <p className="text-xs text-gray-500">
              Faixas de referência de mercado com retorno líquido após IR regressivo.
              LCI e LCA são isentas de IR para PF.
            </p>
          </div>

          {errorCatalog && (
            <div className="rounded-lg bg-red-50 border border-red-100 px-4 py-3 text-sm text-red-600">
              {errorCatalog instanceof Error ? errorCatalog.message : "Erro ao carregar catálogo"}
            </div>
          )}

          {!errorCatalog && (
            <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">Produto / Prazo</th>
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">Taxa bruta</th>
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">6 meses</th>
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">1 ano</th>
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">2 anos</th>
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-600">5 anos</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loadingCatalog
                      ? Array.from({ length: 6 }).map((_, i) => (
                          <tr key={i} className="border-b border-gray-100">
                            {Array.from({ length: 6 }).map((_, j) => (
                              <td key={j} className="py-3 px-4">
                                <div className="h-4 bg-gray-100 rounded animate-pulse" />
                              </td>
                            ))}
                          </tr>
                        ))
                      : filteredCatalog.map((row, i) => (
                          <CatalogRow key={i} row={row} macroRates={macroRates} />
                        ))}
                    {!loadingCatalog && filteredCatalog.length === 0 && (catalog?.results?.length ?? 0) > 0 && (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-sm text-gray-500">
                          Nenhum produto encontrado com os filtros selecionados
                        </td>
                      </tr>
                    )}
                    {!loadingCatalog && !catalog?.results.length && (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-sm text-gray-500">
                          Catálogo não disponível
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>
      )}

      <p className="text-xs text-gray-400 text-center">
        Taxas de referência de mercado — não constituem oferta ao vivo. Consulte seu banco ou corretora para condições específicas.
      </p>
    </div>
  );
}
