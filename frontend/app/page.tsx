import type { Metadata } from "next";
import { LandingPage } from "@/components/landing/LandingPage";

export const metadata: Metadata = {
  title: "InvestIQ — Inteligência para seus investimentos",
  description:
    "Carteira completa, análise de IA, screener de ações e FIIs — tudo em um lugar. Gratuito para começar. Plataforma brasileira de gestão de investimentos.",
  openGraph: {
    title: "InvestIQ — Inteligência para seus investimentos",
    description:
      "Carteira completa, análise de IA, screener de ações e FIIs. Gratuito para começar.",
    type: "website",
  },
};

export default function Page() {
  return <LandingPage />;
}
