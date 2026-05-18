"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  Brain,
  ChartBar,
  MagnifyingGlass,
  Bank,
  UploadSimple,
  Calculator,
  ArrowRight,
  Check,
  X,
  Sparkle,
  ChartPie,
  Bell,
} from "@phosphor-icons/react";
import { LandingNav } from "@/components/LandingNav";

// ─── Motion primitives ────────────────────────────────────────────────────────

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { ease: [0.16, 1, 0.3, 1] as const, duration: 0.55 },
  },
};

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08 } },
};

function InView({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <motion.div
      variants={stagger}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-80px 0px" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// ─── Data ─────────────────────────────────────────────────────────────────────

const FEATURES = [
  {
    key: "ai",
    icon: Brain,
    title: "IA de Investimentos",
    description:
      "Análise DCF, valuation por ativo e diagnóstico completo do portfólio com sugestões de realocação baseadas em dados reais de mercado.",
    badge: "Premium",
    dark: true,
    span: "lg:col-span-3",
  },
  {
    key: "screener",
    icon: MagnifyingGlass,
    title: "Screener Avançado",
    description:
      "Filtre ações pelo método Goldman Sachs e FIIs por P/VP, DY e liquidez com um clique.",
    span: "lg:col-span-2",
  },
  {
    key: "portfolio",
    icon: ChartBar,
    title: "Carteira Completa",
    description:
      "Ações, FIIs, ETFs, renda fixa. Acompanhe P&L, custos médios e rentabilidade em tempo real.",
    span: "lg:col-span-2",
  },
  {
    key: "fixed",
    icon: Bank,
    title: "Renda Fixa",
    description:
      "Compare Tesouro Direto, CDB, LCI e LCA. Simule cenários e encontre as melhores taxas.",
    span: "lg:col-span-3",
  },
  {
    key: "import",
    icon: UploadSimple,
    title: "Importação Automática",
    description:
      "Importe notas de corretagem em PDF/CSV. Suporte para todas as corretoras brasileiras.",
    span: "lg:col-span-3",
  },
  {
    key: "ir",
    icon: Calculator,
    title: "Helper de IR",
    description:
      "Calcule IRRF, apure ganhos e organize informações para a declaração do Imposto de Renda.",
    span: "lg:col-span-2",
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

// ─── Hero ─────────────────────────────────────────────────────────────────────

function HeroSection() {
  return (
    <section className="relative bg-[#111827] min-h-[100dvh] flex items-center overflow-hidden">
      <div
        className="absolute inset-0 opacity-[0.04] pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
        }}
      />
      <div className="absolute bottom-0 left-1/4 w-[600px] h-[400px] bg-blue-600/10 rounded-full blur-[120px] pointer-events-none" />

      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-24 lg:py-0 w-full">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left: copy */}
          <motion.div
            className="flex flex-col gap-6"
            variants={stagger}
            initial="hidden"
            animate="visible"
          >
            <motion.div variants={fadeUp} className="inline-flex w-fit">
              <span className="flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold px-4 py-1.5 rounded-full tracking-wide">
                <Sparkle className="h-3.5 w-3.5" weight="fill" />
                Plataforma gratuita para começar
              </span>
            </motion.div>

            <motion.h1
              variants={fadeUp}
              className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white leading-[1.1] tracking-tight"
            >
              Invista com{" "}
              <span className="text-blue-400">inteligência.</span>
              <br />
              Entenda seu{" "}
              <span className="text-emerald-400">patrimônio.</span>
            </motion.h1>

            <motion.p
              variants={fadeUp}
              className="text-lg text-zinc-400 leading-relaxed max-w-lg"
            >
              Carteira completa, análise de IA, screener de ações e FIIs — tudo
              em um lugar. Gratuito para começar.
            </motion.p>

            <motion.div
              variants={fadeUp}
              className="flex flex-wrap gap-3 mt-2"
            >
              <motion.div
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Link
                  href="/register"
                  className="flex items-center gap-2 px-7 py-3.5 bg-blue-500 text-white font-bold rounded-xl hover:bg-blue-400 transition-colors duration-200 shadow-lg shadow-blue-500/25"
                >
                  Começar grátis
                  <ArrowRight className="h-4 w-4" weight="bold" />
                </Link>
              </motion.div>
              <a
                href="#precos"
                className="flex items-center gap-2 px-7 py-3.5 bg-white/10 text-white font-semibold rounded-xl hover:bg-white/15 border border-white/10 transition-colors duration-200"
              >
                Ver planos
              </a>
            </motion.div>

            <motion.p
              variants={fadeUp}
              className="text-xs text-zinc-500 flex items-center gap-1.5"
            >
              <Check
                className="h-3.5 w-3.5 text-emerald-500 shrink-0"
                weight="bold"
              />
              Sem cartão de crédito — conta criada em 30 segundos
            </motion.p>
          </motion.div>

          {/* Right: stat cards */}
          <motion.div
            className="hidden lg:grid grid-cols-2 gap-3 w-full max-w-sm ml-auto"
            variants={stagger}
            initial="hidden"
            animate="visible"
          >
            {[
              {
                label: "Patrimônio total",
                value: "R$ 47.832",
                sub: "+12,4% no mês",
                accent: true,
              },
              {
                label: "Alocado",
                value: "89%",
                sub: "Carteira diversificada",
              },
              {
                label: "Rendimento anual",
                value: "28,6%",
                sub: "vs CDI +14,2%",
              },
              {
                label: "Dividend yield",
                value: "8,3%",
                sub: "Média da carteira",
              },
            ].map((card) => (
              <motion.div
                key={card.label}
                variants={fadeUp}
                className={`rounded-xl px-5 py-4 flex flex-col gap-1 shadow-lg border ${
                  card.accent
                    ? "bg-blue-500/20 border-blue-500/30"
                    : "bg-white/10 border-white/10"
                }`}
              >
                <span className="text-xs font-medium text-zinc-400 uppercase tracking-wide">
                  {card.label}
                </span>
                <span className="text-2xl font-extrabold tracking-tight text-white">
                  {card.value}
                </span>
                <span
                  className={`text-xs font-medium ${
                    card.accent ? "text-blue-300" : "text-emerald-400"
                  }`}
                >
                  {card.sub}
                </span>
              </motion.div>
            ))}
            <p className="col-span-2 text-[11px] text-zinc-600 tracking-wide uppercase text-right mt-1">
              Dados ilustrativos
            </p>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

// ─── Features ─────────────────────────────────────────────────────────────────

function FeaturesSection() {
  return (
    <section className="bg-zinc-50 py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <InView>
          <motion.div variants={fadeUp} className="mb-14">
            <p className="text-xs font-bold uppercase tracking-widest text-blue-500 mb-3">
              Tudo que você precisa
            </p>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-zinc-900 tracking-tight">
              Da carteira à análise —
              <br className="hidden sm:block" /> num só lugar
            </h2>
            <p className="mt-4 text-zinc-500 max-w-xl leading-relaxed">
              Do acompanhamento de P&L à análise de IA com DCF — ferramentas
              institucionais para o investidor individual.
            </p>
          </motion.div>
        </InView>

        {/* Asymmetric 5-column grid: 3+2, 2+3, 3+2 */}
        <InView className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <motion.div
                key={f.key}
                variants={fadeUp}
                whileHover={{
                  y: -2,
                  transition: {
                    type: "spring",
                    stiffness: 400,
                    damping: 25,
                  },
                }}
                className={`group rounded-2xl border p-6 hover:shadow-md transition-shadow duration-200 ${f.span} ${
                  f.dark
                    ? "bg-zinc-900 border-zinc-700"
                    : "bg-white border-zinc-200 hover:border-blue-200"
                }`}
              >
                <div className="flex items-start justify-between mb-4">
                  <div
                    className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                      f.dark
                        ? "bg-blue-500/20"
                        : "bg-blue-50 group-hover:bg-blue-100 transition-colors"
                    }`}
                  >
                    <Icon
                      className={`h-5 w-5 ${
                        f.dark ? "text-blue-400" : "text-blue-500"
                      }`}
                      weight="duotone"
                    />
                  </div>
                  {f.badge && (
                    <span className="text-[10px] font-bold uppercase tracking-widest bg-blue-500 text-white px-2 py-0.5 rounded-full">
                      {f.badge}
                    </span>
                  )}
                </div>
                <h3
                  className={`font-semibold mb-1.5 ${
                    f.dark ? "text-white" : "text-zinc-900"
                  }`}
                >
                  {f.title}
                </h3>
                <p
                  className={`text-sm leading-relaxed ${
                    f.dark ? "text-zinc-400" : "text-zinc-500"
                  }`}
                >
                  {f.description}
                </p>
              </motion.div>
            );
          })}
        </InView>
      </div>
    </section>
  );
}

// ─── Stats strip ──────────────────────────────────────────────────────────────

function StatsStrip() {
  return (
    <section className="bg-[#111827] py-12 border-y border-white/5">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <motion.div
          className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-0 md:divide-x md:divide-white/10"
          variants={stagger}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-60px 0px" }}
        >
          {STATS.map(({ value, label }) => (
            <motion.div
              key={label}
              variants={fadeUp}
              className="flex flex-col items-center gap-1 text-center md:px-8"
            >
              <span className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                {value}
              </span>
              <span className="text-sm text-zinc-400">{label}</span>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

// ─── Pricing ──────────────────────────────────────────────────────────────────

function PricingSection() {
  return (
    <section id="precos" className="bg-white py-24 scroll-mt-16">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <InView>
          <motion.div variants={fadeUp} className="mb-14">
            <p className="text-xs font-bold uppercase tracking-widest text-blue-500 mb-3">
              Preços simples
            </p>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-zinc-900 tracking-tight">
              Comece grátis.
              <br className="hidden sm:block" /> Evolua quando precisar.
            </h2>
          </motion.div>
        </InView>

        <InView className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl">
          {/* Free */}
          <motion.div
            variants={fadeUp}
            className="rounded-2xl flex flex-col gap-6 p-8 bg-zinc-100 hover:bg-zinc-50 transition-colors"
          >
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                Gratuito
              </p>
              <p className="mt-2 text-5xl font-extrabold tracking-tight text-zinc-900">
                R$ 0
              </p>
              <p className="mt-1 text-sm text-zinc-500">Para sempre</p>
            </div>
            <ul className="flex flex-col gap-3">
              {FREE_FEATURES.map((f) => (
                <li key={f.label} className="flex items-start gap-3 text-sm">
                  <span
                    className={`mt-0.5 shrink-0 h-4 w-4 flex items-center justify-center rounded-full ${
                      f.included
                        ? "bg-emerald-500 text-white"
                        : "bg-zinc-300 text-zinc-500"
                    }`}
                  >
                    {f.included ? (
                      <Check className="h-2.5 w-2.5" weight="bold" />
                    ) : (
                      <X className="h-2.5 w-2.5" weight="bold" />
                    )}
                  </span>
                  <span
                    className={
                      f.included ? "text-zinc-800" : "text-zinc-400"
                    }
                  >
                    {f.label}
                  </span>
                </li>
              ))}
            </ul>
            <div className="mt-auto">
              <motion.div
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.98 }}
              >
                <Link
                  href="/register"
                  className="block w-full rounded-xl text-sm font-bold py-3.5 text-center bg-[#111827] text-white hover:bg-zinc-800 transition-colors"
                >
                  Criar conta grátis
                </Link>
              </motion.div>
            </div>
          </motion.div>

          {/* Pro */}
          <motion.div
            variants={fadeUp}
            className="relative rounded-2xl flex flex-col gap-6 p-8 bg-[#111827] text-white shadow-2xl scale-[1.02]"
          >
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
              <span className="bg-blue-500 text-white text-xs font-bold uppercase tracking-widest px-4 py-1 rounded-full shadow-lg">
                Mais popular
              </span>
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-blue-400">
                Premium
              </p>
              <p className="mt-2 text-5xl font-extrabold tracking-tight text-white">
                R$ 29,90
              </p>
              <p className="mt-1 text-sm text-zinc-400">
                por mês · cancele quando quiser
              </p>
            </div>
            <ul className="flex flex-col gap-3">
              {PRO_FEATURES.map((f) => (
                <li key={f.label} className="flex items-start gap-3 text-sm">
                  <span className="mt-0.5 shrink-0 h-4 w-4 flex items-center justify-center rounded-full bg-blue-500 text-white">
                    <Check className="h-2.5 w-2.5" weight="bold" />
                  </span>
                  <span className="text-zinc-200">{f.label}</span>
                </li>
              ))}
            </ul>
            <div className="mt-auto">
              <motion.div
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.98 }}
              >
                <Link
                  href="/register"
                  className="block w-full rounded-xl text-sm font-bold py-3.5 text-center bg-blue-500 text-white hover:bg-blue-400 transition-colors"
                >
                  Começar com Premium
                </Link>
              </motion.div>
            </div>
          </motion.div>
        </InView>

        <p className="mt-8 text-sm text-zinc-500">
          Sem cartão de crédito. Cancele quando quiser.
          <span className="mx-2 text-zinc-300">·</span>
          Pagamento processado com segurança pelo Stripe.
        </p>
      </div>
    </section>
  );
}

// ─── CTA Banner ───────────────────────────────────────────────────────────────

function CtaBanner() {
  return (
    <section className="relative bg-[#111827] py-24 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600/20 via-transparent to-transparent pointer-events-none" />
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-[100px] pointer-events-none" />

      <motion.div
        className="relative z-10 mx-auto max-w-2xl px-4 sm:px-6 lg:px-8 flex flex-col items-center gap-6"
        variants={stagger}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-60px 0px" }}
      >
        <motion.h2
          variants={fadeUp}
          className="text-4xl sm:text-5xl font-extrabold text-white tracking-tight text-center"
        >
          Comece hoje.{" "}
          <span className="text-blue-400">É grátis.</span>
        </motion.h2>
        <motion.p
          variants={fadeUp}
          className="text-lg text-zinc-400 max-w-md text-center"
        >
          14 dias de Premium incluídos em qualquer cadastro. Sem cartão de
          crédito.
        </motion.p>
        <motion.div
          variants={fadeUp}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <Link
            href="/register"
            className="flex items-center gap-2 px-8 py-4 bg-blue-500 text-white text-base font-bold rounded-xl hover:bg-blue-400 transition-colors shadow-xl shadow-blue-500/25"
          >
            Criar conta grátis
            <ArrowRight className="h-5 w-5" weight="bold" />
          </Link>
        </motion.div>
        <motion.p variants={fadeUp} className="text-xs text-zinc-600">
          Junte-se a investidores que gerenciam sua carteira com inteligência.
        </motion.p>
      </motion.div>
    </section>
  );
}

// ─── Footer ───────────────────────────────────────────────────────────────────

function LandingFooter() {
  return (
    <footer className="bg-[#111827] border-t border-white/5 py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
          <div className="flex flex-col gap-2">
            <Link href="/" className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-md bg-blue-500 flex items-center justify-center">
                <span className="text-white font-bold text-xs">IQ</span>
              </div>
              <span className="font-bold text-sm text-white tracking-tight">
                InvestIQ
              </span>
            </Link>
            <p className="text-xs text-zinc-500">
              Inteligência para seus investimentos.
            </p>
          </div>

          <nav className="flex flex-wrap gap-x-6 gap-y-2">
            {[
              { href: "/login", label: "Entrar" },
              { href: "/register", label: "Criar conta" },
              { href: "#precos", label: "Planos" },
            ].map(({ href, label }) => (
              <a
                key={href}
                href={href}
                className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                {label}
              </a>
            ))}
          </nav>
        </div>

        <div className="mt-8 pt-6 border-t border-white/5">
          <p className="text-xs text-zinc-600 text-center">
            © 2026 InvestIQ. Todos os direitos reservados.
          </p>
        </div>
      </div>
    </footer>
  );
}

// ─── Export ───────────────────────────────────────────────────────────────────

export function LandingPage() {
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
