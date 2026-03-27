import { AppNav } from "@/components/AppNav";
import { ScreenerContent } from "@/features/screener/components/ScreenerContent";

export default function ScreenerPage() {
  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-background">
        <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
          <h1 className="text-2xl font-bold mb-2">Screener de Ações</h1>
          <p className="text-muted-foreground mb-8">
            Seleção inteligente das melhores ações da B3 com metodologia Goldman Sachs
          </p>
          <ScreenerContent />
        </div>
      </main>
    </>
  );
}
