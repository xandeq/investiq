import type { Metadata } from "next";
import { AppNav } from "@/components/AppNav";
import { FIIScoredScreenerContent } from "@/features/fii_screener/components/FIIScoredScreenerContent";

export const metadata: Metadata = {
  title: "FII Screener — InvestIQ",
  description: "Ranking de FIIs por score composto: DY, P/VP e liquidez",
};

export default function FIIScreenerPage() {
  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-background">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="space-y-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">FII Screener</h1>
              <p className="text-sm text-gray-500 mt-1">
                Ranking por score composto (DY 12m + P/VP + Liquidez)
              </p>
            </div>
            <FIIScoredScreenerContent />
          </div>
        </div>
      </main>
    </>
  );
}
