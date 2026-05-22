"use client";
import { useCallback, useEffect, useRef } from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";

interface UseFilterStateOptions<K extends string> {
  /** Keys map to URL param names. Values are defaults (empty string = no filter). */
  defaults: Record<K, string>;
  /** localStorage key for persistence. */
  storageKey: string;
}

interface UseFilterStateReturn<K extends string> {
  values: Record<K, string>;
  set: (key: K, value: string) => void;
  clear: () => void;
}

/**
 * Syncs filter state to URL search params (primary) + localStorage (persistence seed).
 * URL is the single source of truth — localStorage only seeds the URL on first load.
 * Enables deep-linking and session persistence with zero extra state variables.
 */
export function useFilterState<K extends string>({
  defaults,
  storageKey,
}: UseFilterStateOptions<K>): UseFilterStateReturn<K> {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const seededRef = useRef(false);

  // Derive current values purely from URL params
  const values = {} as Record<K, string>;
  for (const key of Object.keys(defaults) as K[]) {
    values[key] = searchParams.get(key) ?? defaults[key];
  }

  // On mount: if URL has no filter params, seed from localStorage
  useEffect(() => {
    if (seededRef.current) return;
    seededRef.current = true;

    const hasUrlFilters = (Object.keys(defaults) as K[]).some(
      (k) => searchParams.get(k) !== null
    );
    if (hasUrlFilters) return;

    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return;
      const stored = JSON.parse(raw) as Partial<Record<K, string>>;
      const params = new URLSearchParams(searchParams.toString());
      let changed = false;
      for (const key of Object.keys(defaults) as K[]) {
        const v = stored[key];
        if (v && v !== defaults[key]) {
          params.set(key, v);
          changed = true;
        }
      }
      if (changed) {
        router.replace(`${pathname}?${params.toString()}`, { scroll: false });
      }
    } catch {
      // corrupt localStorage — ignore
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Persist URL params to localStorage whenever they change
  useEffect(() => {
    try {
      const toStore: Partial<Record<K, string>> = {};
      for (const key of Object.keys(defaults) as K[]) {
        const v = searchParams.get(key);
        if (v !== null) toStore[key] = v;
      }
      if (Object.keys(toStore).length > 0) {
        localStorage.setItem(storageKey, JSON.stringify(toStore));
      }
    } catch {
      // ignore
    }
  }, [searchParams, defaults, storageKey]);

  const set = useCallback(
    (key: K, value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (!value || value === defaults[key]) {
        params.delete(key);
      } else {
        params.set(key, value);
      }
      const qs = params.toString();
      router.replace(`${pathname}${qs ? `?${qs}` : ""}`, { scroll: false });
    },
    [searchParams, defaults, router, pathname]
  );

  const clear = useCallback(() => {
    router.replace(pathname, { scroll: false });
    try {
      localStorage.removeItem(storageKey);
    } catch {
      // ignore
    }
  }, [router, pathname, storageKey]);

  return { values, set, clear };
}
