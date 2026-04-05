import type { FIIPortfolio } from "../types";

interface Props {
  portfolio: FIIPortfolio;
}

function displayValue(value: string | number | null | undefined, suffix?: string): string {
  if (value == null || value === "") return "Dado nao disponivel";
  return suffix ? `${value}${suffix}` : String(value);
}

export function FIIPortfolioSection({ portfolio }: Props) {
  return (
    <div>
      <h3 className="text-sm font-medium mb-3">Portfolio</h3>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-muted/50 rounded-lg p-3">
          <p className="text-xs text-muted-foreground">Numero de Imoveis</p>
          <p className="text-lg font-semibold">{displayValue(portfolio.num_imoveis)}</p>
        </div>
        <div className="bg-muted/50 rounded-lg p-3">
          <p className="text-xs text-muted-foreground">Tipo de Contrato</p>
          <p className="text-lg font-semibold">{displayValue(portfolio.tipo_contrato)}</p>
        </div>
        <div className="bg-muted/50 rounded-lg p-3">
          <p className="text-xs text-muted-foreground">Vacancia</p>
          <p className="text-lg font-semibold">
            {displayValue(
              portfolio.vacancia != null
                ? (portfolio.vacancia * 100).toFixed(1)
                : null,
              "%"
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
