import Link from "next/link";
import { AppNav } from "@/components/AppNav";
import { AdminSubscribersContent } from "./AdminSubscribersContent";

const NAV_LINKS = [
  { href: "/admin", label: "Visão Geral" },
  { href: "/admin/subscribers", label: "Assinantes" },
  { href: "/admin/ai-usage", label: "Uso de IA" },
];

export default function AdminSubscribersPage() {
  return (
    <main className="min-h-screen bg-[#111827] text-white">
      <AppNav />
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <div className="mb-6">
          <h1 className="text-2xl font-bold">Assinantes</h1>
          <p className="text-gray-400 text-sm mt-1">Lista de usuários com plano pago e status Stripe</p>
        </div>
        <nav className="flex gap-1 mb-8 bg-white/5 rounded-lg p-1 w-fit">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="px-4 py-2 rounded-md text-sm font-medium transition-colors hover:bg-white/20 text-gray-300"
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <AdminSubscribersContent />
      </div>
    </main>
  );
}
