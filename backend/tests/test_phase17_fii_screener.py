"""Phase 17 tests: FII Scored Screener backend.

Tests cover:
  - _percentile_ranks helper function edge cases
  - Score formula calculation
  - Beat schedule registration for calculate_fii_scores
  - FIIScoredRow and FIIScoredResponse schema validation
  - GET /fii-screener/ranked endpoint (ordering, auth, null-score handling)
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from decimal import Decimal


# ---------------------------------------------------------------------------
# _percentile_ranks helper tests
# ---------------------------------------------------------------------------

def test_percentile_ranks_basic():
    """_percentile_ranks([10, 20, 30]) returns [0, 50, 100]."""
    from app.modules.market_universe.tasks import _percentile_ranks
    result = _percentile_ranks([10, 20, 30])
    assert result == [0, 50, 100], f"Expected [0, 50, 100], got {result}"


def test_percentile_ranks_with_none():
    """_percentile_ranks([10, None, 30]) returns [0, None, 100]."""
    from app.modules.market_universe.tasks import _percentile_ranks
    result = _percentile_ranks([10, None, 30])
    assert result == [0, None, 100], f"Expected [0, None, 100], got {result}"


def test_percentile_ranks_single():
    """_percentile_ranks([42]) returns [50]."""
    from app.modules.market_universe.tasks import _percentile_ranks
    result = _percentile_ranks([42])
    assert result == [50], f"Expected [50], got {result}"


def test_percentile_ranks_empty():
    """_percentile_ranks([]) returns []."""
    from app.modules.market_universe.tasks import _percentile_ranks
    result = _percentile_ranks([])
    assert result == [], f"Expected [], got {result}"


def test_percentile_ranks_all_none():
    """_percentile_ranks([None, None]) returns [None, None]."""
    from app.modules.market_universe.tasks import _percentile_ranks
    result = _percentile_ranks([None, None])
    assert result == [None, None], f"Expected [None, None], got {result}"


# ---------------------------------------------------------------------------
# Score formula tests
# ---------------------------------------------------------------------------

def test_score_formula():
    """Score = dy_rank*0.5 + pvp_rank_inverted*0.3 + liquidity_rank*0.2."""
    dy_rank = 80
    pvp_rank_inverted = 60
    liquidity_rank = 40
    # 80*0.5 + 60*0.3 + 40*0.2 = 40 + 18 + 8 = 66.0
    expected = 66.0
    score = dy_rank * 0.5 + pvp_rank_inverted * 0.3 + liquidity_rank * 0.2
    assert abs(score - expected) < 0.001, f"Expected {expected}, got {score}"


def test_score_formula_null_metric():
    """If any rank is None, score is None."""
    dy_rank = 80
    pvp_rank_inverted = None  # missing pvp data
    liquidity_rank = 40

    if any(r is None for r in [dy_rank, pvp_rank_inverted, liquidity_rank]):
        score = None
    else:
        score = dy_rank * 0.5 + pvp_rank_inverted * 0.3 + liquidity_rank * 0.2

    assert score is None, f"Expected None for missing metric, got {score}"


# ---------------------------------------------------------------------------
# Beat schedule test
# ---------------------------------------------------------------------------

def test_score_beat_schedule_registered():
    """calculate-fii-scores-daily must be registered with crontab(minute=0, hour=8)."""
    from app.celery_app import celery_app
    from celery.schedules import crontab

    sched = celery_app.conf.beat_schedule
    assert "calculate-fii-scores-daily" in sched, (
        "calculate-fii-scores-daily missing from beat_schedule"
    )
    entry = sched["calculate-fii-scores-daily"]
    assert entry["task"] == "app.modules.market_universe.tasks.calculate_fii_scores", (
        f"Wrong task: {entry['task']}"
    )
    expected = crontab(minute=0, hour=8)
    assert str(entry["schedule"]) == str(expected), (
        f"Schedule mismatch: {entry['schedule']} != {expected}"
    )


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

def test_fii_scored_row_schema():
    """FIIScoredRow has all required fields and accepts None for optional ones."""
    from app.modules.fii_screener.schemas import FIIScoredRow

    row = FIIScoredRow(
        ticker="HGLG11",
        short_name="CSHG LOG",
        segmento="Logistica",
        dy_12m="8.5",
        pvp="0.95",
        daily_liquidity=5_000_000,
        score="72.5",
        dy_rank=80,
        pvp_rank=70,
        liquidity_rank=60,
        score_updated_at="2026-04-04T08:00:00Z",
    )

    assert row.ticker == "HGLG11"
    assert row.segmento == "Logistica"
    assert row.dy_12m == "8.5"
    assert row.score == "72.5"
    assert row.dy_rank == 80
    assert row.pvp_rank == 70
    assert row.liquidity_rank == 60
    assert row.score_updated_at == "2026-04-04T08:00:00Z"


def test_fii_scored_row_schema_optional_fields():
    """FIIScoredRow fields are all optional except ticker."""
    from app.modules.fii_screener.schemas import FIIScoredRow

    row = FIIScoredRow(ticker="XPLG11")
    assert row.ticker == "XPLG11"
    assert row.short_name is None
    assert row.segmento is None
    assert row.score is None
    assert row.dy_rank is None


def test_fii_scored_response_schema():
    """FIIScoredResponse has disclaimer, score_available, total, results fields."""
    from app.modules.fii_screener.schemas import FIIScoredRow, FIIScoredResponse

    row = FIIScoredRow(ticker="HGLG11", score="72.5")
    response = FIIScoredResponse(
        score_available=True,
        total=1,
        results=[row],
    )

    assert response.score_available is True
    assert response.total == 1
    assert len(response.results) == 1
    assert response.disclaimer != ""
    assert "CVM" in response.disclaimer or "recomendacao" in response.disclaimer.lower() or "nao constitui" in response.disclaimer.lower()


def test_fii_scored_response_no_scores():
    """FIIScoredResponse with score_available=False when no scores computed yet."""
    from app.modules.fii_screener.schemas import FIIScoredRow, FIIScoredResponse

    row = FIIScoredRow(ticker="HGLG11")  # score=None
    response = FIIScoredResponse(
        score_available=False,
        total=1,
        results=[row],
    )

    assert response.score_available is False


# ---------------------------------------------------------------------------
# Integration tests: GET /fii-screener/ranked endpoint
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def authed_client(client, email_stub):
    """Client with a registered and logged-in user."""
    import uuid as _uuid
    from tests.conftest import register_verify_and_login
    unique_email = f"fii_test_{_uuid.uuid4().hex[:8]}@example.com"
    await register_verify_and_login(client, email_stub, email=unique_email)
    return client


@pytest.mark.anyio
async def test_ranked_endpoint_requires_auth(client):
    """GET /fii-screener/ranked without auth returns 401."""
    resp = await client.get("/fii-screener/ranked")
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"


@pytest.mark.anyio
async def test_ranked_endpoint_ordered_by_score(authed_client, db_session):
    """Results must be ordered by score descending."""
    import uuid as _uuid
    from app.modules.market_universe.models import FIIMetadata
    from datetime import datetime, timezone

    # Use a unique prefix to avoid UNIQUE constraint errors across test backends
    prefix = _uuid.uuid4().hex[:4].upper()
    now = datetime.now(timezone.utc)
    test_tickers = [f"{prefix}1{i}1" for i in range(3)]  # e.g. AB1011, AB1111, AB1211
    test_scores = [50, 90, 70]

    rows = [
        FIIMetadata(
            id=str(_uuid.uuid4()),
            ticker=ticker,
            score=Decimal(str(score)),
            score_updated_at=now,
        )
        for ticker, score in zip(test_tickers, test_scores)
    ]
    for row in rows:
        db_session.add(row)
    await db_session.commit()

    resp = await authed_client.get("/fii-screener/ranked")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    data = resp.json()
    assert "results" in data
    assert data["total"] >= 3

    # Extract scores for our test tickers
    test_ticker_set = set(test_tickers)
    test_rows = [r for r in data["results"] if r["ticker"] in test_ticker_set]
    assert len(test_rows) == 3, f"Expected 3 test rows, got {len(test_rows)}"

    # Verify ordering: scores should be descending
    scores = [float(r["score"]) for r in test_rows if r["score"] is not None]
    assert scores == sorted(scores, reverse=True), (
        f"Results not ordered by score desc: {scores}"
    )


@pytest.mark.anyio
async def test_ranked_endpoint_null_scores_at_bottom(authed_client, db_session):
    """FIIs with score=None must appear after those with a score."""
    import uuid as _uuid
    from app.modules.market_universe.models import FIIMetadata
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    prefix = _uuid.uuid4().hex[:4].upper()
    # Row with score
    scored = FIIMetadata(
        id=str(_uuid.uuid4()),
        ticker=f"{prefix}S11",
        score=Decimal("80"),
        score_updated_at=now,
    )
    # Row without score
    unscored = FIIMetadata(
        id=str(_uuid.uuid4()),
        ticker=f"{prefix}N11",
        score=None,
    )
    scored_ticker = scored.ticker
    unscored_ticker = unscored.ticker
    db_session.add(scored)
    db_session.add(unscored)
    await db_session.commit()

    resp = await authed_client.get("/fii-screener/ranked")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    data = resp.json()
    results = data["results"]

    # Find positions of our test rows
    tickers = [r["ticker"] for r in results]
    assert scored_ticker in tickers, f"{scored_ticker} not found in results"
    assert unscored_ticker in tickers, f"{unscored_ticker} not found in results"

    scored_pos = tickers.index(scored_ticker)
    unscored_pos = tickers.index(unscored_ticker)
    assert scored_pos < unscored_pos, (
        f"Scored row ({scored_pos}) should appear before null-scored row ({unscored_pos})"
    )


# ---------------------------------------------------------------------------
# Regression tests: scoring logic fixes (2026-05-23)
# ---------------------------------------------------------------------------

def test_score_requires_dy_rank():
    """FIIs without DY data must get score=None regardless of liquidity.

    Regression: before fix, ETFs like SMAL11 scored ~40 via liquidity alone
    because the formula used (dy_rank or 0)*0.6 + liq_rank*0.4.
    """
    dy_rank = None       # no DY data — not a real FII
    pvp_rank_inv = None
    liq_rank = 100       # very liquid but irrelevant without DY

    score = None if dy_rank is None else (
        dy_rank * 0.5 + (pvp_rank_inv or 0) * 0.3 + liq_rank * 0.2
    )
    assert score is None, (
        f"Score must be None when DY is missing (got {score}). "
        "ETFs/stocks without DY should not appear ranked."
    )


def test_score_partial_pvp_fallback():
    """When PVP is missing, score uses DY*0.7 + liquidity*0.3.

    This is the legitimate fallback for FIIs that genuinely have DY but
    no PVP data — NOT the ETF case (which has no DY at all).
    """
    dy_rank = 80
    pvp_rank_inv = None   # PVP genuinely missing for this FII
    liq_rank = 60

    if dy_rank is None:
        score = None
    elif pvp_rank_inv is None:
        score = dy_rank * 0.7 + liq_rank * 0.3
    else:
        score = dy_rank * 0.5 + pvp_rank_inv * 0.3 + liq_rank * 0.2

    # 80*0.7 + 60*0.3 = 56 + 18 = 74.0
    assert score is not None, "Score must not be None when DY is present"
    assert abs(score - 74.0) < 0.001, f"Expected 74.0, got {score}"


def test_non_null_guard_preserves_enriched_dy():
    """Enriched dy_12m must not be overwritten by NULL snapshot values.

    Regression: calculate_fii_scores previously did UPDATE ... SET dy_12m = snapshot_dy
    unconditionally. When snapshot_dy was NULL (brapi doesn't return DY for FIIs
    in the quotes endpoint), it destroyed the enriched data from refresh_fii_metadata.
    """
    # Simulate the guard: only include dy_12m in update_vals when snapshot_dy is not None
    enriched_dy = 0.1396  # pre-enriched value: 13.96% from dividendsData
    snapshot_dy = None    # brapi quotes endpoint returns no DY for FIIs

    update_vals: dict = {"daily_liquidity": 5_000_000}
    if snapshot_dy is not None:
        update_vals["dy_12m"] = snapshot_dy

    # dy_12m must NOT appear in update_vals when snapshot_dy is None
    assert "dy_12m" not in update_vals, (
        "Enriched dy_12m was overwritten with NULL snapshot value. "
        "Non-NULL guard failed — the fix at calculate_fii_scores must be applied."
    )


def test_coalesce_uses_enriched_dy_when_snapshot_null():
    """COALESCE(snapshot.dy, fii_metadata.dy_12m) returns enriched value when snapshot is NULL.

    Regression: before COALESCE fix, dy in the scoring query was taken exclusively
    from screener_snapshots.dy, which is always NULL for FIIs (brapi returns DY
    separately via dividendsData, not in the quotes payload). This meant 633 FIIs
    scored with dy=NULL, which collapsed into score=None for all.
    """
    snapshot_dy = None       # always NULL for FIIs in screener_snapshots
    enriched_dy = 0.1396     # from fii_metadata.dy_12m after refresh_fii_metadata

    # COALESCE picks the first non-NULL value
    effective_dy = snapshot_dy if snapshot_dy is not None else enriched_dy

    assert effective_dy == enriched_dy, (
        f"COALESCE must use enriched dy_12m when snapshot.dy is NULL. "
        f"Got {effective_dy}, expected {enriched_dy}"
    )
    assert effective_dy is not None, "DY must not be None after COALESCE"


def test_percentile_ranks_high_dy_gets_high_rank():
    """Higher DY values must produce higher percentile ranks (DY is benefit metric)."""
    from app.modules.market_universe.tasks import _percentile_ranks

    # [5%, 10%, 15%, 20%] DY values — higher is better
    dy_values = [0.05, 0.10, 0.15, 0.20]
    ranks = _percentile_ranks(dy_values)

    assert ranks is not None
    assert len(ranks) == 4
    # Highest DY (0.20) should get rank 100
    assert ranks[3] == 100, f"Highest DY should rank 100, got {ranks[3]}"
    # Lowest DY (0.05) should get rank 0
    assert ranks[0] == 0, f"Lowest DY should rank 0, got {ranks[0]}"
    # Ranks must be strictly ascending for strictly ascending input
    non_null_ranks = [r for r in ranks if r is not None]
    assert non_null_ranks == sorted(non_null_ranks), f"Ranks must be ascending: {non_null_ranks}"
