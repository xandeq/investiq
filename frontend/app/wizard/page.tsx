import { AppNav } from "@/components/AppNav";
import { WizardContent } from "@/features/wizard/components/WizardContent";

export const metadata = {
  title: "Onde Investir — InvestIQ",
  description:
    "Receba uma recomendação de alocação personalizada por IA com base no seu perfil, prazo e valor disponível.",
};

export default function WizardPage() {
  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-background">
        <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="mb-6">
            <h1 className="text-2xl font-bold">Onde Investir</h1>
            <p className="text-muted-foreground mt-1">
              Informe o valor disponível, horizonte e perfil de risco para receber uma recomendação
              de alocação gerada por IA com contexto macro atualizado.
            </p>
          </div>
          <WizardContent />
        </div>
      </main>
    </>
  );
}
