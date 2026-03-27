import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Ferramentas — InvestIQ",
  description: "Conheça todas as ferramentas do InvestIQ: dashboard em tempo real, análise de IA, watchlist, alertas, importação de dados e muito mais.",
};

/* ─── Feature data ─────────────────────────────────────── */
const FEATURES = [
  {
    id: "dashboard",
    icon: "📊",
    color: "bg-blue-500",
    lightColor: "bg-blue-50",
    textColor: "text-blue-600",
    borderColor: "border-blue-200",
    title: "Dashboard em Tempo Real",
    subtitle: "Visão completa do seu patrimônio em segundos",
    description:
      "Acompanhe o desempenho de toda a sua carteira num único painel. Patrimônio total, retorno do dia, evolução histórica e indicadores macroeconômicos atualizados automaticamente.",
    items: [
      "Patrimônio total com variação diária e histórica",
      "Gráfico de evolução patrimonial (TradingView)",
      "Indicadores macro: SELIC, CDI, IPCA e PTAX em tempo real",
      "Alocação por classe: Ações, FIIs, Renda Fixa, BDRs, ETFs",
      "Últimas transações com destaque visual de compra/venda",
    ],
    badge: "Grátis",
    badgeColor: "bg-emerald-100 text-emerald-700",
  },
  {
    id: "portfolio",
    icon: "💼",
    color: "bg-violet-500",
    lightColor: "bg-violet-50",
    textColor: "text-violet-600",
    borderColor: "border-violet-200",
    title: "Gestão de Carteira & P&L",
    subtitle: "Saiba exatamente quanto você ganhou ou perdeu",
    description:
      "Cadastre suas transações e veja o P&L (lucro/prejuízo) de cada ativo atualizado com cotações em tempo real. Compare sua rentabilidade com benchmarks como CDI e IBOVESPA.",
    items: [
      "P&L por ativo: preço médio de compra vs. cotação atual",
      "Porcentagem de ganho/perda por posição",
      "Histórico completo de dividendos e proventos recebidos",
      "Comparação de rentabilidade vs. CDI e IBOVESPA",
      "Filtros por ano e classe de ativo nos proventos",
    ],
    badge: "Grátis",
    badgeColor: "bg-emerald-100 text-emerald-700",
  },
  {
    id: "transactions",
    icon: "↕️",
    color: "bg-sky-500",
    lightColor: "bg-sky-50",
    textColor: "text-sky-600",
    borderColor: "border-sky-200",
    title: "Controle de Transações",
    subtitle: "Registro detalhado de todas as suas operações",
    description:
      "Registre compras, vendas, dividendos e proventos de forma simples. Filtre, pesquise e exporte seu histórico completo de operações com suporte a múltiplas classes de ativos.",
    items: [
      "Registro de compra e venda com data, quantidade e preço",
      "Suporte a Ações, FIIs, Renda Fixa, BDRs e ETFs",
      "Histórico completo com filtros e busca",
      "Até 50 transações no plano gratuito",
      "Transações ilimitadas no plano Premium",
    ],
    badge: "Grátis",
    badgeColor: "bg-emerald-100 text-emerald-700",
  },
  {
    id: "ai",
    icon: "🤖",
    color: "bg-blue-600",
    lightColor: "bg-blue-50",
    textColor: "text-blue-700",
    borderColor: "border-blue-200",
    title: "IA Copiloto de Investimentos",
    subtitle: "Análises que antes eram exclusivas de grandes gestores",
    description:
      "Use inteligência artificial para analisar ativos individualmente e entender o impacto das condições macroeconômicas na sua carteira. Resultados em linguagem clara, sem jargão.",
    items: [
      "Análise DCF (Fluxo de Caixa Descontado) por ativo",
      "Valuation: P/L, P/VP, EV/EBITDA com benchmarks do setor",
      "Análise macro: impacto de SELIC, inflação e câmbio na carteira",
      "Diagnóstico completo de saúde da carteira",
      "Histórico de análises anteriores salvo automaticamente",
    ],
    badge: "Premium",
    badgeColor: "bg-blue-100 text-blue-700",
  },
  {
    id: "advisor",
    icon: "🧠",
    color: "bg-indigo-500",
    lightColor: "bg-indigo-50",
    textColor: "text-indigo-600",
    borderColor: "border-indigo-200",
    title: "AI Advisor Personalizado",
    subtitle: "Recomendações feitas para o seu perfil",
    description:
      "Configure seu perfil de investidor — objetivos, horizonte e tolerância ao risco — e receba recomendações de IA personalizadas para a sua situação financeira específica.",
    items: [
      "Perfil personalizado: idade, renda, patrimônio e objetivo",
      "Tolerância ao risco: conservador, moderado ou agressivo",
      "Horizon de investimento de curto a longo prazo",
      "Recomendações de alocação alvo por classe de ativo",
      "Diagnóstico automático de desvios do portfólio ideal",
    ],
    badge: "Premium",
    badgeColor: "bg-blue-100 text-blue-700",
  },
  {
    id: "watchlist",
    icon: "👁️",
    color: "bg-emerald-500",
    lightColor: "bg-emerald-50",
    textColor: "text-emerald-600",
    borderColor: "border-emerald-200",
    title: "Watchlist & Alertas de Preço",
    subtitle: "Nunca perca uma oportunidade de compra",
    description:
      "Monitore ativos que você ainda não possui ou quer acompanhar mais de perto. Configure alertas de preço e receba um email automático quando o ativo atingir seu target.",
    items: [
      "Adicione qualquer ticker para monitoramento contínuo",
      "Cotação, DY, P/L e P/VP atualizados em tempo real",
      "Alertas configuráveis: preço-alvo de compra ou venda",
      "Notificação por email automática ao atingir o target",
      "Tolerância de ±2% para evitar falsos disparos",
    ],
    badge: "Grátis",
    badgeColor: "bg-emerald-100 text-emerald-700",
  },
  {
    id: "insights",
    icon: "💡",
    color: "bg-amber-500",
    lightColor: "bg-amber-50",
    textColor: "text-amber-600",
    borderColor: "border-amber-200",
    title: "Insights Automáticos",
    subtitle: "O copiloto trabalha enquanto você dorme",
    description:
      "O sistema analisa sua carteira automaticamente e gera alertas inteligentes sobre concentração, diversificação e oportunidades — sem você precisar pedir.",
    items: [
      "Alertas de concentração excessiva em um único ativo",
      "Sugestões de diversificação por classe e setor",
      "Oportunidades identificadas por variações de mercado",
      "Notificações marcáveis como lido para organização",
      "Histórico completo de insights com data e severidade",
    ],
    badge: "Grátis",
    badgeColor: "bg-emerald-100 text-emerald-700",
  },
  {
    id: "imports",
    icon: "📥",
    color: "bg-orange-500",
    lightColor: "bg-orange-50",
    textColor: "text-orange-600",
    borderColor: "border-orange-200",
    title: "Importação de Dados",
    subtitle: "Migre sua carteira em minutos, sem retrabalho",
    description:
      "Importe seu histórico de operações direto da B3 ou via planilha. O sistema processa, valida e apresenta os dados para revisão antes de confirmar — zero risco de erro.",
    items: [
      "Upload do extrato de operações da B3 (CSV/XLSX)",
      "Importação via planilha padronizada",
      "Revisão item a item antes de confirmar",
      "Detecção automática de duplicatas",
      "3 importações/mês no grátis · ilimitado no Premium",
    ],
    badge: "Grátis",
    badgeColor: "bg-emerald-100 text-emerald-700",
  },
];

const PLANS = [
  {
    name: "Gratuito",
    price: "R$ 0",
    period: "para sempre",
    dark: false,
    features: [
      "Dashboard completo em tempo real",
      "Até 50 transações",
      "Até 3 importações por mês",
      "Watchlist com cotações ao vivo",
      "Alertas de preço",
      "Insights automáticos",
      "Análise de IA básica",
    ],
    cta: "Criar conta grátis",
    href: "/register",
  },
  {
    name: "Premium",
    price: "R$ 29,90",
    period: "por mês",
    dark: true,
    features: [
      "Tudo do plano Gratuito",
      "Transações ilimitadas",
      "Importações ilimitadas",
      "IA Copiloto sem limite de análises",
      "Análise DCF e valuation avançado",
      "Análise macro do portfólio",
      "AI Advisor personalizado",
      "Suporte prioritário",
    ],
    cta: "Assinar Premium",
    href: "/register",
  },
];

/* ─── Page ──────────────────────────────────────────────── */
export default function ToolsPage() {
  return (
    <div className="min-h-screen bg-white" style={{ fontFamily: "'Outfit', sans-serif" }}>

      {/* ── Header ── */}
      <header className="bg-[#111827] sticky top-0 z-50">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link href="/login" className="flex items-center gap-2.5">
              <div className="h-8 w-8 rounded-md bg-blue-500 flex items-center justify-center flex-shrink-0">
                <span className="text-white font-bold text-xs">IQ</span>
              </div>
              <span className="text-white font-bold text-lg tracking-tight">InvestIQ</span>
            </Link>

            <nav className="hidden md:flex items-center gap-1">
              <Link
                href="/tools"
                className="text-white bg-white/10 text-sm font-medium px-4 py-1.5 rounded-full"
              >
                Ferramentas
              </Link>
            </nav>

            <div className="flex items-center gap-3">
              <Link
                href="/login"
                className="text-gray-300 hover:text-white text-sm font-medium transition-colors"
              >
                Entrar
              </Link>
              <Link
                href="/register"
                className="bg-blue-500 hover:bg-blue-600 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
              >
                Criar conta grátis
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="bg-[#111827] pb-20 pt-16 relative overflow-hidden">
        <div className="absolute -top-32 -left-32 h-96 w-96 rounded-full bg-blue-500/10" />
        <div className="absolute top-1/2 -right-24 h-72 w-72 rounded-full bg-emerald-500/8" />
        <div className="absolute bottom-0 left-1/3 h-64 w-64 rounded-full bg-blue-500/5" />

        <div className="relative mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 text-center">
          <div className="inline-flex items-center gap-2 bg-blue-500/20 text-blue-300 text-xs font-semibold px-3 py-1 rounded-full mb-6 border border-blue-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
            8 ferramentas integradas
          </div>

          <h1 className="text-4xl sm:text-5xl font-extrabold text-white tracking-tight leading-tight">
            Tudo o que você precisa<br />
            <span className="text-blue-400">para investir melhor</span>
          </h1>

          <p className="mt-6 text-gray-400 text-lg max-w-2xl mx-auto leading-relaxed">
            Ferramentas profissionais de gestão de carteira, análise com IA e alertas inteligentes —
            antes exclusivas de grandes gestores, agora acessíveis para todos.
          </p>

          <div className="mt-10 flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              href="/register"
              className="bg-blue-500 hover:bg-blue-600 text-white font-semibold px-8 py-3 rounded-lg transition-colors text-base"
            >
              Criar conta grátis →
            </Link>
            <Link
              href="/login"
              className="text-gray-300 hover:text-white border border-white/20 hover:border-white/40 font-medium px-8 py-3 rounded-lg transition-colors text-base"
            >
              Já tenho conta
            </Link>
          </div>
        </div>

        {/* Stats strip */}
        <div className="relative mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 mt-16">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-white/10 rounded-xl overflow-hidden">
            {[
              { value: "8", label: "Ferramentas integradas" },
              { value: "5", label: "Classes de ativos" },
              { value: "IA", label: "Análises inteligentes" },
              { value: "100%", label: "Gratuito para começar" },
            ].map((stat) => (
              <div key={stat.label} className="bg-[#1a2332] px-6 py-5 text-center">
                <p className="text-2xl font-extrabold text-white">{stat.value}</p>
                <p className="text-xs text-gray-400 mt-1">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features grid ── */}
      <section className="py-20 bg-gray-50">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-extrabold text-gray-900 tracking-tight">
              Explore todas as ferramentas
            </h2>
            <p className="mt-3 text-gray-500 text-base max-w-xl mx-auto">
              Cada ferramenta foi desenvolvida para um aspecto específico da gestão de investimentos.
              Veja o que você pode fazer.
            </p>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {FEATURES.map((f) => (
              <div
                key={f.id}
                className={`bg-white rounded-xl border ${f.borderColor} p-6 flex flex-col gap-4 hover:-translate-y-0.5 transition-transform`}
              >
                {/* Icon + badge */}
                <div className="flex items-start justify-between">
                  <div className={`${f.lightColor} w-11 h-11 rounded-lg flex items-center justify-center text-xl flex-shrink-0`}>
                    {f.icon}
                  </div>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${f.badgeColor}`}>
                    {f.badge}
                  </span>
                </div>

                {/* Title */}
                <div>
                  <h3 className="font-bold text-gray-900 text-base leading-tight">{f.title}</h3>
                  <p className={`text-xs font-medium mt-0.5 ${f.textColor}`}>{f.subtitle}</p>
                </div>

                {/* Description */}
                <p className="text-gray-500 text-sm leading-relaxed flex-1">{f.description}</p>

                {/* Feature bullets */}
                <ul className="space-y-1.5">
                  {f.items.map((item) => (
                    <li key={item} className="flex items-start gap-2 text-xs text-gray-600">
                      <span className={`mt-0.5 flex-shrink-0 w-3.5 h-3.5 rounded-full ${f.color} flex items-center justify-center`}>
                        <svg className="w-2 h-2 text-white" fill="none" viewBox="0 0 12 12">
                          <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="py-20 bg-white">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-extrabold text-gray-900 tracking-tight">
              Como funciona
            </h2>
            <p className="mt-3 text-gray-500 text-base">
              Do cadastro à primeira análise em menos de 5 minutos.
            </p>
          </div>

          <div className="grid sm:grid-cols-3 gap-8">
            {[
              {
                step: "01",
                icon: "👤",
                title: "Crie sua conta",
                description:
                  "Cadastro gratuito em segundos. Informe seu perfil de investidor — objetivos, horizonte e tolerância ao risco — para receber análises personalizadas.",
              },
              {
                step: "02",
                icon: "📂",
                title: "Importe ou adicione sua carteira",
                description:
                  "Faça upload do seu extrato da B3, use a planilha padrão ou registre as transações manualmente. O sistema calcula o P&L automaticamente.",
              },
              {
                step: "03",
                icon: "🚀",
                title: "Deixe a IA trabalhar",
                description:
                  "Receba análises de valuation, alertas de preço, insights automáticos e relatórios macro — tudo gerado por IA e personalizado para a sua carteira.",
              },
            ].map((step) => (
              <div key={step.step} className="flex flex-col items-center text-center gap-4">
                <div className="relative">
                  <div className="w-16 h-16 bg-gray-100 rounded-xl flex items-center justify-center text-2xl">
                    {step.icon}
                  </div>
                  <div className="absolute -top-2 -right-2 w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                    <span className="text-white text-[10px] font-bold">{step.step}</span>
                  </div>
                </div>
                <div>
                  <h3 className="font-bold text-gray-900 text-base">{step.title}</h3>
                  <p className="mt-2 text-gray-500 text-sm leading-relaxed">{step.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Asset classes ── */}
      <section className="py-16 bg-gray-50">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-10">
            <h2 className="text-2xl font-extrabold text-gray-900">
              Classes de ativos suportadas
            </h2>
            <p className="mt-2 text-gray-500 text-sm">
              Gerencie toda a sua carteira de renda variável e fixa num único lugar.
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
            {[
              { icon: "📈", name: "Ações", desc: "B3 — Bovespa e Novo Mercado" },
              { icon: "🏢", name: "FIIs", desc: "Fundos Imobiliários" },
              { icon: "🔒", name: "Renda Fixa", desc: "Tesouro, CDB, LCI/LCA" },
              { icon: "🌍", name: "BDRs", desc: "Brazilian Depositary Receipts" },
              { icon: "📦", name: "ETFs", desc: "Exchange-Traded Funds" },
            ].map((a) => (
              <div key={a.name} className="bg-white rounded-xl border border-gray-200 p-4 text-center">
                <span className="text-2xl">{a.icon}</span>
                <p className="font-bold text-gray-900 text-sm mt-2">{a.name}</p>
                <p className="text-gray-400 text-xs mt-0.5">{a.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Plans ── */}
      <section className="py-20 bg-white">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-extrabold text-gray-900 tracking-tight">
              Comece grátis, evolua quando precisar
            </h2>
            <p className="mt-3 text-gray-500 text-base">
              O plano gratuito já inclui as principais ferramentas. Faça upgrade quando quiser análises ilimitadas de IA.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 gap-6">
            {PLANS.map((plan) => (
              <div
                key={plan.name}
                className={`rounded-xl p-8 flex flex-col gap-6 border ${
                  plan.dark
                    ? "bg-[#111827] border-[#1e2d42]"
                    : "bg-gray-50 border-gray-200"
                }`}
              >
                <div>
                  <p className={`text-xs font-bold uppercase tracking-widest mb-2 ${plan.dark ? "text-blue-400" : "text-gray-500"}`}>
                    {plan.name}
                  </p>
                  <div className="flex items-end gap-1">
                    <span className={`text-4xl font-extrabold ${plan.dark ? "text-white" : "text-gray-900"}`}>
                      {plan.price}
                    </span>
                    <span className={`text-sm mb-1.5 ${plan.dark ? "text-gray-400" : "text-gray-500"}`}>
                      {plan.period}
                    </span>
                  </div>
                </div>

                <ul className="space-y-2.5 flex-1">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2.5">
                      <span className={`mt-0.5 flex-shrink-0 w-4 h-4 rounded-full flex items-center justify-center ${plan.dark ? "bg-blue-500" : "bg-emerald-500"}`}>
                        <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 12 12">
                          <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </span>
                      <span className={`text-sm ${plan.dark ? "text-gray-300" : "text-gray-700"}`}>{f}</span>
                    </li>
                  ))}
                </ul>

                <Link
                  href={plan.href}
                  className={`w-full text-center font-semibold py-3 rounded-lg transition-colors text-sm ${
                    plan.dark
                      ? "bg-blue-500 hover:bg-blue-600 text-white"
                      : "bg-gray-900 hover:bg-gray-800 text-white"
                  }`}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>

          <p className="text-center text-gray-400 text-xs mt-6">
            Pagamento processado com segurança pelo Stripe. Cancele a qualquer momento.
          </p>
        </div>
      </section>

      {/* ── Final CTA ── */}
      <section className="bg-[#111827] py-20 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 to-emerald-500/10" />
        <div className="relative mx-auto max-w-3xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            Pronto para tomar o controle<br />dos seus investimentos?
          </h2>
          <p className="mt-4 text-gray-400 text-base">
            Crie sua conta gratuitamente e comece a usar todas as ferramentas hoje.
            Sem cartão de crédito.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              href="/register"
              className="bg-blue-500 hover:bg-blue-600 text-white font-semibold px-10 py-3.5 rounded-lg transition-colors text-base"
            >
              Criar conta grátis →
            </Link>
            <Link
              href="/login"
              className="text-gray-300 hover:text-white border border-white/20 hover:border-white/40 font-medium px-10 py-3.5 rounded-lg transition-colors text-base"
            >
              Já tenho conta
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="bg-[#0d1117] py-8">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded bg-blue-500 flex items-center justify-center">
              <span className="text-white font-bold text-[10px]">IQ</span>
            </div>
            <span className="text-gray-400 text-sm font-medium">InvestIQ</span>
          </div>
          <div className="flex items-center gap-6">
            <Link href="/tools" className="text-gray-500 hover:text-gray-300 text-xs transition-colors">Ferramentas</Link>
            <Link href="/planos" className="text-gray-500 hover:text-gray-300 text-xs transition-colors">Planos</Link>
            <Link href="/login" className="text-gray-500 hover:text-gray-300 text-xs transition-colors">Entrar</Link>
            <Link href="/register" className="text-gray-500 hover:text-gray-300 text-xs transition-colors">Criar conta</Link>
          </div>
          <p className="text-gray-600 text-xs">© 2025 InvestIQ. Todos os direitos reservados.</p>
        </div>
      </footer>
    </div>
  );
}
