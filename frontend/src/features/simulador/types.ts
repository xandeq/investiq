export type PrazoLabel = "6m" | "1a" | "2a" | "5a";
export type PerfilLabel = "conservador" | "moderado" | "arrojado";
export type CenarioKey = "pessimista" | "base" | "otimista";

export interface AllocationClass {
  pct: string;
  valor: string;
}

export interface AllocationBreakdown {
  acoes: AllocationClass;
  fiis: AllocationClass;
  renda_fixa: AllocationClass;
  caixa: AllocationClass;
}

export interface ClassResult {
  asset_class: string;
  label: string;
  pct_alocado: string;
  valor_alocado: string;
  retorno_bruto_pct: string;
  ir_rate_pct: string;
  retorno_liquido_pct: string;
  valor_final: string;
  is_exempt: boolean;
}

export interface Cenario {
  nome: string;
  key: CenarioKey;
  total_investido: string;
  total_bruto: string;
  total_liquido: string;
  retorno_bruto_pct: string;
  retorno_liquido_pct: string;
  classes: ClassResult[];
}

export interface CurrentClassAllocation {
  pct: string;
  valor: string;
}

export interface RebalancingItem {
  asset_class: string;
  label: string;
  current_pct: string;
  ideal_pct: string;
  delta_pct: string;
  action: string; // adicionar | reduzir | manter
  valor_delta: string;
}

export interface PortfolioDelta {
  total_portfolio: string;
  current_allocation: Record<string, CurrentClassAllocation>;
  rebalancing: RebalancingItem[];
}

export interface SimuladorResponse {
  perfil: string;
  prazo: string;
  holding_days: number;
  valor_inicial: string;
  disclaimer: string;
  allocation: AllocationBreakdown;
  cenarios: Cenario[];
  portfolio_delta: PortfolioDelta | null;
  cdi_annual_pct: string | null;
}
