import type { Metadata } from "next";
import { StockDetailContent } from "./StockDetailContent";

interface PageProps {
  params: Promise<{ ticker: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { ticker } = await params;
  return {
    title: `${ticker.toUpperCase()} - Análise | InvestIQ`,
  };
}

export default async function StockPage({ params }: PageProps) {
  const { ticker } = await params;
  return <StockDetailContent ticker={ticker.toUpperCase()} />;
}
