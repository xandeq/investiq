import type { Metadata } from "next";
import Link from "next/link";
import { Check, X, BarChart2, BrainCircuit, ScanSearch, Landmark, Upload, Calculator, ArrowRight } from "lucide-react";
import { LandingNav } from "@/components/LandingNav";

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

// ─── Data ─────────────────────────────────────────────────────────────────────

const FEATURES = [
  {
    icon: BarChart2,
    title: "Carteira Completa",
    description:
      "Ações, FIIs, ETFs, renda fixa. Acompanhe P&L, custos médios e rentabilidade em tempo real.",
  },
  {
    icon: BrainCircuit,
    title: "IA de Investimentos",
    description:
      "Análise DCF, valuation por ativo e diagnóstico completo do portfólio com sugestões de realocação.",
    badge: "Premium",
  },
  {
    icon: ScanSearch,
    title: "Screener Avançado",
    description:
      "Filtre ações pelo método Goldman Sachs e FIIs por P/VP, DY e liquidez.",
  },
  {
    icon: Landmark,
    title: "Renda Fixa",
    description:
      "Compare Tesouro Direto, CDB, LCI e LCA. Simule cenários e encontre as melhores taxas.",
  },
  {
    icon: Upload,
    title: "Importação Automática",
    description:
      "Importe notas de corretagem em PDF/CSV. Suporte para todas as corretoras brasileiras.",
  },
  {
    icon: Calculator,
    title: "Helper de IR",
    description:
      "Calcule IRRF, apure ganhos e organize informações para a declaração do Imposto de Renda.",
  },
];

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

const STATS = [
  { value: "20+", label: "Ferramentas de análise" },
  { value: "B3", label: "Todas as corretoras" },
  { value: "Tempo real", label: "Dados de mercado" },
  { value: "14 dias", label: "Grátis Premium" },
];

// ─── Sub-components ────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  accent = false,
}: {
  label: string;
  value: string;
  sub: string;
  accent?: boolean;
}) {
  return (
    <div
      className={`rounded-xl px-5 py-4 flex flex-col gap-1 shadow-lg border ${
        accent
          ? "bg-blue-500/20 border-blue-500/30 text-white"
          : "bg-white/10 border-white/10 text-white"
      }`}
    >
      <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">{label}</span>
      <span className="text-2xl font-extrabold tracking-tight">{value}</span>
      <span className={`text-xs font-medium ${accent ? "text-blue-300" : "text-emerald-400"}`}>
        {sub}
      </span>
    </div>
  );
}

function FeatureCard({
  icon: Icon,
  title,
  description,
  badge,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  badge?: string;
}) {
  return (
    <div className="group bg-white rounded-xl border border-gray-200 p-6 hover:border-blue-200 hover:shadow-md transition-all duration-200">
      <div className="flex items-start justify-between mb-4">
        <div className="h-10 w-10 rounded-lg bg-blue-50 flex items-center justify-center group-hover:bg-blue-100 transition-colors">
          <Icon className="h-5 w-5 text-blue-500" strokeWidth={1.75} />
        </div>
        {badge && (
          <span className="text-[10px] font-bold uppercase tracking-widest bg-blue-500 text-white px-2 py-0.5 rounded-full">
            {badge}
          </span>
        )}
      </div>
      <h3 className="font-semibold text-gray-900 mb-1.5">{title}</h3>
      <p className="text-sm text-gray-500 leading-relaxed">{description}</p>
    </div>
  );
}

function PricingFeatureItem({
  label,
  included,
  highlighted,
}: {
  label: string;
  included: boolean;
  highlighted: boolean;
}) {
  return (
    <li className="flex items-start gap-3 text-sm">
      <span
        className={`mt-0.5 shrink-0 h-4 w-4 flex items-center justify-center rounded-full ${
          included
            ? highlighted
              ? "bg-blue-500 text-white"
              : "bg-emerald-500 text-white"
            : "bg-gray-300 text-gray-500"
        }`}
      >
        {included ? (
          <Check className="h-2.5 w-2.5" strokeWidth={3} />
        ) : (
          <X className="h-2.5 w-2.5" strokeWidth={3} />
        )}
      </span>
      <span
        className={
          included
            ? highlighted
              ? "text-gray-200"
              : "text-gray-800"
            : highlighted
            ? "text-gray-500"
            : "text-gray-400"
        }
      >
        {label}
      </span>
    </li>
  );
}

function LandingPricingCard({
  name,
  price,
  priceNote,
  features,
  highlighted,
  ctaHref,
  ctaLabel,
  badge,
}: {
  name: string;
  price: string;
  priceNote?: string;
  features: { label: string; included: boolean }[];
  highlighted?: boolean;
  ctaHref: string;
  ctaLabel: string;
  badge?: string;
}) {
  return (
    <div
      className={`relative rounded-2xl flex flex-col gap-6 p-8 transition-all duration-200 ${
        highlighted
          ? "bg-[#111827] text-white shadow-2xl scale-[1.02]"
          : "bg-gray-100 hover:bg-gray-50"
      }`}
    >
      {badge && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <span className="bg-blue-500 text-white text-xs font-bold uppercase tracking-widest px-4 py-1 rounded-full shadow-lg">
            {badge}
          </span>
        </div>
      )}
      <div>
        <p
          className={`text-xs font-bold uppercase tracking-wider ${
            highlighted ? "text-blue-400" : "text-gray-500"
          }`}
        >
          {name}
        </p>
        <p
          className={`mt-2 text-5xl font-extrabold tracking-tight ${
            highlighted ? "text-white" : "text-gray-900"
          }`}
        >
          {price}
        </p>
        {priceNote && (
          <p className={`mt-1 text-sm ${highlighted ? "text-gray-400" : "text-gray-500"}`}>
            {priceNote}
          </p>
        )}
      </div>

      <ul className="flex flex-col gap-3">
        {features.map((f) => (
          <PricingFeatureItem
            key={f.label}
            label={f.label}
            included={f.included}
            highlighted={!!highlighted}
          />
        ))}
      </ul>

      <div className="mt-auto">
        <Link
          href={ctaHref}
          className={`block w-full rounded-xl text-sm font-bold py-3.5 text-center transition-all duration-200 hover:scale-[1.02] ${
            highlighted
              ? "bg-blue-500 text-white hover:bg-blue-400"
              : "bg-[#111827] text-white hover:bg-gray-800"
          }`}
        >
          {ctaLabel}
        </Link>
      </div>
    </div>
  );
}

// ─── Sections ──────────────────────────────────────────────────────────────────

function HeroSection() {
  return (
    <section className="relative bg-[#111827] min-h-screen flex items-center overflow-hidden">
      {/* Subtle grid background */}
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
        }}
      />
      {/* Blue glow bottom-left */}
      <div className="absolute bottom-0 left-1/4 w-[600px] h-[400px] bg-blue-600/10 rounded-full blur-[120px] pointer-events-none" />

      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-24 lg:py-0 w-full">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left: copy */}
          <div className="flex flex-col gap-6">
            {/* Badge */}
            <div className="inline-flex w-fit">
              <span className="flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold px-4 py-1.5 rounded-full tracking-wide">
                <span className="text-blue-400">✦</span>
                Plataforma gratuita para começar
              </span>
            </div>

            {/* Headline */}
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white leading-[1.1] tracking-tight">
              Invista com{" "}
              <span className="text-blue-400">inteligência.</span>
              <br />
              Entenda seu{" "}
              <span className="text-emerald-400">patrimônio.</span>
            </h1>

            {/* Subheadline */}
            <p className="text-lg text-gray-400 leading-relaxed max-w-lg">
              Carteira completa, análise de IA, screener de ações e FIIs — tudo em um
              lugar. Gratuito para começar.
            </p>

            {/* CTAs */}
            <div className="flex flex-wrap gap-3 mt-2">
              <Link
                href="/register"
                className="flex items-center gap-2 px-7 py-3.5 bg-blue-500 text-white font-bold rounded-xl hover:bg-blue-400 transition-all duration-200 hover:scale-[1.02] shadow-lg shadow-blue-500/25"
              >
                Começar grátis
                <ArrowRight className="h-4 w-4" strokeWidth={2.5} />
              </Link>
              <a
                href="#precos"
                className="flex items-center gap-2 px-7 py-3.5 bg-white/10 text-white font-semibold rounded-xl hover:bg-white/15 border border-white/10 transition-all duration-200"
              >
                Ver planos
              </a>
            </div>

            {/* Social proof micro line */}
            <p className="text-xs text-gray-500 flex items-center gap-1.5">
              <Check className="h-3.5 w-3.5 text-emerald-500 shrink-0" strokeWidth={3} />
              Sem cartão de crédito — conta criada em 30 segundos
            </p>
          </div>

          {/* Right: floating stat cards */}
          <div className="hidden lg:flex flex-col gap-4 items-end">
            <div className="grid grid-cols-2 gap-3 w-full max-w-sm">
              <StatCard
                label="Patrimônio total"
                value="R$ 47.832"
                sub="+12,4% no mês"
                accent
              />
              <StatCard
                label="Alocado"
                value="89%"
                sub="Carteira diversificada"
              />
              <StatCard
                label="Rendimento anual"
                value="28,6%"
                sub="vs CDI +14,2%"
              />
              <StatCard
                label="Dividend yield"
                value="8,3%"
                sub="Média da carteira"
              />
            </div>
            {/* "screen" frame hint */}
            <p className="text-[11px] text-gray-600 tracking-wide uppercase mt-1">
              Dados ilustrativos
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

function FeaturesSection() {
  return (
    <section className="bg-[#F9FAFB] py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-14">
          <p className="text-xs font-bold uppercase tracking-widest text-blue-500 mb-3">
            Tudo que você precisa
          </p>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-gray-900 tracking-tight">
            Da carteira à análise —
            <br className="hidden sm:block" /> num só lugar
          </h2>
          <p className="mt-4 text-gray-500 max-w-xl mx-auto leading-relaxed">
            Do acompanhamento de P&L à análise de IA com DCF — o InvestIQ reúne as
            ferramentas de um investidor institucional para o investidor individual.
          </p>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map((f) => (
            <FeatureCard key={f.title} {...f} />
          ))}
        </div>
      </div>
    </section>
  );
}

function StatsStrip() {
  return (
    <section className="bg-[#111827] py-12 border-y border-white/5">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-0 md:divide-x md:divide-white/10">
          {STATS.map(({ value, label }) => (
            <div key={label} className="flex flex-col items-center gap-1 text-center md:px-8">
              <span className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                {value}
              </span>
              <span className="text-sm text-gray-400">{label}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function PricingSection() {
  return (
    <section id="precos" className="bg-white py-24 scroll-mt-16">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-14">
          <p className="text-xs font-bold uppercase tracking-widest text-blue-500 mb-3">
            Preços simples
          </p>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-gray-900 tracking-tight">
            Comece grátis.
            <br className="hidden sm:block" /> Evolua quando precisar.
          </h2>
        </div>

        {/* Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl mx-auto">
          <LandingPricingCard
            name="Gratuito"
            price="R$ 0"
            priceNote="Para sempre"
            features={FREE_FEATURES}
            ctaHref="/register"
            ctaLabel="Criar conta grátis"
          />
          <LandingPricingCard
            name="Premium"
            price="R$ 29,90"
            priceNote="por mês · cancele quando quiser"
            features={PRO_FEATURES}
            highlighted
            ctaHref="/register"
            ctaLabel="Começar com Premium"
            badge="Mais popular"
          />
        </div>

        {/* Trust line */}
        <p className="mt-8 text-center text-sm text-gray-500">
          Sem cartão de crédito. Cancele quando quiser.
          <span className="mx-2 text-gray-300">·</span>
          Pagamento processado com segurança pelo Stripe.
        </p>
      </div>
    </section>
  );
}

function CtaBanner() {
  return (
    <section className="relative bg-[#111827] py-24 overflow-hidden">
      {/* Blue gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600/20 via-transparent to-transparent pointer-events-none" />
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-[100px] pointer-events-none" />

      <div className="relative z-10 mx-auto max-w-2xl px-4 sm:px-6 lg:px-8 text-center flex flex-col items-center gap-6">
        <h2 className="text-4xl sm:text-5xl font-extrabold text-white tracking-tight">
          Comece hoje.{" "}
          <span className="text-blue-400">É grátis.</span>
        </h2>
        <p className="text-lg text-gray-400 max-w-md">
          14 dias de Premium incluídos em qualquer cadastro. Sem cartão de crédito.
        </p>
        <Link
          href="/register"
          className="flex items-center gap-2 px-8 py-4 bg-blue-500 text-white text-base font-bold rounded-xl hover:bg-blue-400 transition-all duration-200 hover:scale-[1.02] shadow-xl shadow-blue-500/25 mt-2"
        >
          Criar conta grátis
          <ArrowRight className="h-5 w-5" strokeWidth={2.5} />
        </Link>
        <p className="text-xs text-gray-600">
          Junte-se a investidores que gerenciam sua carteira com inteligência.
        </p>
      </div>
    </section>
  );
}

function LandingFooter() {
  return (
    <footer className="bg-[#111827] border-t border-white/5 py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
          {/* Brand */}
          <div className="flex flex-col gap-2">
            <Link href="/" className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-md bg-blue-500 flex items-center justify-center">
                <span className="text-white font-bold text-xs">IQ</span>
              </div>
              <span className="font-bold text-sm text-white tracking-tight">InvestIQ</span>
            </Link>
            <p className="text-xs text-gray-500">Inteligência para seus investimentos.</p>
          </div>

          {/* Links */}
          <nav className="flex flex-wrap gap-x-6 gap-y-2">
            {[
              { href: "/login", label: "Entrar" },
              { href: "/register", label: "Criar conta" },
              { href: "#precos", label: "Planos" },
            ].map(({ href, label }) => (
              <a
                key={href}
                href={href}
                className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
              >
                {label}
              </a>
            ))}
          </nav>
        </div>

        {/* Bottom line */}
        <div className="mt-8 pt-6 border-t border-white/5">
          <p className="text-xs text-gray-600 text-center">
            © 2026 InvestIQ. Todos os direitos reservados.
          </p>
        </div>
      </div>
    </footer>
  );
}

// ─── Page ──────────────────────────────────────────────────────────────────────

export default function LandingPage() {
  return (
    <>
      <LandingNav />
      <main>
        <HeroSection />
        <FeaturesSection />
        <StatsStrip />
        <PricingSection />
        <CtaBanner />
      </main>
      <LandingFooter />
    </>
  );
}
