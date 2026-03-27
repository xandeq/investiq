"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useSubscription } from "@/features/billing/hooks/useSubscription";

export default function SuccessPage() {
  const [stopPolling, setStopPolling] = useState(false);
  const { isPro, isLoading } = useSubscription({
    refetchInterval: stopPolling ? false : 2_000,
  });

  // Stop polling once plan is confirmed or after 30 s timeout
  useEffect(() => {
    if (isPro) setStopPolling(true);
  }, [isPro]);

  useEffect(() => {
    const t = setTimeout(() => setStopPolling(true), 30_000);
    return () => clearTimeout(t);
  }, []);

  if (!isLoading && isPro) {
    return (
      <main className="min-h-screen bg-background flex items-center justify-center px-4">
        <div className="text-center space-y-6 max-w-md">
          <div className="text-5xl">🎉</div>
          <h1 className="text-2xl font-bold text-foreground">
            Bem-vindo ao Premium!
          </h1>
          <p className="text-muted-foreground">
            Sua assinatura está ativa. Agora você tem acesso completo às análises
            de IA, importações ilimitadas e muito mais.
          </p>
          <Link
            href="/dashboard"
            className="inline-block rounded-md bg-primary text-primary-foreground px-6 py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            Ir para o Dashboard
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="text-center space-y-4 max-w-sm">
        <div className="h-10 w-10 rounded-full border-4 border-primary border-t-transparent animate-spin mx-auto" />
        <h1 className="text-xl font-semibold text-foreground">
          Confirmando seu pagamento…
        </h1>
        <p className="text-sm text-muted-foreground">
          Isso leva alguns segundos. Não feche esta página.
        </p>
        {stopPolling && !isPro && (
          <p className="text-sm text-muted-foreground mt-4">
            Demorou mais que o esperado.{" "}
            <Link href="/planos" className="underline text-primary">
              Voltar para planos
            </Link>
          </p>
        )}
      </div>
    </main>
  );
}
