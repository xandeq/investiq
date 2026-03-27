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
