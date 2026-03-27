import { AIContent } from "@/features/ai/components/AIContent";
import { AppNav } from "@/components/AppNav";

export default function AIPage() {
  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-background">
        <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
          <h1 className="text-2xl font-bold mb-6">Análise IA</h1>
          <AIContent />
        </div>
      </main>
    </>
  );
}
