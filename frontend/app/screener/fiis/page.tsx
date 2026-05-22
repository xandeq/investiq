import { Suspense } from "react";
import { AppNav } from "@/components/AppNav";
import { FIIScreenerContent } from "@/features/screener_v2/components/FIIScreenerContent";

export default function FIIScreenerPage() {
  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-background">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="mb-6">
            <h1 className="text-2xl font-bold">Screener de FIIs</h1>
            <p className="text-muted-foreground mt-1">
              Filtre fundos imobiliários por segmento, DY, P/VP, vacância e cotistas — snapshot diário + metadados CVM
            </p>
          </div>
          <Suspense fallback={<div className="h-96 rounded-lg border border-zinc-200 bg-zinc-50 animate-pulse" />}>
            <FIIScreenerContent />
          </Suspense>
        </div>
      </main>
    </>
  );
}
