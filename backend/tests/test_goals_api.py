"""Tests for Phase 42 Investment Goals API.

Covers:
  - target_amount = 0 → 422 validation error
  - progress > 100% → status = "concluido"
  - deadline in the past → status = "em_risco"
  - monthly_contribution_needed guarded when months_to_deadline == 0
  - tenant isolation: cannot read/update/delete another tenant's goal
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import register_verify_and_login

pytestmark = pytest.mark.anyio


# ─── Helpers ──────────────────────────────────────────────────────────────────


async def _create_goal(client: AsyncClient, **kwargs) -> dict:
    payload = {
        "name": "Test Goal",
        "target_amount": "10000.00",
        "current_amount": "0",
        **kwargs,
    }
    resp = await client.post("/portfolio/goals", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ─── Tests ────────────────────────────────────────────────────────────────────


async def test_create_goal_target_zero_returns_422(client, email_stub):
    """target_amount = 0 must be rejected by schema validation (CHECK constraint +
    Pydantic gt=0 guard)."""
    await register_verify_and_login(client, email_stub, email="goals1@example.com")
    resp = await client.post("/portfolio/goals", json={
        "name": "Bad goal",
        "target_amount": "0",
    })
    assert resp.status_code == 422


async def test_create_goal_target_negative_returns_422(client, email_stub):
    """Negative target_amount is also rejected."""
    await register_verify_and_login(client, email_stub, email="goals2@example.com")
    resp = await client.post("/portfolio/goals", json={
        "name": "Negative",
        "target_amount": "-500",
    })
    assert resp.status_code == 422


async def test_goal_status_concluido_when_progress_over_100(client, email_stub):
    """When current_amount >= target_amount the status must be 'concluido'
    and progress_pct must be capped at 100 in the progress bar (UI) while
    the raw value may exceed 100."""
    await register_verify_and_login(client, email_stub, email="goals3@example.com")
    goal = await _create_goal(
        client,
        target_amount="1000.00",
        current_amount="1200.00",  # 120% — over-funded
    )
    assert goal["status"] == "concluido"
    assert float(goal["progress_pct"]) >= 100
    assert float(goal["remaining_amount"]) == 0


async def test_goal_status_em_risco_when_deadline_in_past(client, email_stub):
    """A goal with a deadline in the past (months_to_deadline == 0) that has
    not been completed must show status = 'em_risco' and
    monthly_contribution_needed = None (can't compute for a past deadline)."""
    await register_verify_and_login(client, email_stub, email="goals4@example.com")
    goal = await _create_goal(
        client,
        target_amount="50000.00",
        current_amount="1000.00",
        deadline="2020-01-01",  # well in the past
    )
    assert goal["status"] == "em_risco"
    assert goal["months_to_deadline"] == 0
    assert goal["monthly_contribution_needed"] is None


async def test_monthly_contribution_none_when_no_deadline(client, email_stub):
    """Goals without a deadline must have monthly_contribution_needed = None
    because there is no timeframe for the calculation."""
    await register_verify_and_login(client, email_stub, email="goals5@example.com")
    goal = await _create_goal(
        client,
        target_amount="20000.00",
        current_amount="5000.00",
        # no deadline
    )
    assert goal["deadline"] is None
    assert goal["monthly_contribution_needed"] is None


async def test_monthly_contribution_computed_with_future_deadline(client, email_stub):
    """Goals with a future deadline must return monthly_contribution_needed > 0."""
    await register_verify_and_login(client, email_stub, email="goals6@example.com")
    goal = await _create_goal(
        client,
        target_amount="12000.00",
        current_amount="0",
        deadline="2040-12-01",  # far future — always positive months_to_deadline
    )
    assert goal["status"] in ("nao_iniciado", "em_andamento")
    assert goal["months_to_deadline"] is not None
    assert goal["months_to_deadline"] > 0
    monthly = goal["monthly_contribution_needed"]
    assert monthly is not None
    assert float(monthly) > 0


async def test_tenant_isolation_cannot_read_other_tenant_goal(client, email_stub):
    """User A creates a goal. User B lists goals and must NOT see User A's goal."""
    await register_verify_and_login(client, email_stub, email="goalsa@example.com")
    goal = await _create_goal(client, name="User A secret goal")

    # Log in as User B (implicitly logs out A via cookie replacement)
    await register_verify_and_login(client, email_stub, email="goalsb@example.com")
    resp = await client.get("/portfolio/goals")
    assert resp.status_code == 200
    ids = [g["id"] for g in resp.json()]
    assert goal["id"] not in ids


async def test_tenant_isolation_cannot_delete_other_tenant_goal(client, email_stub):
    """User A creates a goal. User B cannot delete it — must get 404."""
    await register_verify_and_login(client, email_stub, email="goalsc@example.com")
    goal = await _create_goal(client, name="Protected goal")

    await register_verify_and_login(client, email_stub, email="goalsd@example.com")
    resp = await client.delete(f"/portfolio/goals/{goal['id']}")
    assert resp.status_code == 404


async def test_update_goal_null_clearing(client, email_stub):
    """PATCH with deadline=null must clear the deadline field (not keep old value).
    This tests the model_dump(exclude_unset=True) fix in service.update_goal."""
    await register_verify_and_login(client, email_stub, email="goalse@example.com")
    goal = await _create_goal(client, deadline="2035-01-01")
    assert goal["deadline"] == "2035-01-01"

    resp = await client.patch(f"/portfolio/goals/{goal['id']}", json={"deadline": None})
    assert resp.status_code == 200
    assert resp.json()["deadline"] is None


async def test_list_goals_empty_for_new_user(client, email_stub):
    """New user starts with an empty goals list."""
    await register_verify_and_login(client, email_stub, email="goalsf@example.com")
    resp = await client.get("/portfolio/goals")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_delete_goal(client, email_stub):
    """Deleting a goal returns 204 and goal disappears from list."""
    await register_verify_and_login(client, email_stub, email="goalsg@example.com")
    goal = await _create_goal(client)

    resp = await client.delete(f"/portfolio/goals/{goal['id']}")
    assert resp.status_code == 204

    resp2 = await client.get("/portfolio/goals")
    assert resp2.status_code == 200
    assert all(g["id"] != goal["id"] for g in resp2.json())
