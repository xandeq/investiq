import { AppNav } from "@/components/AppNav";
import { RendaFixaContent } from "@/features/screener_v2/components/RendaFixaContent";

export default function RendaFixaPage() {
  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-background">
        <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="mb-6">
            <h1 className="text-2xl font-bold">Renda Fixa</h1>
            <p className="text-muted-foreground mt-1">
              Tesouro Direto e taxas de referência de CDB · LCI · LCA com retorno líquido após IR
            </p>
          </div>
          <RendaFixaContent />
        </div>
      </main>
    </>
  );
}
