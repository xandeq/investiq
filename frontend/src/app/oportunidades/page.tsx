import type { Metadata } from "next";
import { AppNav } from "@/components/AppNav";
import { OpportunitiesGrid } from "@/features/opportunities/components/OpportunitiesGrid";

export const metadata: Metadata = {
  title: "Oportunidades — InvestIQ",
  description:
    "Radar de oportunidades do dia com score IA, atualização automática a cada 5 minutos e análise de risco.",
};

export default function OportunidadesPage() {
  return (
    <main className="min-h-screen bg-background">
      <AppNav />
      <div className="container mx-auto px-4 py-8">
        <OpportunitiesGrid />
      </div>
    </main>
  );
}
