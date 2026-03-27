import Link from "next/link";

/**
 * Auth route group layout — split two-column, no top nav.
 * Wraps login, register, verify-email, forgot-password, reset-password pages.
 */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex">
      {/* Left column — branding (hidden on mobile) */}
      <div className="hidden lg:flex lg:w-1/2 bg-[#111827] relative overflow-hidden flex-col justify-between p-12">
        {/* Decorative shapes */}
        <div className="absolute -top-24 -left-24 h-96 w-96 rounded-full bg-blue-500/10" />
        <div className="absolute top-1/3 -right-16 h-64 w-64 rounded-full bg-emerald-500/10" />
        <div className="absolute bottom-12 left-1/4 h-48 w-48 rounded-full bg-blue-500/5" />

        {/* Logo + nav link */}
        <div className="relative z-10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-md bg-blue-500 flex items-center justify-center">
              <span className="text-white font-bold text-sm">IQ</span>
            </div>
            <span className="text-white font-bold text-xl tracking-tight">InvestIQ</span>
          </div>
          <Link
            href="/tools"
            className="text-gray-300 hover:text-white text-xs font-medium border border-white/20 hover:border-white/40 px-3 py-1.5 rounded-full transition-colors"
          >
            Ver ferramentas →
          </Link>
        </div>

        {/* Tagline */}
        <div className="relative z-10 space-y-8">
          <div>
            <h2 className="text-4xl font-extrabold text-white tracking-tight leading-tight">
              Inteligência institucional<br />para o investidor moderno.
            </h2>
            <p className="mt-4 text-gray-400 text-base">
              Gerencie sua carteira, acompanhe P&L em tempo real e obtenha análises de IA personalizadas.
            </p>
          </div>

          <ul className="space-y-4">
            {[
              { icon: "📊", text: "Dashboard com patrimônio e alocação em tempo real" },
              { icon: "🤖", text: "Copiloto de IA com análise macro e diagnóstico de carteira" },
              { icon: "🔔", text: "Alertas automáticos de watchlist e insights diários" },
            ].map(({ icon, text }) => (
              <li key={text} className="flex items-start gap-3">
                <span className="text-lg mt-0.5">{icon}</span>
                <span className="text-gray-300 text-sm">{text}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative z-10 text-gray-600 text-xs">© 2025 InvestIQ. Todos os direitos reservados.</p>
      </div>

      {/* Right column — form */}
      <div className="flex-1 flex items-center justify-center px-6 py-12 bg-white">
        <div className="w-full max-w-md space-y-8">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2 justify-center">
            <div className="h-8 w-8 rounded-md bg-blue-500 flex items-center justify-center">
              <span className="text-white font-bold text-xs">IQ</span>
            </div>
            <span className="font-bold text-lg tracking-tight">InvestIQ</span>
          </div>

          {/* Form card */}
          <div className="bg-gray-50 rounded-lg p-8">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
