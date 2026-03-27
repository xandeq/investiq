import { AppNav } from "@/components/AppNav";
import { AdvisorContent } from "@/features/ai/components/AdvisorContent";

export default function AdvisorPage() {
  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-background">
        <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
          <h1 className="text-2xl font-bold mb-2">AI Advisor</h1>
          <p className="text-muted-foreground mb-8">Análise completa da sua carteira com inteligência artificial</p>
          <AdvisorContent />
        </div>
      </main>
    </>
  );
}
