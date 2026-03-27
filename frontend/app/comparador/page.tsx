import { AppNav } from "@/components/AppNav";
import { ComparadorContent } from "@/features/comparador/components/ComparadorContent";

export default function ComparadorPage() {
  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-background">
        <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="mb-6">
            <h1 className="text-2xl font-bold">Comparador RF vs RV</h1>
            <p className="text-muted-foreground mt-1">
              Compare retorno líquido após IR entre renda fixa e renda variável por prazo
            </p>
          </div>
          <ComparadorContent />
        </div>
      </main>
    </>
  );
}
