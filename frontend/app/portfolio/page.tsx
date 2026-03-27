import { PortfolioContent } from "@/features/portfolio/components/PortfolioContent";
import { AppNav } from "@/components/AppNav";

export default function PortfolioPage() {
  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-background">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <h1 className="text-2xl font-bold mb-6">Carteira e Análise</h1>
          <PortfolioContent />
        </div>
      </main>
    </>
  );
}
