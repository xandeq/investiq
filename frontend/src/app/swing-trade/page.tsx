import type { Metadata } from "next";
import { AppNav } from "@/components/AppNav";
import { SwingTradeContent } from "@/features/swing_trade/components/SwingTradeContent";

export const metadata: Metadata = {
  title: "Swing Trade — InvestIQ",
  description: "Sinais de swing trade da sua carteira, radar de oportunidades e registro de operações manuais.",
};

export default function SwingTradePage() {
  return (
    <main className="min-h-screen bg-background">
      <AppNav />
      <div className="container mx-auto px-4 py-8">
        <SwingTradeContent />
      </div>
    </main>
  );
}
