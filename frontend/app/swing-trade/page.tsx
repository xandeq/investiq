import type { Metadata } from "next";
import { AppNav } from "@/components/AppNav";
import SwingTradeContent from "@/features/swing_trade/components/SwingTradeContent";

export const metadata: Metadata = {
  title: "Swing Trade — InvestIQ",
  description:
    "Sinais de swing trade da sua carteira, radar de oportunidades e registro de operações manuais.",
};

export default function SwingTradePage() {
  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-background">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="space-y-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Swing Trade</h1>
              <p className="text-sm text-gray-500 mt-1">
                Sinais da sua carteira, radar de descontos e registro de
                operações.
              </p>
            </div>
            <SwingTradeContent />
          </div>
        </div>
      </main>
    </>
  );
}
