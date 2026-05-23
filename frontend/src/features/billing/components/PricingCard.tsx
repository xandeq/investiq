import { Check, X } from "@phosphor-icons/react";
import { UpgradeCTA } from "./UpgradeCTA";

interface Feature { label: string; included: boolean; }

interface Props {
  name: string;
  price: string;
  priceNote?: string;
  features: Feature[];
  highlighted?: boolean;
  ctaLabel?: string;
  isCurrentPlan?: boolean;
}

export function PricingCard({ name, price, priceNote, features, highlighted = false, ctaLabel, isCurrentPlan = false }: Props) {
  return (
    <div className={`rounded-xl flex flex-col gap-6 p-8 transition-all duration-200 ${
      highlighted
        ? "bg-zinc-900 text-white"
        : "bg-zinc-100 hover:bg-zinc-200"
    }`}>
      <div>
        <p className={`text-xs font-bold uppercase tracking-wider ${highlighted ? "text-blue-400" : "text-zinc-400"}`}>
          {name}
        </p>
        <p className={`mt-2 text-5xl font-extrabold tracking-tight ${highlighted ? "text-white" : "text-zinc-900"}`}>
          {price}
        </p>
        {priceNote && (
          <p className={`mt-1 text-sm ${highlighted ? "text-zinc-400" : "text-zinc-400"}`}>{priceNote}</p>
        )}
      </div>

      <ul className="flex flex-col gap-3">
        {features.map((f) => (
          <li key={f.label} className="flex items-start gap-3 text-sm">
            <span className={`mt-0.5 shrink-0 h-4 w-4 flex items-center justify-center rounded-full ${
              f.included
                ? highlighted ? "bg-blue-500 text-white" : "bg-emerald-500 text-white"
                : "bg-zinc-300 text-zinc-500"
            }`}>
              {f.included ? <Check className="h-2.5 w-2.5" weight="bold" /> : <X className="h-2.5 w-2.5" weight="bold" />}
            </span>
            <span className={f.included ? (highlighted ? "text-zinc-200" : "text-zinc-800") : (highlighted ? "text-zinc-500" : "text-zinc-400")}>
              {f.label}
            </span>
          </li>
        ))}
      </ul>

      <div className="mt-auto">
        {isCurrentPlan ? (
          <div className={`rounded-lg text-sm font-semibold text-center py-3 px-5 ${highlighted ? "bg-white/10 text-white" : "bg-white text-zinc-800"}`}>
            Plano atual
          </div>
        ) : ctaLabel ? (
          <UpgradeCTA
            label={ctaLabel}
            className={`w-full rounded-lg text-sm font-bold py-3 px-5 text-center active:scale-[0.97] transition-all duration-150 ${
              highlighted ? "bg-blue-500 text-white hover:bg-blue-400" : "bg-zinc-900 text-white hover:bg-zinc-800"
            }`}
          />
        ) : null}
      </div>
    </div>
  );
}
