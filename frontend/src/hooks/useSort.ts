import { useState, useMemo } from "react";

export type SortDir = "asc" | "desc";

/**
 * Generic sort hook for client-side table sorting.
 * Handles string, number, and numeric-string values.
 *
 * Usage:
 *   const { sorted, col, dir, toggle } = useSortedData(data, "ticker", "asc");
 */
export function useSortedData<T extends Record<string, unknown>>(
  data: T[],
  defaultCol?: keyof T & string,
  defaultDir: SortDir = "asc"
) {
  const [col, setCol] = useState<(keyof T & string) | null>(defaultCol ?? null);
  const [dir, setDir] = useState<SortDir>(defaultDir);

  function toggle(c: keyof T & string) {
    if (col === c) {
      setDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setCol(c);
      setDir("asc");
    }
  }

  const sorted = useMemo(() => {
    if (!col) return data;
    return [...data].sort((a, b) => {
      const av = a[col];
      const bv = b[col];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      // Try numeric comparison
      const an = typeof av === "number" ? av : typeof av === "string" ? parseFloat(av) : NaN;
      const bn = typeof bv === "number" ? bv : typeof bv === "string" ? parseFloat(bv) : NaN;
      if (!isNaN(an) && !isNaN(bn)) {
        return dir === "asc" ? an - bn : bn - an;
      }
      // String comparison
      const as_ = String(av).toLowerCase();
      const bs_ = String(bv).toLowerCase();
      const cmp = as_.localeCompare(bs_, "pt-BR");
      return dir === "asc" ? cmp : -cmp;
    });
  }, [data, col, dir]);

  return { sorted, col, dir, toggle };
}
