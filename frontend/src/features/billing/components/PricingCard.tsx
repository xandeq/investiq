import { UpgradeCTA } from "./UpgradeCTA";
import { Check, X } from "lucide-react";

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
    <div className={`rounded-lg flex flex-col gap-6 p-8 transition-all duration-200 ${
      highlighted
        ? "bg-[#111827] text-white hover:scale-[1.02]"
        : "bg-gray-100 hover:bg-gray-200"
    }`}>
      <div>
        <p className={`text-xs font-bold uppercase tracking-wider ${highlighted ? "text-blue-400" : "text-muted-foreground"}`}>
          {name}
        </p>
        <p className={`mt-2 text-5xl font-extrabold tracking-tight ${highlighted ? "text-white" : "text-foreground"}`}>
          {price}
        </p>
        {priceNote && (
          <p className={`mt-1 text-sm ${highlighted ? "text-gray-400" : "text-muted-foreground"}`}>{priceNote}</p>
        )}
      </div>

      <ul className="flex flex-col gap-3">
        {features.map((f) => (
          <li key={f.label} className="flex items-start gap-3 text-sm">
            <span className={`mt-0.5 shrink-0 h-4 w-4 flex items-center justify-center rounded-full ${
              f.included
                ? highlighted ? "bg-blue-500 text-white" : "bg-emerald-500 text-white"
                : "bg-gray-300 text-gray-500"
            }`}>
              {f.included ? <Check className="h-2.5 w-2.5" strokeWidth={3} /> : <X className="h-2.5 w-2.5" strokeWidth={3} />}
            </span>
            <span className={f.included ? (highlighted ? "text-gray-200" : "text-foreground") : (highlighted ? "text-gray-500" : "text-muted-foreground")}>
              {f.label}
            </span>
          </li>
        ))}
      </ul>

      <div className="mt-auto">
        {isCurrentPlan ? (
          <div className={`rounded-md text-sm font-semibold text-center py-3 px-5 ${highlighted ? "bg-white/10 text-white" : "bg-white text-foreground"}`}>
            Plano atual
          </div>
        ) : ctaLabel ? (
          <UpgradeCTA
            label={ctaLabel}
            className={`w-full rounded-md text-sm font-bold py-3 px-5 text-center transition-all duration-200 hover:scale-[1.02] ${
              highlighted ? "bg-blue-500 text-white hover:bg-blue-400" : "bg-[#111827] text-white hover:bg-gray-800"
            }`}
          />
        ) : null}
      </div>
    </div>
  );
}
