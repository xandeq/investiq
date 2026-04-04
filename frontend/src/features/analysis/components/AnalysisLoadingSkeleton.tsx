interface Props {
  title: string;
}

export function AnalysisLoadingSkeleton({ title }: Props) {
  return (
    <div className="rounded-xl border bg-card p-6">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <div className="flex items-center gap-3">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        <span className="text-sm text-muted-foreground">Calculando...</span>
      </div>
    </div>
  );
}
