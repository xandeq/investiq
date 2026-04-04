/**
 * Full CVM disclaimer with optional data freshness timestamp.
 * Must be the first visible element above all analysis sections.
 */
interface Props {
  dataTimestamp?: string;
}

export function AnalysisDisclaimer({ dataTimestamp }: Props) {
  return (
    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
      <p className="text-sm text-amber-800 font-medium">
        Análise informativa — não constitui recomendação de investimento pessoal.
        O conteúdo é apresentado unicamente para fins educacionais e informativos,
        baseado em dados históricos e metodologias de valuation amplamente reconhecidas.
        Consulte um assessor financeiro registrado na CVM. (CVM Res. 19/2021, Res. 30/2021)
      </p>
      {dataTimestamp && (
        <p className="text-xs text-amber-600 mt-1">
          Dados de: {new Date(dataTimestamp).toLocaleDateString("pt-BR")}
        </p>
      )}
    </div>
  );
}
