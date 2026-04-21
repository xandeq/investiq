"use client";
import { useState } from "react";
import { useSwingSignals } from "../hooks/useSwingSignals";
import { useSwingOperations } from "../hooks/useSwingOperations";
import { useCopilot } from "../hooks/useCopilot";
import { SignalsSection } from "./SignalsSection";
import { RadarSection } from "./RadarSection";
import { OperationsSection } from "./OperationsSection";
import { CopilotSection } from "./CopilotSection";

type Tab = "copilot" | "signals" | "radar" | "operations";

const TABS: { key: Tab; label: string; icon: string }[] = [
  { key: "copilot",     label: "🤖 Copiloto",          icon: "" },
  { key: "signals",    label: "Sinais da Carteira",   icon: "" },
  { key: "radar",      label: "Radar Swing",           icon: "" },
  { key: "operations", label: "Minhas Operações",      icon: "" },
];

function formatGeneratedAt(iso: string | undefined | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return `${d.toLocaleDateString("pt-BR")} ${d.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  })}`;
}

export function SwingTradeContent() {
  const [activeTab, setActiveTab] = useState<Tab>("copilot");
  const [isRefreshing, setIsRefreshing] = useState(false);

  const signalsQuery  = useSwingSignals();
  const operationsQuery = useSwingOperations();
  const copilotQuery  = useCopilot();

  const portfolioSignals = signalsQuery.data?.portfolio_signals;
  const radarSignals     = signalsQuery.data?.radar_signals;

  const signalsError = signalsQuery.error
    ? signalsQuery.error instanceof Error
      ? signalsQuery.error.message
      : "Erro ao carregar sinais"
    : null;

  const handleRefreshCopilot = async () => {
    setIsRefreshing(true);
    try {
      await copilotQuery.refresh();
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleCreateFromCopilot = (payload: {
    ticker: string;
    entry_price: number;
    stop_price: number;
    target_price: number;
    notes: string;
    quantity: number;
  }) => {
    operationsQuery.createOp({
      ticker: payload.ticker,
      quantity: payload.quantity,
      entry_price: payload.entry_price,
      entry_date: new Date().toISOString(),
      target_price: payload.target_price,
      stop_price: payload.stop_price,
      notes: payload.notes,
    });
    // Switch to operations tab so user sees the new entry
    setActiveTab("operations");
  };

  return (
    <div className="space-y-4">
      {/* Page title */}
      <div className="mb-2">
        <h1 className="text-2xl font-bold text-gray-900">Swing Trade</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Copiloto analisa o mercado e entrega decisões prontas — você dá o último clique.
        </p>
      </div>

      {/* Tab header */}
      <div className="flex items-center justify-between border-b border-gray-200">
        <nav className="flex -mb-px overflow-x-auto">
          {TABS.map((tab) => {
            const active = tab.key === activeTab;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  active
                    ? tab.key === "copilot"
                      ? "border-blue-600 text-blue-600"
                      : "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </nav>

        {signalsQuery.data?.generated_at && activeTab !== "copilot" && (
          <span className="text-[11px] text-gray-400 shrink-0 ml-2">
            Atualizado em {formatGeneratedAt(signalsQuery.data.generated_at)}
          </span>
        )}
      </div>

      {/* Error banner (shared across signal-based tabs) */}
      {signalsError && activeTab !== "operations" && activeTab !== "copilot" && (
        <div className="rounded-lg bg-red-50 border border-red-100 px-4 py-3 text-sm text-red-600">
          {signalsError}
        </div>
      )}

      {/* Tab content */}
      {activeTab === "copilot" && (
        <CopilotSection
          swingPicks={copilotQuery.data?.swing_picks ?? []}
          dividendPlays={copilotQuery.data?.dividend_plays ?? []}
          universeScanned={copilotQuery.data?.universe_scanned ?? 0}
          fromCache={copilotQuery.data?.from_cache ?? false}
          isLoading={copilotQuery.isLoading}
          error={copilotQuery.data?.error ?? (copilotQuery.error instanceof Error ? copilotQuery.error.message : null)}
          onCreateOperation={handleCreateFromCopilot}
          onRefresh={handleRefreshCopilot}
          isRefreshing={isRefreshing}
        />
      )}

      {activeTab === "signals" && (
        <SignalsSection
          signals={portfolioSignals}
          isLoading={signalsQuery.isLoading}
        />
      )}

      {activeTab === "radar" && (
        <RadarSection
          signals={radarSignals}
          isLoading={signalsQuery.isLoading}
        />
      )}

      {activeTab === "operations" && (
        <OperationsSection
          data={operationsQuery.operations}
          isLoading={operationsQuery.isLoading}
          onCreate={(payload) => operationsQuery.createOp(payload)}
          onClose={(id, exit_price) =>
            operationsQuery.closeOp({ id, payload: { exit_price } })
          }
          onDelete={(id) => operationsQuery.deleteOp(id)}
          createPending={operationsQuery.createOpPending}
          closePending={false}
          deletePending={operationsQuery.deleteOpPending}
        />
      )}
    </div>
  );
}

export default SwingTradeContent;
