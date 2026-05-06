"""DIAX cash-flow projection client for Cash Parking Advisor."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import httpx

from app.core.config import settings
from app.modules.cash_flow_advisor.schemas import CashFlowProjection

_CACHE_KEY = "cash_flow_advisor:diax_projection"
_CACHE_TTL_SECONDS = 3600


class DiaxNotConfigured(RuntimeError):
    """Raised when DIAX integration settings are missing."""


class DiaxUnreachable(RuntimeError):
    """Raised when DIAX cannot be reached or returns an invalid response."""


def _camel_to_snake(name: str) -> str:
    out = []
    for char in name:
        if char.isupper():
            out.append("_")
            out.append(char.lower())
        else:
            out.append(char)
    return "".join(out).lstrip("_")


def _normalize_keys(value: Any) -> Any:
    if isinstance(value, list):
        return [_normalize_keys(item) for item in value]
    if isinstance(value, dict):
        return {_camel_to_snake(str(k)): _normalize_keys(v) for k, v in value.items()}
    return value


def _json_default(value: Any) -> str:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


class DiaxClient:
    """Pulls DIAX cash-flow projection with optional Redis caching."""

    def __init__(
        self,
        *,
        redis_client: Any | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._redis = redis_client
        self._http = http_client
        self._owns_http = http_client is None

    async def __aenter__(self) -> "DiaxClient":
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=10)
            self._owns_http = True
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._owns_http and self._http is not None:
            await self._http.aclose()

    async def get_cash_flow_projection(self) -> CashFlowProjection:
        if not settings.DIAX_BASE_URL or not settings.DIAX_INTEGRATION_KEY:
            raise DiaxNotConfigured("DIAX_BASE_URL and DIAX_INTEGRATION_KEY are required")

        cached = await self._cache_get()
        if cached is not None:
            return cached

        http_client = self._http or httpx.AsyncClient(timeout=10)
        close_after = self._http is None
        try:
            response = await http_client.get(
                f"{settings.DIAX_BASE_URL.rstrip('/')}/api/v1/integrations/cash-flow-projection",
                headers={"X-Integration-Key": settings.DIAX_INTEGRATION_KEY},
            )
            response.raise_for_status()
            data = _normalize_keys(response.json())
            projection = CashFlowProjection(**data, fetched_at=datetime.now(timezone.utc))
            await self._cache_set(projection)
            return projection
        except httpx.HTTPError as exc:
            raise DiaxUnreachable(str(exc)) from exc
        finally:
            if close_after:
                await http_client.aclose()

    async def _cache_get(self) -> CashFlowProjection | None:
        if self._redis is None:
            return None
        raw = await self._redis.get(_CACHE_KEY)
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return CashFlowProjection(**_normalize_keys(json.loads(raw)))

    async def _cache_set(self, projection: CashFlowProjection) -> None:
        if self._redis is None:
            return
        payload = json.dumps(
            projection.model_dump(mode="json", by_alias=False),
            default=_json_default,
        )
        # Keep cache payload compatible with DIAX's public camelCase contract.
        payload = payload.replace("current_balance", "currentBalance")
        payload = payload.replace("available_to_invest", "availableToInvest")
        payload = payload.replace("next_big_outflow", "nextBigOutflow")
        payload = payload.replace("daily_projection", "dailyProjection")
        payload = payload.replace("opening_balance", "openingBalance")
        payload = payload.replace("total_income", "totalIncome")
        payload = payload.replace("total_expenses", "totalExpenses")
        payload = payload.replace("closing_balance", "closingBalance")
        payload = payload.replace("is_negative", "isNegative")
        payload = payload.replace("has_high_priority_expense", "hasHighPriorityExpense")
        await self._redis.setex(_CACHE_KEY, _CACHE_TTL_SECONDS, payload)
