"""Integration tests for the AI analysis pipeline.

Tests cover:
- POST /ai/analyze/{ticker} — 202 for pro users, 403 for free users
- POST /ai/analyze/macro — 202 for pro users, 403 for free users
- GET /ai/jobs/{job_id} — returns job status
- GET /ai/jobs — returns list of jobs

All Celery task dispatches are mocked — tasks are not actually executed.
AI provider calls are never made during integration tests.

Setup notes:
- Register + verify + login a "pro" user (set plan="pro" after register)
- Register + verify + login a "free" user (default plan — no modification needed)
- Mock Celery task .delay() to avoid worker dependency
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select, update

from app.modules.auth.models import User
from tests.conftest import register_verify_and_login


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _upgrade_user_to_pro(db_session, user_id: str) -> None:
    """Upgrade a user to pro plan directly in the test DB."""
    await db_session.execute(
        update(User).where(User.id == user_id).values(plan="pro")
    )
    await db_session.flush()


async def _expire_trial(db_session, user_id: str) -> None:
    """Set trial_ends_at to the past so the user is treated as free (no trial)."""
    past = datetime.now(tz=timezone.utc) - timedelta(days=1)
    await db_session.execute(
        update(User).where(User.id == user_id).values(trial_ends_at=past)
    )
    await db_session.flush()


# ---------------------------------------------------------------------------
# Tests: POST /ai/analyze/{ticker}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyze_asset_returns_202_for_pro_user(client, db_session, email_stub):
    """Pro user gets 202 with job_id when requesting asset analysis."""
    user_id = await register_verify_and_login(
        client, email_stub, email="pro@example.com"
    )
    await _upgrade_user_to_pro(db_session, user_id)

    with patch("app.modules.ai.router._dispatch_asset_analysis") as mock_dispatch:
        mock_dispatch.return_value = None
        resp = await client.post("/ai/analyze/VALE3")

    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert data["job_type"] == "asset"
    assert data["ticker"] == "VALE3"


@pytest.mark.asyncio
async def test_analyze_asset_returns_403_for_free_user(client, db_session, email_stub):
    """Free user (expired trial) gets 403 when requesting asset analysis."""
    user_id = await register_verify_and_login(
        client, email_stub, email="free@example.com"
    )
    await _expire_trial(db_session, user_id)

    resp = await client.post("/ai/analyze/VALE3")

    assert resp.status_code == 403, resp.text
    data = resp.json()
    assert "Premium" in data["detail"] or "upgrade" in data["detail"].lower()


@pytest.mark.asyncio
async def test_analyze_asset_returns_401_unauthenticated(client):
    """Unauthenticated request gets 401."""
    resp = await client.post("/ai/analyze/VALE3")
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# Tests: POST /ai/analyze/macro
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyze_macro_returns_202_for_pro_user(client, db_session, email_stub):
    """Pro user gets 202 with job_id when requesting macro analysis."""
    user_id = await register_verify_and_login(
        client, email_stub, email="macro_pro@example.com"
    )
    await _upgrade_user_to_pro(db_session, user_id)

    with patch("app.modules.ai.router._dispatch_macro_analysis") as mock_dispatch:
        mock_dispatch.return_value = None
        resp = await client.post("/ai/analyze/macro")

    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert data["job_type"] == "macro"
    assert data["ticker"] is None


@pytest.mark.asyncio
async def test_analyze_macro_returns_403_for_free_user(client, db_session, email_stub):
    """Free user (expired trial) gets 403 when requesting macro analysis."""
    user_id = await register_verify_and_login(
        client, email_stub, email="macro_free@example.com"
    )
    await _expire_trial(db_session, user_id)

    resp = await client.post("/ai/analyze/macro")

    assert resp.status_code == 403, resp.text


# ---------------------------------------------------------------------------
# Tests: GET /ai/jobs/{job_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_job_returns_job_status(client, db_session, email_stub):
    """GET /ai/jobs/{job_id} returns the job created by POST /ai/analyze/."""
    user_id = await register_verify_and_login(
        client, email_stub, email="poll@example.com"
    )
    await _upgrade_user_to_pro(db_session, user_id)

    with patch("app.modules.ai.router._dispatch_asset_analysis"):
        post_resp = await client.post("/ai/analyze/PETR4")

    assert post_resp.status_code == 202
    job_id = post_resp.json()["id"]

    get_resp = await client.get(f"/ai/jobs/{job_id}")
    assert get_resp.status_code == 200, get_resp.text
    data = get_resp.json()
    assert data["id"] == job_id
    assert data["status"] == "pending"
    assert data["ticker"] == "PETR4"
    assert data["result"] is None  # not yet completed


@pytest.mark.asyncio
async def test_get_job_returns_404_for_unknown_job(client, email_stub):
    """GET /ai/jobs/{job_id} returns 404 when job_id is unknown."""
    await register_verify_and_login(
        client, email_stub, email="notfound@example.com"
    )

    resp = await client.get("/ai/jobs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# Tests: GET /ai/jobs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_jobs_returns_empty_for_new_user(client, email_stub):
    """New user with no jobs gets empty list from GET /ai/jobs."""
    await register_verify_and_login(
        client, email_stub, email="listjobs@example.com"
    )

    resp = await client.get("/ai/jobs")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_jobs_returns_created_jobs(client, db_session, email_stub):
    """GET /ai/jobs returns all jobs created by the authenticated user."""
    user_id = await register_verify_and_login(
        client, email_stub, email="listjobs2@example.com"
    )
    await _upgrade_user_to_pro(db_session, user_id)

    with patch("app.modules.ai.router._dispatch_asset_analysis"):
        await client.post("/ai/analyze/VALE3")
        await client.post("/ai/analyze/PETR4")

    resp = await client.get("/ai/jobs")
    assert resp.status_code == 200, resp.text
    jobs = resp.json()
    assert len(jobs) == 2
    tickers = {j["ticker"] for j in jobs}
    assert tickers == {"VALE3", "PETR4"}


@pytest.mark.asyncio
async def test_list_jobs_tenant_isolation(client, db_session, email_stub):
    """User A cannot see User B's jobs."""
    user_a_id = await register_verify_and_login(
        client, email_stub, email="usera@example.com"
    )
    await _upgrade_user_to_pro(db_session, user_a_id)

    with patch("app.modules.ai.router._dispatch_asset_analysis"):
        await client.post("/ai/analyze/VALE3")

    # User B logs in — should see empty list
    await register_verify_and_login(
        client, email_stub, email="userb@example.com", password="SecurePass123!"
    )
    # Re-login as user B (the client now has user B's cookie after login)
    resp = await client.get("/ai/jobs")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


# ---------------------------------------------------------------------------
# SMOKE TESTS: POST /ai/analyze/portfolio (AI Advisor)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyze_portfolio_returns_202_for_pro_user(client, db_session, email_stub):
    """[SMOKE] Pro user gets 202 + job_id when requesting portfolio analysis."""
    user_id = await register_verify_and_login(
        client, email_stub, email="advisor_pro@example.com"
    )
    await _upgrade_user_to_pro(db_session, user_id)

    with patch("app.modules.ai.router._dispatch_portfolio_analysis") as mock_dispatch:
        mock_dispatch.return_value = None
        resp = await client.post("/ai/analyze/portfolio")

    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert data["job_type"] == "portfolio"
    assert data["ticker"] is None


@pytest.mark.asyncio
async def test_analyze_portfolio_returns_403_for_free_user(client, db_session, email_stub):
    """[SMOKE] Free user (expired trial) gets 403 on portfolio analysis."""
    user_id = await register_verify_and_login(
        client, email_stub, email="advisor_free@example.com"
    )
    await _expire_trial(db_session, user_id)

    resp = await client.post("/ai/analyze/portfolio")

    assert resp.status_code == 403, resp.text
    data = resp.json()
    assert "Premium" in data["detail"] or "upgrade" in data["detail"].lower()


@pytest.mark.asyncio
async def test_analyze_portfolio_returns_401_unauthenticated(client):
    """[SMOKE] Unauthenticated request to portfolio analysis gets 401."""
    resp = await client.post("/ai/analyze/portfolio")
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# REGRESSION TESTS: completed job result parsing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_completed_advisor_job_returns_result(client, db_session, email_stub):
    """[REGRESSION] GET /ai/jobs/{id} returns parsed advisor result when status=completed."""
    import json
    import uuid
    from datetime import datetime, timezone
    from app.modules.ai.models import AIAnalysisJob

    user_id = await register_verify_and_login(
        client, email_stub, email="advisor_result@example.com"
    )
    await _upgrade_user_to_pro(db_session, user_id)

    # Manually insert a completed advisor job
    advisor_payload = {
        "job_id": str(uuid.uuid4()),
        "advisor": {
            "diagnostico": "Carteira concentrada em ações.",
            "pontos_positivos": ["Boa diversificação setorial"],
            "pontos_de_atencao": ["Exposição cambial elevada"],
            "sugestoes": ["Aumentar renda fixa"],
            "proximos_passos": ["Revisar alocação em 30 dias"],
            "disclaimer": "Análise informativa — não constitui recomendação de investimento (CVM Res. 19/2021)",
        },
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    # Get the tenant_id for this user
    from sqlalchemy import select
    from app.modules.auth.models import User
    result = await db_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    tenant_id = str(user.tenant_id)

    job_id = str(uuid.uuid4())
    job = AIAnalysisJob(
        id=job_id,
        tenant_id=tenant_id,
        job_type="portfolio",
        ticker=None,
        status="completed",
        result_json=json.dumps(advisor_payload),
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(job)
    await db_session.flush()

    resp = await client.get(f"/ai/jobs/{job_id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "completed"
    assert data["result"] is not None
    assert data["error_message"] is None
    assert "advisor" in data["result"]
    advisor = data["result"]["advisor"]
    assert advisor["diagnostico"] == "Carteira concentrada em ações."
    assert len(advisor["pontos_positivos"]) == 1
    assert len(advisor["pontos_de_atencao"]) == 1
    assert len(advisor["sugestoes"]) == 1
    assert len(advisor["proximos_passos"]) == 1
    assert "disclaimer" in advisor


@pytest.mark.asyncio
async def test_get_failed_job_returns_null_result(client, db_session, email_stub):
    """[REGRESSION] GET /ai/jobs/{id} returns null result when status=failed."""
    import uuid
    from datetime import datetime, timezone
    from app.modules.ai.models import AIAnalysisJob
    from sqlalchemy import select
    from app.modules.auth.models import User

    user_id = await register_verify_and_login(
        client, email_stub, email="advisor_fail@example.com"
    )

    result = await db_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    tenant_id = str(user.tenant_id)

    job_id = str(uuid.uuid4())
    job = AIAnalysisJob(
        id=job_id,
        tenant_id=tenant_id,
        job_type="portfolio",
        ticker=None,
        status="failed",
        error_message="All AI providers failed.",
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(job)
    await db_session.flush()

    resp = await client.get(f"/ai/jobs/{job_id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "failed"
    assert data["result"] is None
    assert data["error_message"] == "All AI providers failed."


# ---------------------------------------------------------------------------
# INTEGRATION TESTS: full portfolio analysis job flow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_portfolio_analysis_full_flow(client, db_session, email_stub):
    """[INTEGRATION] POST /ai/analyze/portfolio → job created → GET job shows pending."""
    user_id = await register_verify_and_login(
        client, email_stub, email="advisor_flow@example.com"
    )
    await _upgrade_user_to_pro(db_session, user_id)

    with patch("app.modules.ai.router._dispatch_portfolio_analysis") as mock_dispatch:
        mock_dispatch.return_value = None
        post_resp = await client.post("/ai/analyze/portfolio")

    assert post_resp.status_code == 202
    job_id = post_resp.json()["id"]
    assert mock_dispatch.called  # dispatch was invoked

    # Poll the job
    get_resp = await client.get(f"/ai/jobs/{job_id}")
    assert get_resp.status_code == 200
    job_data = get_resp.json()
    assert job_data["id"] == job_id
    assert job_data["job_type"] == "portfolio"
    assert job_data["status"] == "pending"
    assert job_data["result"] is None

    # Job appears in list
    list_resp = await client.get("/ai/jobs")
    assert list_resp.status_code == 200
    ids = [j["id"] for j in list_resp.json()]
    assert job_id in ids


@pytest.mark.asyncio
async def test_portfolio_job_tenant_isolation(client, db_session, email_stub):
    """[INTEGRATION] Portfolio jobs are isolated per tenant — user B cannot see user A's jobs."""
    user_a_id = await register_verify_and_login(
        client, email_stub, email="advisor_tenant_a@example.com"
    )
    await _upgrade_user_to_pro(db_session, user_a_id)

    with patch("app.modules.ai.router._dispatch_portfolio_analysis"):
        await client.post("/ai/analyze/portfolio")

    # Login as user B
    await register_verify_and_login(
        client, email_stub, email="advisor_tenant_b@example.com", password="SecurePass123!"
    )
    resp = await client.get("/ai/jobs")
    assert resp.status_code == 200
    portfolio_jobs = [j for j in resp.json() if j["job_type"] == "portfolio"]
    assert portfolio_jobs == []


@pytest.mark.asyncio
async def test_analyze_portfolio_dispatch_receives_positions_and_tier(client, db_session, email_stub):
    """[INTEGRATION] _dispatch_portfolio_analysis is called with job, positions, pnl, allocation, tier."""
    user_id = await register_verify_and_login(
        client, email_stub, email="advisor_dispatch@example.com"
    )
    await _upgrade_user_to_pro(db_session, user_id)

    with patch("app.modules.ai.router._dispatch_portfolio_analysis") as mock_dispatch:
        mock_dispatch.return_value = None
        resp = await client.post("/ai/analyze/portfolio")

    assert resp.status_code == 202
    assert mock_dispatch.called
    args = mock_dispatch.call_args
    job, positions, pnl, allocation, tier = args[0]
    assert job.job_type == "portfolio"
    # positions/allocation can be empty (no portfolio data in test) — must be list
    assert isinstance(positions, list)
    assert isinstance(allocation, list)
    assert isinstance(pnl, dict)
    assert tier in ("free", "paid", "admin")
