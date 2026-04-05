import type { Metadata } from "next";
import { AppNav } from "@/components/AppNav";
import { OpportunityDetectorContent } from "@/features/opportunity_detector/components/OpportunityDetectorContent";

export const metadata: Metadata = {
  title: "Oportunidades Detectadas — InvestIQ",
  description: "Histórico de oportunidades detectadas pelo scanner automático",
};

export default function OpportunityDetectorPage() {
  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-background">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="space-y-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Oportunidades Detectadas
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                Histórico de oportunidades identificadas pelo scanner automático
              </p>
            </div>
            <OpportunityDetectorContent />
          </div>
        </div>
      </main>
    </>
  );
}
