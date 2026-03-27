export interface InvestorProfile {
  id: string;
  tenant_id: string;
  idade: number | null;
  renda_mensal: string | null;
  patrimonio_total: string | null;
  objetivo: "aposentadoria" | "renda_passiva" | "crescimento" | "reserva" | null;
  horizonte_anos: number | null;
  tolerancia_risco: "conservador" | "moderado" | "arrojado" | null;
  percentual_renda_fixa_alvo: string | null;
  completion_pct: number;
  updated_at: string | null;
}

export interface InvestorProfileUpsert {
  idade?: number | null;
  renda_mensal?: number | null;
  patrimonio_total?: number | null;
  objetivo?: string | null;
  horizonte_anos?: number | null;
  tolerancia_risco?: string | null;
  percentual_renda_fixa_alvo?: number | null;
}
