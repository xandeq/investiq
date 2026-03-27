import { AppNav } from "@/components/AppNav";
import { SimuladorContent } from "@/features/simulador/components/SimuladorContent";

export const metadata = {
  title: "Simulador de Alocação — InvestIQ",
  description:
    "Simule a alocação ideal por perfil de risco com 3 cenários e ajuste IR ajustado.",
};

export default function SimuladorPage() {
  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-background">
        <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="mb-6">
            <h1 className="text-2xl font-bold">Simulador de Alocação</h1>
            <p className="text-muted-foreground mt-1">
              Informe o valor disponível, prazo e perfil de risco para receber uma sugestão de
              alocação com 3 cenários de retorno líquido de IR.
            </p>
          </div>
          <SimuladorContent />
        </div>
      </main>
    </>
  );
}
