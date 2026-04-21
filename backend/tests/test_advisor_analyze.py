"""Tests for POST /advisor/analyze and GET /advisor/{job_id} (Phase 24 — ADVI-02)."""
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from tests.conftest import register_verify_and_login


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyze_requires_auth(client: AsyncClient):
    """Unauthenticated POST /advisor/analyze returns 401."""
    resp = await client.post("/advisor/analyze")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_job_requires_auth(client: AsyncClient):
    """Unauthenticated GET /advisor/{job_id} returns 401."""
    resp = await client.get(f"/advisor/{uuid.uuid4()}")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /advisor/analyze
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyze_returns_202_with_job_id(client: AsyncClient, db_session, email_stub):
    """POST /advisor/analyze dispatches Celery task and returns job_id."""
    await register_verify_and_login(
        client, email_stub, email="analyze_start@example.com"
    )

    with patch("app.celery_app.celery_app.send_task") as mock_task:
        resp = await client.post("/advisor/analyze")

    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "pending"
    assert "disclaimer" in data
    # Celery task was dispatched
    mock_task.assert_called_once()
    call_args = mock_task.call_args
    assert call_args[0][0] == "advisor.run_analysis"


@pytest.mark.asyncio
async def test_analyze_stores_job_in_db(client: AsyncClient, db_session, email_stub):
    """POST /advisor/analyze persists a WizardJob row with perfil='advisor'."""
    from sqlalchemy import select
    from app.modules.wizard.models import WizardJob

    await register_verify_and_login(
        client, email_stub, email="analyze_db@example.com"
    )

    with patch("app.celery_app.celery_app.send_task"):
        resp = await client.post("/advisor/analyze")

    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    row = await db_session.execute(select(WizardJob).where(WizardJob.id == job_id))
    job = row.scalar_one_or_none()
    assert job is not None
    assert job.perfil == "advisor"
    assert job.status == "pending"


# ---------------------------------------------------------------------------
# GET /advisor/{job_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_job_not_found(client: AsyncClient, db_session, email_stub):
    """GET /advisor/{unknown_id} returns 404."""
    await register_verify_and_login(
        client, email_stub, email="job_notfound@example.com"
    )
    resp = await client.get(f"/advisor/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_job_pending_status(client: AsyncClient, db_session, email_stub):
    """GET /advisor/{job_id} returns pending status for a newly created job."""
    await register_verify_and_login(
        client, email_stub, email="job_pending@example.com"
    )

    with patch("app.celery_app.celery_app.send_task"):
        start = await client.post("/advisor/analyze")
    job_id = start.json()["job_id"]

    resp = await client.get(f"/advisor/{job_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == job_id
    assert data["status"] == "pending"
    assert data["result"] is None
    assert "disclaimer" in data


@pytest.mark.asyncio
async def test_get_job_completed_with_result(client: AsyncClient, db_session, email_stub):
    """GET /advisor/{job_id} returns structured result when job is completed."""
    from sqlalchemy import update
    from app.modules.wizard.models import WizardJob

    await register_verify_and_login(
        client, email_stub, email="job_completed@example.com"
    )

    with patch("app.celery_app.celery_app.send_task"):
        start = await client.post("/advisor/analyze")
    job_id = start.json()["job_id"]

    # Simulate completed job with structured result
    structured_result = {
        "diagnostico": "Carteira bem diversificada com exposição equilibrada.",
        "pontos_positivos": ["Boa diversificação setorial", "Renda passiva presente"],
        "pontos_de_atencao": ["Concentração em um setor"],
        "sugestoes": ["Considerar renda fixa para equilíbrio"],
        "proximos_passos": ["Revisar alocação trimestral"],
        "disclaimer": "Análise informativa — não constitui recomendação de investimento",
        "health_score": 75,
        "biggest_risk": "60% em Financeiro",
        "passive_income_monthly_brl": "250.00",
        "underperformers": [],
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    await db_session.execute(
        update(WizardJob)
        .where(WizardJob.id == job_id)
        .values(
            status="completed",
            result_json=json.dumps(structured_result),
            completed_at=datetime.now(timezone.utc),
        )
    )
    await db_session.commit()

    resp = await client.get(f"/advisor/{job_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"

    result = data["result"]
    assert result is not None
    assert result["diagnostico"] == structured_result["diagnostico"]
    assert result["pontos_positivos"] == structured_result["pontos_positivos"]
    assert result["pontos_de_atencao"] == structured_result["pontos_de_atencao"]
    assert result["sugestoes"] == structured_result["sugestoes"]
    assert result["proximos_passos"] == structured_result["proximos_passos"]
    assert result["health_score"] == 75


@pytest.mark.asyncio
async def test_get_job_isolation(client: AsyncClient, db_session, email_stub):
    """User A cannot access User B's advisor job."""
    user_a_email = "advisor_a@example.com"
    user_b_email = "advisor_b@example.com"

    await register_verify_and_login(client, email_stub, email=user_a_email)

    with patch("app.celery_app.celery_app.send_task"):
        start = await client.post("/advisor/analyze")
    job_id_a = start.json()["job_id"]

    # Login as User B
    await register_verify_and_login(client, email_stub, email=user_b_email)

    resp = await client.get(f"/advisor/{job_id_a}")
    assert resp.status_code == 404
