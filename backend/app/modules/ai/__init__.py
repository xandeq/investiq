"""AI Analysis Engine module.

Provides async AI skill adapters (DCF, valuation, earnings, macro impact)
as Celery tasks. All outputs carry mandatory CVM-compliant disclaimers.
AI features are gated behind the Premium plan.
"""
