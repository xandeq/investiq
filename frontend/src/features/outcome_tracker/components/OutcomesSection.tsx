"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { useOutcomes, useCreateOutcome, useCloseOutcome } from "../hooks/useOutcomes";
import { useOutcomeStats } from "../hooks/useOutcomeStats";
import { useExpectancy } from "../hooks/useExpectancy";
import { OutcomeStatsBar } from "./OutcomeStatsBar";
import { OutcomesTable } from "./OutcomesTable";
import { RegisterOutcomeForm } from "./RegisterOutcomeForm";
import { CloseOutcomeModal } from "./CloseOutcomeModal";
import { ExpectancyChart } from "./ExpectancyChart";
import type { OutcomeClosePayload, SignalOutcome } from "../types";

export function OutcomesSection() {
  const [closingOutcome, setClosingOutcome] = useState<SignalOutcome | null>(null);

  const outcomesQuery    = useOutcomes();
  const statsQuery       = useOutcomeStats();
  const expectancyQuery  = useExpectancy();
  const createMut        = useCreateOutcome();
  const closeMut         = useCloseOutcome();

  const outcomes = outcomesQuery.data?.outcomes ?? [];

  const handleClose = (id: string, payload: OutcomeClosePayload) => {
    closeMut.mutate(
      { id, payload },
      { onSuccess: () => setClosingOutcome(null) },
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
      className="space-y-3"
    >
      {/* Stats bar (only when there are closed outcomes) */}
      {(statsQuery.data?.total_closed ?? 0) > 0 && (
        <OutcomeStatsBar
          stats={statsQuery.data}
          isLoading={statsQuery.isLoading}
        />
      )}

      {/* Expectancy by pattern (only when there are patterns with data) */}
      {(expectancyQuery.data?.expectancy?.length ?? 0) > 0 && (
        <ExpectancyChart data={expectancyQuery.data!.expectancy} />
      )}

      {/* Error banner */}
      {outcomesQuery.isError && (
        <div className="rounded-lg bg-red-50 border border-red-100 px-4 py-3 text-sm text-red-600 flex items-center justify-between">
          <span>Erro ao carregar resultados.</span>
          <button
            onClick={() => outcomesQuery.refetch()}
            className="text-xs font-semibold underline"
          >
            Tentar novamente
          </button>
        </div>
      )}

      {/* Register form */}
      <RegisterOutcomeForm
        onSubmit={(payload) => createMut.mutate(payload)}
        isPending={createMut.isPending}
      />

      {/* Outcomes list */}
      <OutcomesTable
        outcomes={outcomes}
        isLoading={outcomesQuery.isLoading}
        isError={outcomesQuery.isError}
        onClose={(outcome) => setClosingOutcome(outcome)}
        closePending={closeMut.isPending}
      />

      {/* Close modal */}
      <CloseOutcomeModal
        outcome={closingOutcome}
        onClose={() => setClosingOutcome(null)}
        onConfirm={handleClose}
        isPending={closeMut.isPending}
      />
    </motion.div>
  );
}
