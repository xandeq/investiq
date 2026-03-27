import { AppNav } from "@/components/AppNav";
import { PricingCard } from "@/features/billing/components/PricingCard";

const FREE_FEATURES = [
  { label: "Carteira de ações, FIIs e renda fixa", included: true },
  { label: "Até 50 transações", included: true },
  { label: "Até 3 importações por mês", included: true },
  { label: "Dashboard e P&L em tempo real", included: true },
  { label: "Análise de IA (DCF, valuation, macro)", included: false },
  { label: "Importações ilimitadas", included: false },
  { label: "Transações ilimitadas", included: false },
];

const PRO_FEATURES = [
  { label: "Carteira de ações, FIIs e renda fixa", included: true },
  { label: "Transações ilimitadas", included: true },
  { label: "Importações ilimitadas por mês", included: true },
  { label: "Dashboard e P&L em tempo real", included: true },
  { label: "Análise de IA — DCF e valuation por ativo", included: true },
  { label: "Análise macro do portfólio", included: true },
  { label: "Suporte prioritário", included: true },
];

export default function PlanosPage() {
  return (
    <main className="min-h-screen bg-background">
      <AppNav />

      <div className="container mx-auto px-4 py-16 max-w-4xl">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold text-foreground">Planos e preços</h1>
          <p className="mt-3 text-muted-foreground max-w-xl mx-auto">
            Comece gratuitamente e faça upgrade quando precisar de análises avançadas
            para maximizar seus investimentos.
          </p>
        </div>

        {/* Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <PricingCard
            name="Gratuito"
            price="R$ 0"
            priceNote="Para sempre"
            features={FREE_FEATURES}
          />
          <PricingCard
            name="Premium"
            price="R$ 29,90"
            priceNote="por mês · cancele quando quiser"
            features={PRO_FEATURES}
            highlighted
            ctaLabel="Assinar Premium"
          />
        </div>

        {/* Trust line */}
        <p className="mt-8 text-center text-sm text-muted-foreground">
          Pagamento processado com segurança pelo Stripe. Cancele a qualquer momento.
        </p>
      </div>
    </main>
  );
}
