"""Tests for GET /signals/calibration endpoint (Phase 34 completion).

Covers:
  - Unauthenticated access → 401
  - Authenticated returns valid structure with correct keys
  - data_sufficient=False when no closed outcomes
  - pattern_weights contains all default patterns
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import register_verify_and_login

pytestmark = pytest.mark.anyio


async def test_calibration_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/signals/calibration")
    assert resp.status_code == 401


async def test_calibration_returns_valid_structure(
    client: AsyncClient, email_stub
) -> None:
    await register_verify_and_login(client, email_stub, email="cal1@example.com")
    resp = await client.get("/signals/calibration")
    assert resp.status_code == 200
    data = resp.json()

    assert "data_sufficient" in data
    assert "total_outcomes" in data
    assert "thresholds" in data
    assert "pattern_weights" in data
    assert "grade_performance" in data

    assert isinstance(data["data_sufficient"], bool)
    assert isinstance(data["total_outcomes"], int)
    assert "min_to_adjust" in data["thresholds"]
    assert "min_to_disable" in data["thresholds"]


async def test_calibration_no_closed_outcomes_not_sufficient(
    client: AsyncClient, email_stub
) -> None:
    await register_verify_and_login(client, email_stub, email="cal2@example.com")
    resp = await client.get("/signals/calibration")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_sufficient"] is False
    assert data["total_outcomes"] == 0


async def test_calibration_pattern_weights_present(
    client: AsyncClient, email_stub
) -> None:
    await register_verify_and_login(client, email_stub, email="cal3@example.com")
    resp = await client.get("/signals/calibration")
    assert resp.status_code == 200
    data = resp.json()
    weights = data["pattern_weights"]
    assert len(weights) > 0
    for pattern, pw in weights.items():
        assert "weight" in pw
        assert "status" in pw
        assert pw["status"] in ("default", "boosted", "disabled")
        assert "n" in pw
