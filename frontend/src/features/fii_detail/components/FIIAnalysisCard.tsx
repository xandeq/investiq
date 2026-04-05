"use client";
import { AnalysisDisclaimer } from "@/features/analysis/components/AnalysisDisclaimer";

interface Props {
  onTrigger: () => void;
  isStarting: boolean;
  startError: string | null;
  status: string | undefined;
  narrative: string | null;
  disclaimer: string | undefined;
}

export function FIIAnalysisCard({
  onTrigger,
  isStarting,
  startError,
  status,
  narrative,
  disclaimer,
}: Props) {
  const isLoading = status === "pending" || status === "running" || isStarting;
  const isCompleted = status === "completed";
  const isFailed = status === "failed";

  return (
    <div className="border rounded-lg p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Analise IA do FII</h3>
        {!isCompleted && !isLoading && (
          <button
            onClick={onTrigger}
            disabled={isStarting}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 text-sm"
          >
            Gerar Analise IA
          </button>
        )}
      </div>

      {isLoading && (
        <div className="flex items-center gap-2 text-muted-foreground">
          <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full" />
          <span>Analisando...</span>
        </div>
      )}

      {startError && (
        <p className="text-sm text-destructive">{startError}</p>
      )}

      {isFailed && (
        <p className="text-sm text-destructive">Falha na analise. Tente novamente.</p>
      )}

      {isCompleted && narrative && (
        <>
          <AnalysisDisclaimer />
          <div className="prose prose-sm max-w-none">
            <p className="whitespace-pre-line">{narrative}</p>
          </div>
        </>
      )}
    </div>
  );
}
