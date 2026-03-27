"use client";
import Link from "next/link";

interface Props {
  message: string;
  upgradeUrl?: string;
}

export function UpgradeBanner({ message, upgradeUrl = "/planos" }: Props) {
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 flex flex-col sm:flex-row sm:items-center gap-3">
      <p className="flex-1 text-sm text-amber-900">{message}</p>
      <Link
        href={upgradeUrl}
        className="shrink-0 rounded-md bg-primary text-primary-foreground px-4 py-1.5 text-sm font-medium hover:bg-primary/90 transition-colors text-center"
      >
        Ver planos
      </Link>
    </div>
  );
}
