"""Opportunity Detector module — Phase 1 MVP.

Monitors BR stocks, crypto, and fixed income for significant price drops or
above-average rates. Analyzes cause via 4-agent AI pipeline and dispatches
multi-channel alerts (Telegram + Email).

Phase 1: hardcoded asset list + single destination (admin alerts).
Phase 2 (future): per-user watchlist + Stripe tier gating.
"""
