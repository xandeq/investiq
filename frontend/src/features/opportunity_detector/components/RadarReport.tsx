"use client";
import type {
  RadarReport,
  RadarAcaoItem,
  RadarFiiItem,
  RadarCryptoItem,
  RadarRendaFixaItem,
  RadarMacro,
} from "../types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmt(n: number | null | undefined, decimals = 2, prefix = ""): string {
  if (n == null) return "—";
  return (
    prefix +
    n.toLocaleString("pt-BR", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    })
  );
}

function fmtPrice(n: number | null | undefined, currency = "R$"): string {
  if (n == null) return "—";
  if (n >= 1000) {
    return `${currency} ${(n / 1000).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}k`;
  }
  return `${currency} ${n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function DiscountBadge({ pct }: { pct: number }) {
  const abs = Math.abs(pct);
  let cls = "bg-gray-100 text-gray-600";
  if (abs >= 25) cls = "bg-red-100 text-red-700 font-bold";
  else if (abs >= 15) cls = "bg-orange-100 text-orange-700 font-semibold";
  else if (abs >= 8) cls = "bg-yellow-100 text-yellow-700";
  else if (pct < 0) cls = "bg-blue-50 text-blue-600";

  return (
    <span className={`text-xs px-2 py-0.5 rounded-full whitespace-nowrap ${cls}`}>
      {pct >= 0 ? "+" : ""}{fmt(pct, 1)}%
    </span>
  );
}

function SectionHeader({
  icon,
  title,
  subtitle,
}: {
  icon: string;
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <span className="text-xl">{icon}</span>
      <div>
        <h3 className="text-sm font-bold text-gray-800">{title}</h3>
        {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Macro bar
// ---------------------------------------------------------------------------

function MacroBar({ macro }: { macro: RadarMacro }) {
  return (
    <div className="flex flex-wrap gap-4 bg-gray-900 text-white rounded-lg px-4 py-3 text-xs mb-4">
      <div>
        <span className="text-gray-400">SELIC </span>
        <span className="font-bold text-emerald-400">{fmt(macro.selic, 2)}% a.a.</span>
      </div>
      <div>
        <span className="text-gray-400">CDI </span>
        <span className="font-bold text-emerald-400">{fmt(macro.cdi, 2)}% a.a.</span>
      </div>
      <div>
        <span className="text-gray-400">IPCA </span>
        <span className="font-bold">{fmt(macro.ipca, 2)}%</span>
      </div>
      <div>
        <span className="text-gray-400">USD/BRL </span>
        <span className="font-bold">R$ {fmt(macro.ptax_usd, 4)}</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Ações section
// ---------------------------------------------------------------------------

function AcoesSection({ items }: { items: RadarAcaoItem[] }) {
  const sorted = [...items].sort((a, b) => a.discount_from_high_pct - b.discount_from_high_pct);

  return (
    <div>
      <SectionHeader
        icon="📈"
        title="Ações B3 — Desconto vs Máxima 52 Semanas"
        subtitle="Empresas sólidas do IBOV abaixo do topo histórico anual"
      />
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-200 text-left">
              <th className="pb-2 pr-3 text-gray-500 font-medium">Ticker</th>
              <th className="pb-2 pr-3 text-gray-500 font-medium">Setor</th>
              <th className="pb-2 pr-3 text-gray-500 font-medium text-right">Preço atual</th>
              <th className="pb-2 pr-3 text-gray-500 font-medium text-right">Máx 52s</th>
              <th className="pb-2 pr-3 text-gray-500 font-medium text-right">Desconto</th>
              <th className="pb-2 pr-3 text-gray-500 font-medium text-right">P/L</th>
              <th className="pb-2 text-gray-500 font-medium">Sinal</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((item) => (
              <tr key={item.ticker} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="py-2 pr-3 font-mono font-bold text-gray-900">{item.ticker}</td>
                <td className="py-2 pr-3 text-gray-500 whitespace-nowrap">{item.setor}</td>
                <td className="py-2 pr-3 text-right font-medium">{fmtPrice(item.current_price)}</td>
                <td className="py-2 pr-3 text-right text-gray-500">{fmtPrice(item.high_52w)}</td>
                <td className="py-2 pr-3 text-right">
                  <DiscountBadge pct={item.discount_from_high_pct} />
                </td>
                <td className="py-2 pr-3 text-right text-gray-600">
                  {item.pl != null ? `${fmt(item.pl, 1)}x` : "—"}
                </td>
                <td className="py-2 text-gray-600 text-xs max-w-[200px]">{item.signal}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// FIIs section
// ---------------------------------------------------------------------------

function FiisSection({ items }: { items: RadarFiiItem[] }) {
  const sorted = [...items].sort((a, b) => a.discount_from_high_pct - b.discount_from_high_pct);

  return (
    <div>
      <SectionHeader
        icon="🏢"
        title="Fundos Imobiliários — Desconto vs Máxima 52 Semanas"
        subtitle="FIIs de qualidade abaixo do topo anual + DY estimado"
      />
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-200 text-left">
              <th className="pb-2 pr-3 text-gray-500 font-medium">Ticker</th>
              <th className="pb-2 pr-3 text-gray-500 font-medium">Segmento</th>
              <th className="pb-2 pr-3 text-gray-500 font-medium text-right">Preço</th>
              <th className="pb-2 pr-3 text-gray-500 font-medium text-right">Máx 52s</th>
              <th className="pb-2 pr-3 text-gray-500 font-medium text-right">Desconto</th>
              <th className="pb-2 pr-3 text-gray-500 font-medium text-right">DY anual</th>
              <th className="pb-2 text-gray-500 font-medium">Sinal</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((item) => (
              <tr key={item.ticker} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="py-2 pr-3 font-mono font-bold text-gray-900">{item.ticker}</td>
                <td className="py-2 pr-3 text-gray-500 whitespace-nowrap">{item.segmento}</td>
                <td className="py-2 pr-3 text-right font-medium">{fmtPrice(item.current_price)}</td>
                <td className="py-2 pr-3 text-right text-gray-500">{fmtPrice(item.high_52w)}</td>
                <td className="py-2 pr-3 text-right">
                  <DiscountBadge pct={item.discount_from_high_pct} />
                </td>
                <td className="py-2 pr-3 text-right font-medium text-emerald-700">
                  {item.dy_anual_pct != null ? `${fmt(item.dy_anual_pct, 1)}%` : "—"}
                </td>
                <td className="py-2 text-gray-600 text-xs max-w-[200px]">{item.signal}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Crypto section
// ---------------------------------------------------------------------------

function CryptoSection({ items }: { items: RadarCryptoItem[] }) {
  return (
    <div>
      <SectionHeader
        icon="₿"
        title="Criptomoedas — Desconto vs ATH Histórico"
        subtitle="Distância do topo absoluto histórico em BRL"
      />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {items.map((item) => (
          <div key={item.symbol} className="rounded-lg border border-gray-200 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-bold text-gray-900">{item.name}</p>
                <p className="text-xs text-gray-500">ATH em {item.ath_date}</p>
              </div>
              <DiscountBadge pct={item.discount_from_ath_pct} />
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <p className="text-gray-400">Preço atual</p>
                <p className="font-bold text-gray-900">
                  R$ {item.current_price_brl.toLocaleString("pt-BR")}
                </p>
                {item.current_price_usd && (
                  <p className="text-gray-400">US$ {item.current_price_usd.toLocaleString("pt-BR")}</p>
                )}
              </div>
              <div>
                <p className="text-gray-400">ATH histórico</p>
                <p className="font-semibold text-gray-700">
                  R$ {item.ath_brl.toLocaleString("pt-BR")}
                </p>
                {item.ath_usd && (
                  <p className="text-gray-400">US$ {item.ath_usd.toLocaleString("pt-BR")}</p>
                )}
              </div>
            </div>

            <div className="flex gap-3 text-xs">
              {item.change_24h_pct != null && (
                <div>
                  <span className="text-gray-400">24h </span>
                  <span className={item.change_24h_pct >= 0 ? "text-emerald-600" : "text-red-600"}>
                    {item.change_24h_pct >= 0 ? "+" : ""}{fmt(item.change_24h_pct, 1)}%
                  </span>
                </div>
              )}
              {item.change_30d_pct != null && (
                <div>
                  <span className="text-gray-400">30d </span>
                  <span className={item.change_30d_pct >= 0 ? "text-emerald-600" : "text-red-600"}>
                    {item.change_30d_pct >= 0 ? "+" : ""}{fmt(item.change_30d_pct, 1)}%
                  </span>
                </div>
              )}
              {item.change_1y_pct != null && (
                <div>
                  <span className="text-gray-400">1a </span>
                  <span className={item.change_1y_pct >= 0 ? "text-emerald-600" : "text-red-600"}>
                    {item.change_1y_pct >= 0 ? "+" : ""}{fmt(item.change_1y_pct, 1)}%
                  </span>
                </div>
              )}
            </div>

            <p className="text-xs text-gray-600 border-t border-gray-100 pt-2">{item.signal}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Renda Fixa section
// ---------------------------------------------------------------------------

function RendaFixaSection({ items }: { items: RadarRendaFixaItem[] }) {
  const sorted = [...items].sort((a, b) => b.taxa_pct - a.taxa_pct);

  return (
    <div>
      <SectionHeader
        icon="🏦"
        title="Renda Fixa — Tesouro Direto"
        subtitle="Melhores taxas disponíveis — taxas historicamente altas com Selic a 14,65%"
      />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {sorted.map((item, i) => (
          <div key={i} className="rounded-lg border border-gray-200 p-3 space-y-1">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-gray-800 leading-tight">{item.tipo}</p>
              <span className="text-sm font-bold text-emerald-700">{fmt(item.taxa_pct, 2)}%</span>
            </div>
            {item.vencimento && (
              <p className="text-xs text-gray-400">Venc. {item.vencimento}</p>
            )}
            <p className="text-xs text-gray-600">{item.signal}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function RadarSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-10 bg-gray-100 rounded-lg" />
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="space-y-3">
          <div className="h-5 bg-gray-100 rounded w-1/3" />
          <div className="space-y-2">
            {[1, 2, 3].map((j) => (
              <div key={j} className="h-8 bg-gray-50 rounded" />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface RadarReportViewProps {
  report: RadarReport | null;
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export function RadarReportView({
  report,
  isLoading,
  error,
  onRefresh,
}: RadarReportViewProps) {
  if (isLoading) {
    return (
      <div className="rounded-lg border border-blue-100 bg-blue-50 p-6">
        <div className="flex items-center gap-3 mb-4">
          <svg className="animate-spin h-5 w-5 text-blue-600" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
          </svg>
          <div>
            <p className="text-sm font-medium text-blue-800">Analisando mercado...</p>
            <p className="text-xs text-blue-600">
              Consultando ações, FIIs, crypto e renda fixa (~30–60 segundos)
            </p>
          </div>
        </div>
        <RadarSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-600">
        {error}
        <button
          onClick={onRefresh}
          className="ml-3 underline text-red-700 hover:text-red-900"
        >
          Tentar novamente
        </button>
      </div>
    );
  }

  if (!report) return null;

  const generatedAt = new Date(report.generated_at).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm p-5 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-gray-900">Radar de Oportunidades</h2>
          <p className="text-xs text-gray-400">
            Gerado em {generatedAt} · Cache {report.cache_expires_in_minutes}min
          </p>
        </div>
        <button
          onClick={onRefresh}
          className="text-xs text-blue-600 hover:text-blue-800 border border-blue-200 rounded-md px-3 py-1.5 transition-colors hover:bg-blue-50"
        >
          ↻ Atualizar
        </button>
      </div>

      {/* Disclaimer */}
      <p className="text-xs text-gray-400 bg-gray-50 rounded px-3 py-2">
        ⚠️ Análise informativa — não constitui recomendação de investimento (CVM Res. 19/2021).
        Desconto calculado vs máxima de 52 semanas (ações/FIIs) ou ATH histórico (crypto).
      </p>

      {/* Macro */}
      <MacroBar macro={report.macro} />

      {/* Divider */}
      <div className="border-t border-gray-100" />

      {/* Ações */}
      {report.acoes.length > 0 && <AcoesSection items={report.acoes} />}

      <div className="border-t border-gray-100" />

      {/* FIIs */}
      {report.fiis.length > 0 && <FiisSection items={report.fiis} />}

      <div className="border-t border-gray-100" />

      {/* Crypto */}
      {report.crypto.length > 0 && <CryptoSection items={report.crypto} />}

      <div className="border-t border-gray-100" />

      {/* Renda Fixa */}
      {report.renda_fixa.length > 0 && <RendaFixaSection items={report.renda_fixa} />}
    </div>
  );
}
