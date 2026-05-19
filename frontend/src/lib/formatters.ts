export const formatBRL = (value: string | number): string =>
  new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
  }).format(typeof value === "string" ? parseFloat(value) : value);

export const formatPct = (value: string | number): string =>
  `${parseFloat(String(value)).toFixed(2)}%`;

export const formatDate = (value: string): string =>
  new Date(value + "T00:00:00").toLocaleDateString("pt-BR");

/** Returns the correct detail page path for a ticker.
 *  FII tickers in Brazil end with 11 (or 12 for rights).
 *  Everything else is treated as a stock. */
export function tickerPath(ticker: string): string {
  const t = ticker.toUpperCase();
  return t.endsWith("11") || t.endsWith("12") ? `/fii/${t}` : `/stock/${t}`;
}
