"use client";

interface Narrative {
  type: string;
  text: string;
}

interface Props {
  narratives: Narrative[];
}

const typeLabels: Record<string, string> = {
  dcf: "Valuation DCF",
  earnings: "Lucros e Qualidade",
  dividend: "Dividendos",
  sector: "Comparação Setorial",
};

export function NarrativeSection({ narratives }: Props) {
  if (narratives.length === 0) return null;

  return (
    <div className="rounded-xl border bg-card p-6 space-y-4">
      <h3 className="text-lg font-semibold">Resumo da Análise</h3>
      <div className="space-y-4">
        {narratives.map(({ type, text }) => (
          <div key={type}>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">
              {typeLabels[type] ?? type}
            </p>
            <p className="text-sm whitespace-pre-line">{text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
