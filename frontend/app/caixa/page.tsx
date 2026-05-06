import { AppNav } from "@/components/AppNav";
import { CashParkingContent } from "@/features/cash_flow_advisor/components/CashParkingContent";

export const metadata = {
  title: "Caixa - InvestIQ",
  description: "Ranking determinístico para aplicar caixa parado com base no fluxo DIAX.",
};

export default function CaixaPage() {
  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-background">
        <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="mb-6">
            <h1 className="text-2xl font-bold">Caixa</h1>
            <p className="text-muted-foreground mt-1">
              Veja onde estacionar o dinheiro disponível até a próxima saída relevante.
            </p>
          </div>
          <CashParkingContent />
        </div>
      </main>
    </>
  );
}
