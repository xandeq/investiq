"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/features/auth/hooks/useAuth";
import { useSubscription } from "@/features/billing/hooks/useSubscription";
import { TrialBanner } from "@/features/billing/components/TrialBanner";
import { apiClient } from "@/lib/api-client";
import {
  SquaresFour,
  Briefcase,
  ArrowsLeftRight,
  Brain,
  Eye,
  ListChecks,
  Lightning,
  User,
  UploadSimple,
  CreditCard,
  Scroll,
  SignOut,
  MagnifyingGlass,
  CaretDown,
  ChartBar,
  Sparkle,
  Calculator,
  Bank,
  Buildings,
  ChartPie,
  Lightbulb,
  Wallet,
  Pulse,
} from "@phosphor-icons/react";

interface UnreadCountResponse {
  count: number;
}

function useInsightsUnreadCount() {
  const { data } = useQuery<UnreadCountResponse>({
    queryKey: ["insights-unread-count"],
    queryFn: () => apiClient<UnreadCountResponse>("/insights/unread-count"),
    staleTime: 60 * 1000,
    refetchInterval: 60 * 1000,
  });
  return data?.count ?? 0;
}

function InsightsBadge() {
  const count = useInsightsUnreadCount();
  if (count === 0) return null;
  return (
    <span className="bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center leading-none shrink-0">
      {count > 9 ? "9+" : count}
    </span>
  );
}

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
  exact?: boolean;
}

interface NavGroup {
  label: string;
  icon: React.ElementType;
  /** Paths that make this group "active" */
  activePrefixes: string[];
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Portfólio",
    icon: Briefcase,
    activePrefixes: ["/portfolio", "/imports", "/ir-helper"],
    items: [
      { href: "/portfolio", label: "Visão Geral", icon: Briefcase, exact: true },
      { href: "/portfolio/transactions", label: "Transações", icon: ArrowsLeftRight },
      { href: "/imports", label: "Importar", icon: UploadSimple },
      { href: "/ir-helper", label: "IR Helper", icon: Calculator },
    ],
  },
  {
    label: "Mercado",
    icon: ChartBar,
    activePrefixes: ["/watchlist", "/screener", "/renda-fixa", "/comparador", "/simulador", "/wizard", "/fii", "/caixa"],
    items: [
      { href: "/watchlist", label: "Watchlist", icon: Eye },
      { href: "/screener/acoes", label: "Ações", icon: MagnifyingGlass },
      { href: "/screener/fiis", label: "FIIs", icon: Buildings },
      { href: "/fii/screener", label: "FII Screener", icon: MagnifyingGlass },
      { href: "/renda-fixa", label: "Renda Fixa", icon: Bank },
      { href: "/caixa", label: "Caixa", icon: Wallet },
      { href: "/comparador", label: "Comparador", icon: ChartBar },
      { href: "/simulador", label: "Simulador", icon: ChartPie },
      { href: "/wizard", label: "Onde Investir", icon: Lightbulb },
      { href: "/screener", label: "Triagem IA", icon: MagnifyingGlass, exact: true },
    ],
  },
  {
    label: "IA & Análise",
    icon: Sparkle,
    activePrefixes: ["/ai", "/insights", "/opportunity-detector", "/swing-trade", "/inteligencia"],
    items: [
      { href: "/ai/advisor", label: "Advisor de Carteira", icon: Brain },
      { href: "/ai", label: "Análise de Ativo", icon: Brain, exact: true },
      { href: "/insights", label: "Insights", icon: ListChecks },
      { href: "/opportunity-detector", label: "Oportunidades", icon: Lightning },
      { href: "/swing-trade", label: "Swing Trade", icon: Pulse },
      { href: "/inteligencia", label: "Inteligência", icon: Scroll },
    ],
  },
  {
    label: "Conta",
    icon: User,
    activePrefixes: ["/profile", "/planos"],
    items: [
      { href: "/profile", label: "Perfil", icon: User },
      { href: "/planos", label: "Planos", icon: CreditCard },
    ],
  },
];

function AdminDropdown({ pathname }: { pathname: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const isActive = pathname.startsWith("/admin");

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => { setOpen(false); }, [pathname]);

  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen(v => !v)}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200 whitespace-nowrap shrink-0 ${
          isActive ? "bg-amber-500 text-white" : "text-amber-400 hover:text-white hover:bg-amber-500/20"
        }`}>
        <Scroll className="h-3.5 w-3.5 shrink-0" />
        <span className="hidden sm:block">Admin</span>
        <CaretDown className={`h-3 w-3 shrink-0 transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="absolute left-0 top-full mt-1 z-50 min-w-[160px] rounded-lg bg-[#1f2937] border border-white/10 shadow-xl overflow-hidden">
          {[
            { href: "/admin/logs", label: "Logs do Sistema", icon: Scroll },
            { href: "/admin/ai-usage", label: "AI Usage", icon: Pulse },
            { href: "/admin/subscribers", label: "Assinantes", icon: CreditCard },
          ].map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href}
              className={`flex items-center gap-2.5 px-4 py-2.5 text-xs font-medium transition-colors ${
                pathname === href ? "bg-amber-500 text-white" : "text-zinc-300 hover:bg-white/10 hover:text-white"
              }`}>
              <Icon className="h-3.5 w-3.5 shrink-0" />
              {label}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function NavDropdown({
  group,
  pathname,
}: {
  group: NavGroup;
  pathname: string;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const isGroupActive = group.activePrefixes.some((p) =>
    pathname.startsWith(p)
  );

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200 whitespace-nowrap ${
          isGroupActive
            ? "bg-blue-500 text-white"
            : "text-zinc-400 hover:text-white hover:bg-white/10"
        }`}
      >
        <group.icon className="h-3.5 w-3.5 shrink-0" />
        <span className="hidden sm:block">{group.label}</span>
        <CaretDown
          className={`h-3 w-3 shrink-0 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div className="absolute left-0 top-full mt-1 z-50 min-w-[180px] rounded-lg bg-[#1f2937] border border-white/10 shadow-xl overflow-hidden">
          {group.items.map(({ href, label, icon: Icon, exact }) => {
            const isActive = exact ? pathname === href : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-2.5 px-4 py-2.5 text-xs font-medium transition-colors duration-150 ${
                  isActive
                    ? "bg-blue-500 text-white"
                    : "text-zinc-300 hover:bg-white/10 hover:text-white"
                }`}
              >
                <Icon className="h-3.5 w-3.5 shrink-0" />
                <span className="flex-1">{label}</span>
                {href === "/insights" && <InsightsBadge />}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function AppNav() {
  const pathname = usePathname();
  const { logout } = useAuth();
  const { isAdmin, isTrial, daysRemaining } = useSubscription();

  const isDashboard = pathname === "/dashboard";

  return (
    <div>
      {isTrial && <TrialBanner daysRemaining={daysRemaining} />}
    <nav className="bg-[#111827] text-white">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-14 items-center gap-1">
          {/* Logo */}
          <Link href="/dashboard" className="flex items-center gap-2 mr-4 shrink-0">
            <div className="h-7 w-7 rounded-md bg-blue-500 flex items-center justify-center">
              <span className="text-white font-bold text-xs">IQ</span>
            </div>
            <span className="font-bold text-sm tracking-tight hidden sm:block">InvestIQ</span>
          </Link>

          {/* Nav items */}
          <div className="flex items-center gap-0.5 flex-1 min-w-0">
            {/* Dashboard — standalone link */}
            <Link
              href="/dashboard"
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200 whitespace-nowrap shrink-0 ${
                isDashboard
                  ? "bg-blue-500 text-white"
                  : "text-zinc-400 hover:text-white hover:bg-white/10"
              }`}
            >
              <SquaresFour className="h-3.5 w-3.5 shrink-0" />
              <span className="hidden sm:block">Dashboard</span>
            </Link>

            {/* Dropdown groups */}
            {NAV_GROUPS.map((group) => (
              <NavDropdown key={group.label} group={group} pathname={pathname} />
            ))}

            {/* Admin — only for admins */}
            {isAdmin && (
              <AdminDropdown pathname={pathname} />
            )}
          </div>

          {/* Logout */}
          <button
            onClick={logout}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-red-400 hover:text-white hover:bg-red-500/20 transition-all duration-200 shrink-0 ml-1"
          >
            <SignOut className="h-3.5 w-3.5" />
            <span className="hidden sm:block">Sair</span>
          </button>
        </div>
      </div>
    </nav>
    </div>
  );
}
