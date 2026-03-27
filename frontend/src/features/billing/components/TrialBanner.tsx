"use client";
import Link from "next/link";

interface TrialBannerProps {
  daysRemaining: number;
}

export function TrialBanner({ daysRemaining }: TrialBannerProps) {
  const label =
    daysRemaining === 0
      ? "Seu Trial Pro expira hoje"
      : daysRemaining === 1
      ? "1 dia restante no seu Trial Pro"
      : `${daysRemaining} dias restantes no seu Trial Pro`;

  return (
    <div className="w-full bg-blue-600 text-white text-sm py-2 px-4 flex items-center justify-between gap-4">
      <span>
        <span className="font-semibold">Trial Pro gratuito</span> — {label}. Aproveite acesso completo a IA, Screener e sem limites.
      </span>
      <Link
        href="/planos"
        className="shrink-0 bg-white text-blue-600 font-semibold text-xs px-3 py-1 rounded hover:bg-blue-50 transition-colors"
      >
        Fazer upgrade
      </Link>
    </div>
  );
}
