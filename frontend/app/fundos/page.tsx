import { AppNav } from "@/components/AppNav";
import { FundsContent } from "@/features/funds/components/FundsContent";

export default function FundosPage() {
  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-background">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <h1 className="text-2xl font-bold mb-2">Fundos de Investimento</h1>
          <p className="text-sm text-zinc-500 mb-6">
            Consulte fundos CVM e acompanhe suas posições em cotas.
          </p>
          <FundsContent />
        </div>
      </main>
    </>
  );
}
