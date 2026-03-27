import { apiClient } from "@/lib/api-client";
import type { SimuladorResponse, PrazoLabel, PerfilLabel } from "./types";

export async function postSimulador(
  valor: number,
  prazo: PrazoLabel,
  perfil: PerfilLabel
): Promise<SimuladorResponse> {
  return apiClient<SimuladorResponse>("/simulador/simulate", {
    method: "POST",
    body: JSON.stringify({ valor, prazo, perfil }),
  });
}
