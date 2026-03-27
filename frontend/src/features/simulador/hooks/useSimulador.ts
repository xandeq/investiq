"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { postSimulador } from "../api";
import type { PrazoLabel, PerfilLabel } from "../types";

interface SimuladorParams {
  valor: number;
  prazo: PrazoLabel;
  perfil: PerfilLabel;
}

export function useSimulador() {
  const [params, setParams] = useState<SimuladorParams | null>(null);

  const query = useQuery({
    queryKey: ["simulador", params],
    queryFn: () =>
      postSimulador(params!.valor, params!.prazo, params!.perfil),
    enabled: params !== null,
    staleTime: 5 * 60 * 1000,
  });

  return { ...query, params, setParams };
}
