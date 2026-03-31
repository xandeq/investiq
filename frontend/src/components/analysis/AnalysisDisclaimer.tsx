"use client";

import { AlertTriangle } from "lucide-react";

/**
 * CVM-compliant disclaimer component for analysis pages.
 *
 * Renders a yellow warning alert above analysis content to ensure
 * legal compliance with CVM Res. 19/2021 and Res. 30/2021.
 *
 * Must be visible on every page that displays AI-generated analysis.
 */
export const AnalysisDisclaimer: React.FC = () => (
  <div className="mb-6 rounded-lg border border-yellow-200 bg-yellow-50 p-4 dark:border-yellow-800 dark:bg-yellow-950">
    <div className="flex items-start gap-3">
      <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-yellow-600" />
      <div>
        <h3 className="text-sm font-semibold text-yellow-900 dark:text-yellow-100">
          Análise Informativa — Não é Recomendação Pessoal
        </h3>
        <div className="mt-2 text-sm text-yellow-800 dark:text-yellow-200">
          <p>
            Este conteúdo é apresentado unicamente para fins educacionais e informativos,
            baseado em dados históricos e metodologias de valuation amplamente reconhecidas.
            Não constitui recomendação de investimento pessoal (CVM Res. 19/2021).
          </p>
          <p className="mt-2">
            Consulte um assessor financeiro registrado na CVM antes de tomar decisões
            de investimento com base nesta análise.
          </p>
        </div>
      </div>
    </div>
  </div>
);
