import type { Metadata } from "next";
import { AppNav } from "@/components/AppNav";
import { AcoesUniverseContent } from "@/features/acoes_screener/components/AcoesUniverseContent";

export const metadata: Metadata = {
  title: "Screener de Ações — InvestIQ",
  description:
    "Explore o universo completo de ações B3 — filtros por fundamentos",
};

export default function AcoesScreenerPage() {
  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-background">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="space-y-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Screener de Ações
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                Explore o universo completo de ações B3 — filtros por
                fundamentos
              </p>
            </div>
            <AcoesUniverseContent />
          </div>
        </div>
      </main>
    </>
  );
}
