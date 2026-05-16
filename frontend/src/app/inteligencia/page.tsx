import type { Metadata } from "next";
import { AppNav } from "@/components/AppNav";
import { IntelligenceContent } from "@/features/intelligence/components/IntelligenceContent";

export const metadata: Metadata = {
  title: "Inteligência de Mercado — InvestIQ",
  description: "Mapa de sentimento da B3, menções no Reddit e feed de notícias com impacto financeiro.",
};

export default function InteligenciaPage() {
  return (
    <main className="min-h-screen bg-background">
      <AppNav />
      <div className="container mx-auto px-4 py-8">
        <IntelligenceContent />
      </div>
    </main>
  );
}
