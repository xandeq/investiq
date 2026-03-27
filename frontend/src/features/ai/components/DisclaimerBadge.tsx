/**
 * CVM-compliant disclaimer badge.
 * Must appear on every AI result panel — never hidden.
 * No 'use client' needed — pure display component.
 */

const CVM_DISCLAIMER =
  "Análise informativa — não constitui recomendação de investimento (CVM Res. 19/2021)";

export function DisclaimerBadge() {
  return (
    <div className="mt-3 rounded-md bg-amber-50 border border-amber-200 px-3 py-2">
      <p className="text-xs text-amber-700 font-medium">{CVM_DISCLAIMER}</p>
    </div>
  );
}
