import { apiClient } from "@/lib/api-client";
import type { ComparadorResponse, PrazoLabel } from "./types";

export async function getComparador(
  prazo: PrazoLabel,
  valor?: number
): Promise<ComparadorResponse> {
  const q = new URLSearchParams({ prazo });
  if (valor) q.set("valor", String(valor));
  return apiClient<ComparadorResponse>(`/comparador/compare?${q}`);
}
