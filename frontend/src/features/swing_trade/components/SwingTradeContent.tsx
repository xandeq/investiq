"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Robot,
  ChartLineUp,
  Crosshair,
  Briefcase,
  ChartBar,
  Trophy,
  Sliders,
} from "@phosphor-icons/react";
import { useSwingSignals } from "../hooks/useSwingSignals";
import { useSwingOperations } from "../hooks/useSwingOperations";
import { useCopilot } from "../hooks/useCopilot";
import { SignalsSection } from "./SignalsSection";
import { RadarSection } from "./RadarSection";
import { OperationsSection } from "./OperationsSection";
import { CopilotSection } from "./CopilotSection";
import { StatsSection } from "./StatsSection";
import { OutcomesSection } from "../../outcome_tracker/components/OutcomesSection";
import { CalibrationSection } from "../../signal_engine/components/CalibrationSection";

type Tab = "copilot" | "signals" | "radar" | "operations" | "stats" | "resultados" | "calibracao";

const TABS: { key: Tab; label: string; Icon: React.ElementType }[] = [
  { key: "copilot",     label: "Copiloto",          Icon: Robot },
  { key: "signals",    label: "Sinais da Carteira", Icon: ChartLineUp },
  { key: "radar",      label: "Radar Swing",        Icon: Crosshair },
  { key: "operations", label: "Minhas Operações",   Icon: Briefcase },
  { key: "stats",      label: "Estatísticas",       Icon: ChartBar },
  { key: "resultados", label: "Resultados",         Icon: Trophy },
  { key: "calibracao", label: "Calibração",         Icon: Sliders },
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

  const signalsQuery    = useSwingSignals();
  const operationsQuery = useSwingOperations();
  const copilotQuery    = useCopilot();

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
    setActiveTab("operations");
  };

  return (
    <div className="space-y-4">
      {/* Page header */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="mb-2"
      >
        <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">Swing Trade</h1>
        <p className="text-sm text-zinc-500 mt-0.5">
          Copiloto analisa o mercado e entrega decisões prontas — você dá o último clique.
        </p>
      </motion.div>

      {/* Animated tab bar */}
      <div className="flex items-center justify-between border-b border-zinc-200">
        <nav className="flex -mb-px overflow-x-auto relative" aria-label="Navegação Swing Trade">
          {TABS.map((tab, i) => {
            const active = tab.key === activeTab;
            const { Icon } = tab;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`relative flex items-center gap-1.5 px-4 py-3 text-sm font-medium whitespace-nowrap active:scale-[0.97] transition-all duration-150 ${
                  active
                    ? "text-blue-600"
                    : "text-zinc-500 hover:text-zinc-700"
                }`}
                style={{ animationDelay: `${i * 40}ms` }}
              >
                <Icon
                  size={15}
                  weight={active ? "fill" : "regular"}
                  aria-hidden
                />
                {tab.label}

                {/* Animated underline indicator */}
                {active && (
                  <motion.span
                    layoutId="tab-indicator"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 rounded-full"
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  />
                )}
              </button>
            );
          })}
        </nav>

        {signalsQuery.data?.generated_at && activeTab !== "copilot" && (
          <span className="text-[11px] text-zinc-400 shrink-0 ml-2">
            Atualizado em {formatGeneratedAt(signalsQuery.data.generated_at)}
          </span>
        )}
      </div>

      {/* Error banner */}
      {signalsError && activeTab !== "operations" && activeTab !== "copilot" && (
        <div className="rounded-lg bg-red-50 border border-red-100 px-4 py-3 text-sm text-red-600">
          {signalsError}
        </div>
      )}

      {/* Tab content with fade-in */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
        >
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

          {activeTab === "stats" && <StatsSection />}

          {activeTab === "resultados" && <OutcomesSection />}

          {activeTab === "calibracao" && <CalibrationSection />}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

export default SwingTradeContent;
