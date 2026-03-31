"""Shared constants for the AI Analysis module (Phase 12).

Centralizes analysis types, quota limits, and CVM-compliant disclaimers.
"""

# Valid analysis types
ANALYSIS_TYPES = ("dcf", "earnings", "dividend", "sector")

# Monthly quota limits per plan tier
QUOTA_LIMITS = {"free": 0, "pro": 50, "enterprise": 500}

# Full CVM-compliant disclaimer (Portuguese, UTF-8)
CVM_DISCLAIMER_PT = (
    "An\u00e1lise informativa, n\u00e3o constitui recomenda\u00e7\u00e3o de investimento pessoal. "
    "O conte\u00fado \u00e9 apresentado unicamente para fins educacionais e informativos, "
    "baseado em dados hist\u00f3ricos e metodologias de valuation amplamente reconhecidas. "
    "Cada investidor tem sua pr\u00f3pria situa\u00e7\u00e3o financeira, toler\u00e2ncia ao risco "
    "e objetivos. Consulte um assessor financeiro registrado na CVM se precisar de "
    "recomenda\u00e7\u00e3o customizada. (CVM Res. 19/2021, Res. 30/2021)"
)

# Short disclaimer for compact UI elements
CVM_DISCLAIMER_SHORT_PT = (
    "An\u00e1lise informativa, n\u00e3o constitui recomenda\u00e7\u00e3o de investimento pessoal "
    "(CVM Res. 19/2021)"
)
