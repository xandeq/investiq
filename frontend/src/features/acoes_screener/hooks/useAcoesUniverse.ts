import { useQuery } from "@tanstack/react-query";
import { getAcoesUniverse } from "../api";
import type { AcoesUniverseResponse } from "../types";

export function useAcoesUniverse() {
  return useQuery<AcoesUniverseResponse>({
    queryKey: ["acoes-universe"],
    queryFn: getAcoesUniverse,
    staleTime: 1000 * 60 * 60, // 1h — data refreshed nightly by Celery beat
  });
}
