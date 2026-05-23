"""FastAPI router for /signals endpoints.

GET  /signals/active            — list active A+ signals from Redis (auth required)
GET  /signals/calibration       — pattern weights + grade performance stats
GET  /signals/{ticker}/evaluate — on-demand evaluation for a specific ticker
POST /signals/sizing            — calculate Kelly fractional position size
"""
import json
import logging
import os

import redis.asyncio as aioredis
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.core.middleware import get_authed_db, get_current_tenant_id
from app.core.security import get_current_user
from app.modules.chart_analyzer.analyzer import analyze
from app.modules.signal_engine.calibration import PATTERN_WEIGHTS, MIN_SAMPLES_TO_ADJUST, MIN_SAMPLES_TO_DISABLE
from app.modules.signal_engine.gates import evaluate_signal
from app.modules.signal_engine.kelly import calculate_position_size
from app.modules.signal_engine.scanner import get_active_signals
from app.modules.outcome_tracker.service import get_stats, get_expectancy_by_pattern

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_async_redis():
    url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    try:
        return aioredis.from_url(url, decode_responses=True)
    except Exception as exc:
        logger.warning("signal_engine router: Redis unavailable: %s", exc)
        return None


async def _get_news_context(redis_client, tickers: list[str]) -> dict[str, list[str]]:
    """Read cached news headlines per ticker from Redis (set by ingest_news_events task)."""
    if redis_client is None or not tickers:
        return {}
    news: dict[str, list[str]] = {}
    import json as _json
    for ticker in tickers:
        try:
            raw = await redis_client.get(f"news:ticker:{ticker}:recent")
            if raw:
                news[ticker] = _json.loads(raw)
        except Exception:
            pass
    return news


@router.get("/active")
@limiter.limit("30/minute")
async def list_active_signals(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Return current A+ signals cached in Redis, enriched with recent news context.

    Returns an empty list if no signals are available (scanner hasn't run yet
    or market is closed).
    """
    redis_client = _get_async_redis()
    try:
        signals = await get_active_signals(redis_client)
        if signals:
            tickers = [s["ticker"] for s in signals]
            news_ctx = await _get_news_context(redis_client, tickers)
            for signal in signals:
                signal["news_context"] = news_ctx.get(signal["ticker"], [])
    finally:
        if redis_client is not None:
            try:
                await redis_client.aclose()
            except Exception:
                pass

    return {"signals": signals, "count": len(signals)}


@router.get("/calibration")
@limiter.limit("10/minute")
async def get_calibration_stats(
    request: Request,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Return pattern calibration stats and grade performance.

    Shows current pattern weights (boosted/disabled/default), per-grade
    winrate/avg-R, and pattern expectancy — enabling users to see which
    setups are performing vs underperforming.

    Requires ≥ MIN_SAMPLES_TO_ADJUST closed outcomes per pattern to calibrate.
    """
    # Fetch outcome stats (grade breakdown)
    stats = await get_stats(db, tenant_id)
    total_closed = stats.get("total_closed", 0)

    # Fetch pattern expectancy from DB
    pattern_exp = await get_expectancy_by_pattern(db, tenant_id)

    # Read current weights from Redis (fall back to in-memory defaults)
    redis_client = _get_async_redis()
    current_weights: dict[str, float] = {}
    try:
        if redis_client is not None:
            raw = await redis_client.get("signal_engine:pattern_weights")
            if raw:
                current_weights = json.loads(raw)
    except Exception:
        pass
    finally:
        if redis_client is not None:
            try:
                await redis_client.aclose()
            except Exception:
                pass

    if not current_weights:
        current_weights = dict(PATTERN_WEIGHTS)

    # Build pattern weight status
    pattern_weights_out = {}
    for pattern, weight in current_weights.items():
        if weight == 0.0:
            w_status = "disabled"
        elif weight > 1.0:
            w_status = "boosted"
        else:
            w_status = "default"
        exp_data = pattern_exp.get(pattern)
        pattern_weights_out[pattern] = {
            "weight": weight,
            "status": w_status,
            "n": exp_data["n"] if exp_data else 0,
            "expectancy": exp_data["expectancy"] if exp_data else None,
            "win_rate": exp_data["win_rate"] if exp_data else None,
        }

    return {
        "data_sufficient": total_closed >= MIN_SAMPLES_TO_ADJUST,
        "total_outcomes": total_closed,
        "thresholds": {
            "min_to_adjust": MIN_SAMPLES_TO_ADJUST,
            "min_to_disable": MIN_SAMPLES_TO_DISABLE,
        },
        "pattern_weights": pattern_weights_out,
        "grade_performance": stats.get("grade_breakdown", {}),
    }


@router.get("/{ticker}/evaluate")
@limiter.limit("20/minute")
async def evaluate_ticker_signal(
    request: Request,
    ticker: str,
    current_user: dict = Depends(get_current_user),
):
    """On-demand A+ gate evaluation for a specific B3 ticker.

    Runs a full chart analysis and applies all 10 gates. Useful for
    evaluating tickers outside the default UNIVERSE.
    """
    ticker = ticker.upper()
    if not ticker or len(ticker) > 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ticker")

    brapi_token = os.environ.get("BRAPI_TOKEN", "")

    redis_client = _get_async_redis()
    try:
        analysis = await analyze(ticker, brapi_token=brapi_token, redis_client=redis_client)
    finally:
        if redis_client is not None:
            try:
                await redis_client.aclose()
            except Exception:
                pass

    if analysis.get("error") and not analysis.get("indicators"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to analyze {ticker}: {analysis['error']}",
        )

    evaluation = evaluate_signal(ticker, analysis)

    return {
        "ticker": ticker,
        "grade": evaluation.grade,
        "score": evaluation.score,
        "passed_gates": evaluation.passed_gates,
        "total_gates": evaluation.total_gates,
        "is_a_plus": evaluation.is_a_plus,
        "setup": evaluation.setup,
        "gates": [
            {
                "gate_name": g.gate_name,
                "passed": g.passed,
                "value": g.value,
                "threshold": g.threshold,
                "reason": g.reason,
            }
            for g in evaluation.gates
        ],
    }


_RATIONALE_CACHE_PREFIX = "copilot:rationale:"
_RATIONALE_CACHE_TTL = 6 * 3600  # 6h


@router.get("/{ticker}/rationale")
@limiter.limit("10/minute")
async def get_ticker_rationale(
    request: Request,
    ticker: str,
    current_user: dict = Depends(get_current_user),
):
    """Generate an AI rationale for a ticker's signal state.

    Uses signal evaluation + sentiment context to produce a 2-3 sentence
    investor-friendly explanation. Cached in Redis for 6h to control LLM costs.
    Falls back to a template string if the LLM call fails.
    """
    ticker = ticker.upper()
    if not ticker or len(ticker) > 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ticker")

    brapi_token = os.environ.get("BRAPI_TOKEN", "")
    redis_client = _get_async_redis()

    # Check cache first
    cache_key = f"{_RATIONALE_CACHE_PREFIX}{ticker}"
    if redis_client is not None:
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                import json as _json
                data = _json.loads(cached)
                data["cached"] = True
                return data
        except Exception:
            pass

    # Fetch signal evaluation and sentiment concurrently
    try:
        analysis = await analyze(ticker, brapi_token=brapi_token, redis_client=redis_client)
    except Exception as exc:
        logger.warning("rationale: analyze failed for %s: %s", ticker, exc)
        analysis = {}

    evaluation = evaluate_signal(ticker, analysis)

    sentiment_score: float | None = None
    reddit_mentions: int = 0
    try:
        from app.modules.briefing_engine.context_assembler import get_context_batch
        batch = await get_context_batch([ticker], hours=24, redis_client=redis_client)
        ctx = batch.get(ticker, {})
        sentiment_score = ctx.get("sentiment_score")
        reddit_mentions = ctx.get("reddit_mentions", 0)
    except Exception as exc:
        logger.debug("rationale: sentiment fetch failed for %s: %s", ticker, exc)

    if redis_client is not None:
        try:
            await redis_client.aclose()
        except Exception:
            pass

    # Build context for LLM prompt
    grade = evaluation.grade
    setup = evaluation.setup
    passed = evaluation.passed_gates
    total = evaluation.total_gates
    is_a_plus = evaluation.is_a_plus

    sentiment_label = "neutro"
    if sentiment_score is not None:
        if sentiment_score > 0.3:
            sentiment_label = "positivo"
        elif sentiment_score < -0.2:
            sentiment_label = "negativo"

    setup_block = ""
    if setup:
        setup_block = (
            f"Padrão: {setup.get('pattern', '?')}, R/R: {float(setup.get('rr', 0)):.1f}x, "
            f"entrada: {float(setup.get('entry', 0)):.2f}, stop: {float(setup.get('stop', 0)):.2f}, "
            f"alvo: {float(setup.get('target_1', 0)):.2f}."
        )

    prompt = (
        f"Você é um analista técnico sênior explicando uma análise para um investidor brasileiro.\n\n"
        f"Ticker: {ticker}\n"
        f"Nota técnica: {grade} ({passed}/{total} condições satisfeitas)\n"
        f"Setup ativo: {'sim' if is_a_plus else 'não'}\n"
        f"{setup_block}\n"
        f"Sentimento social (últimas 24h): {sentiment_label}"
        + (f" (score={sentiment_score:+.2f}, {reddit_mentions} menções)" if sentiment_score is not None else "")
        + "\n\n"
        "Escreva 2-3 frases concisas explicando o estado atual do setup em linguagem simples para o investidor. "
        "Mencione o que está favorável ou desfavorável. Não use markdown. Não use listas. "
        "Tom analítico, objetivo, sem promessas de retorno."
    )

    # Determine confidence string
    confidence = "baixa"
    if is_a_plus and sentiment_score is not None and sentiment_score > 0.3:
        confidence = "alta"
    elif is_a_plus or (sentiment_score is not None and sentiment_score > 0.1):
        confidence = "média"

    rationale: str
    try:
        from app.modules.ai.provider import call_llm
        rationale = await call_llm(
            prompt=prompt,
            system="Responda apenas com o texto do analista, sem introduções ou assinaturas.",
            tier="free",
            max_tokens=200,
        )
        rationale = rationale.strip()
    except Exception as exc:
        logger.warning("rationale: LLM call failed for %s: %s", ticker, exc)
        # Fallback template
        pattern = setup.get("pattern", "completo") if setup else "completo"
        if is_a_plus and sentiment_label == "positivo":
            rationale = (
                f"Setup técnico {grade} ({pattern}) confirmado com "
                f"sentimento positivo nas redes sociais. Condições técnicas e de mercado convergem — "
                f"aguardar entrada na zona definida com stop respeitado."
            )
        elif is_a_plus:
            rationale = (
                f"Setup técnico {grade} confirmado ({pattern}), "
                f"mas o sentimento nas redes está {sentiment_label}. "
                "Aguardar confluência antes de entrar."
            )
        else:
            rationale = (
                f"{passed} de {total} condições técnicas satisfeitas — setup ainda incompleto. "
                "Monitorar para formação de confluências adicionais."
            )

    result = {"ticker": ticker, "rationale": rationale, "confidence": confidence, "cached": False}

    # Cache successful result
    if redis_client is not None or True:  # write via a new connection
        new_redis = _get_async_redis()
        if new_redis is not None:
            try:
                import json as _json
                await new_redis.setex(cache_key, _RATIONALE_CACHE_TTL, _json.dumps(result))
            except Exception:
                pass
            finally:
                try:
                    await new_redis.aclose()
                except Exception:
                    pass

    return result


class SizingRequest(BaseModel):
    book_value: Decimal
    entry: Decimal
    stop: Decimal
    win_rate: float = 0.5
    avg_win_r: float = 2.5
    open_positions: int = 0
    daily_pnl_pct: float = 0.0


@router.post("/sizing")
@limiter.limit("20/minute")
async def calculate_sizing(
    request: Request,
    body: SizingRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Calculate Kelly fractional position size with risk guardrails.

    Returns allocation fraction, BRL amount, share count, and any blocking
    reasons (drawdown limit, max open positions).
    """
    result = calculate_position_size(
        book_value=body.book_value,
        entry=body.entry,
        stop=body.stop,
        win_rate=body.win_rate,
        avg_win_r=body.avg_win_r,
        open_positions=body.open_positions,
        daily_pnl_pct=body.daily_pnl_pct,
    )
    # Convert Decimal to float for JSON serialization
    result["amount_brl"] = float(result["amount_brl"])
    return result
