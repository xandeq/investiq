import type { Metadata } from "next";
import { FIIDetailContent } from "./FIIDetailContent";

interface PageProps {
  params: Promise<{ ticker: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { ticker } = await params;
  return {
    title: `${ticker.toUpperCase()} - FII Analise | InvestIQ`,
  };
}

export default async function FIIPage({ params }: PageProps) {
  const { ticker } = await params;
  return <FIIDetailContent ticker={ticker.toUpperCase()} />;
}
