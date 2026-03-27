import { apiClient } from "@/lib/api-client";
import type { WizardStartResponse, WizardJobResponse, PrazoLabel, PerfilLabel } from "./types";

export async function startWizard(perfil: PerfilLabel, prazo: PrazoLabel, valor: number): Promise<WizardStartResponse> {
  return apiClient<WizardStartResponse>("/wizard/start", {
    method: "POST",
    body: JSON.stringify({ perfil, prazo, valor }),
  });
}

export async function getWizardJob(jobId: string): Promise<WizardJobResponse> {
  return apiClient<WizardJobResponse>(`/wizard/${jobId}`);
}
