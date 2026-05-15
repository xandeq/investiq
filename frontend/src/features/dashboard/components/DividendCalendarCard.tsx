"use client";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { formatBRL } from "@/lib/formatters";

// ─── Types ────────────────────────────────────────────────────────────────────

interface DividendEvent {
  ticker: string;
  asset_class: string;
  payment_date: string;    // "YYYY-MM-DD" or ""
  ex_date: string;         // "YYYY-MM-DD" or ""
  rate_per_share: string;  // Decimal as string, e.g. "1.25"
  quantity: string;        // Decimal as string
  estimated_income: string; // Decimal as string
  label: string;           // "Dividendo", "JCP", "Rendimento"
}

interface DividendCalendarResponse {
  events: DividendEvent[];
  data_available: boolean;
}

// ─── Date helpers ─────────────────────────────────────────────────────────────

function formatDisplayDate(dateStr: string): string {
  if (!dateStr) return "—";
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
  });
}

function isUrgent(dateStr: string): boolean {
  if (!dateStr) return false;
  const days = (new Date(dateStr).getTime() - Date.now()) / 86400000;
  return days >= 0 && days <= 14;
}

// ─── Label pill ───────────────────────────────────────────────────────────────

const LABEL_STYLES: Record<string, string> = {
  Dividendo: "bg-blue-100 text-blue-700",
  JCP: "bg-purple-100 text-purple-700",
  Rendimento: "bg-green-100 text-green-700",
};

function LabelPill({ label }: { label: string }) {
  const style = LABEL_STYLES[label] ?? "bg-gray-100 text-gray-600";
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold leading-tight ${style}`}
    >
      {label}
    </span>
  );
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function SkeletonRows() {
  return (
    <div className="space-y-2">
      {[1, 2, 3].map((n) => (
        <div key={n} className="h-10 rounded-lg bg-gray-100 animate-pulse" />
      ))}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function DividendCalendarCard() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard", "dividend-calendar"],
    queryFn: () => apiClient<DividendCalendarResponse>("/dashboard/dividend-calendar"),
    staleTime: 30 * 60 * 1000,
  });

  return (
    <div className="rounded-xl border border-border bg-white px-5 py-4 shadow-sm">
      <h2 className="mb-4 text-sm font-bold uppercase tracking-wider text-muted-foreground">
        Calendário de Dividendos — próximos 90 dias
      </h2>

      {isLoading && <SkeletonRows />}

      {!isLoading && data && !data.data_available && (
        <p className="py-4 text-center text-sm text-muted-foreground">
          Nenhum dividendo previsto para os próximos 90 dias
        </p>
      )}

      {!isLoading && data && data.data_available && data.events.length === 0 && (
        <p className="py-4 text-center text-sm text-muted-foreground">
          Nenhum dividendo previsto para os próximos 90 dias
        </p>
      )}

      {!isLoading && data && data.data_available && data.events.length > 0 && (() => {
        const events = data.events.slice(0, 20);
        const totalIncome = data.events.reduce(
          (sum, e) => sum + parseFloat(e.estimated_income || "0"),
          0
        );

        return (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  <th className="pb-2 pr-4 text-left">Ticker</th>
                  <th className="pb-2 pr-4 text-left">Tipo</th>
                  <th className="pb-2 pr-4 text-left">Data Ex</th>
                  <th className="pb-2 pr-4 text-left">Pagamento</th>
                  <th className="pb-2 pr-4 text-right">R$/cota</th>
                  <th className="pb-2 text-right">Estimado</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event, idx) => {
                  const urgent = isUrgent(event.payment_date);
                  return (
                    <tr
                      key={`${event.ticker}-${event.ex_date}-${idx}`}
                      className="border-b border-border/50 last:border-0 hover:bg-gray-50 transition-colors"
                    >
                      <td className="py-2.5 pr-4 font-bold text-foreground">
                        {event.ticker}
                      </td>
                      <td className="py-2.5 pr-4">
                        <LabelPill label={event.label} />
                      </td>
                      <td className="py-2.5 pr-4 text-muted-foreground">
                        {formatDisplayDate(event.ex_date)}
                      </td>
                      <td
                        className={`py-2.5 pr-4 ${
                          urgent
                            ? "font-bold text-amber-600"
                            : "text-muted-foreground"
                        }`}
                      >
                        {formatDisplayDate(event.payment_date)}
                        {urgent && (
                          <span
                            className="ml-1.5 inline-block rounded-full bg-amber-100 px-1.5 py-0.5 text-xs font-semibold text-amber-700"
                            title="Pagamento em até 14 dias"
                          >
                            Em breve
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 pr-4 text-right text-muted-foreground">
                        {formatBRL(event.rate_per_share)}
                      </td>
                      <td className="py-2.5 text-right font-medium text-green-600">
                        {formatBRL(event.estimated_income)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr className="border-t-2 border-border">
                  <td
                    colSpan={5}
                    className="pt-3 pr-4 text-right text-xs font-bold uppercase tracking-wider text-muted-foreground"
                  >
                    Total estimado no período
                  </td>
                  <td className="pt-3 text-right text-base font-extrabold text-green-600">
                    {formatBRL(totalIncome)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        );
      })()}
    </div>
  );
}
