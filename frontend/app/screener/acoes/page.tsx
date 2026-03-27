import { AppNav } from "@/components/AppNav";
import { AcoesScreenerContent } from "@/features/screener_v2/components/AcoesScreenerContent";

export default function AcoesScreenerPage() {
  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-background">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="mb-6">
            <h1 className="text-2xl font-bold">Screener de Ações B3</h1>
            <p className="text-muted-foreground mt-1">
              Filtre ações por múltiplos critérios — dados do snapshot diário, sem chamadas externas por requisição
            </p>
          </div>
          <AcoesScreenerContent />
        </div>
      </main>
    </>
  );
}
