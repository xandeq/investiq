"""AI skill adapters for InvestIQ analysis engine.

Each skill is an async function that:
1. Accepts market data / portfolio context as plain dicts
2. Calls call_llm() from provider.py
3. Returns a structured dict with 'disclaimer' key always present

CVM compliance: every response includes the mandatory disclaimer text.
"""

DISCLAIMER_TEXT = (
    "Análise informativa — não constitui recomendação de investimento "
    "(CVM Res. 19/2021)"
)
