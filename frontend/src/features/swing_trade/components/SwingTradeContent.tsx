"use client";
import { useState } from "react";
import { useSwingSignals } from "../hooks/useSwingSignals";
import { useSwingOperations } from "../hooks/useSwingOperations";
import { SignalsSection } from "./SignalsSection";
import { RadarSection } from "./RadarSection";
import { OperationsSection } from "./OperationsSection";

type Tab = "signals" | "radar" | "operations";

const TABS: { key: Tab; label: string }[] = [
  { key: "signals", label: "Sinais da Carteira" },
  { key: "radar", label: "Radar Swing" },
  { key: "operations", label: "Minhas Operações" },
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
  const [activeTab, setActiveTab] = useState<Tab>("signals");

  const signalsQuery = useSwingSignals();
  const operationsQuery = useSwingOperations();

  const portfolioSignals = signalsQuery.data?.portfolio_signals;
  const radarSignals = signalsQuery.data?.radar_signals;

  const signalsError = signalsQuery.error
    ? signalsQuery.error instanceof Error
      ? signalsQuery.error.message
      : "Erro ao carregar sinais"
    : null;

  return (
    <div className="space-y-4">
      {/* Tab header */}
      <div className="flex items-center justify-between border-b border-gray-200">
        <nav className="flex -mb-px">
          {TABS.map((tab) => {
            const active = tab.key === activeTab;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  active
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </nav>

        {signalsQuery.data?.generated_at && (
          <span className="text-[11px] text-gray-400">
            Atualizado em {formatGeneratedAt(signalsQuery.data.generated_at)}
          </span>
        )}
      </div>

      {/* Error banner (shared across signal-based tabs) */}
      {signalsError && activeTab !== "operations" && (
        <div className="rounded-lg bg-red-50 border border-red-100 px-4 py-3 text-sm text-red-600">
          {signalsError}
        </div>
      )}

      {/* Tab content */}
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
