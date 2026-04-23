"""AI provider client with AWS Secrets Manager + auto-fallback.

Four tiers:

FREE tier  — trial/free-plan users:
  Pool of free models rotated randomly. No paid fallback.
  On failure or timeout, the next model in the shuffled list is tried.
  Raises AIProviderError only if every model in the pool fails.

PAID tier  — paying (pro/enterprise) users, standard AI mode:
  1. OpenAI (gpt-4o-mini)
  2. OpenRouter (deepseek/deepseek-chat)
  3. Groq (llama-3.3-70b-versatile)
  If all paid providers fail → falls back to free pool as last resort.

ULTRA tier — pro users with ai_mode="ultra":
  1. Anthropic (claude-sonnet-4-6) — best reasoning + instruction following
  2. OpenAI (gpt-4o) — strong JSON output, reliable
  3. OpenRouter (perplexity/sonar-pro) — adds real-time market context
  4. OpenRouter (deepseek/deepseek-r1) — excellent quantitative reasoning
  5. Gemini (gemini-2.5-pro) — strong analytical fallback
  If all ultra providers fail → falls back to paid chain.

ADMIN tier — internal/admin accounts:
  Free pool first (same as FREE tier).
  If all free models fail → falls back to paid chain as last resort.

Free model pool (confirmed working 2026-03-20):
    groq       - llama-3.1-8b-instant
    groq       - llama-3.3-70b-versatile
    groq       - meta-llama/llama-4-scout-17b-16e-instruct
    groq       - moonshotai/kimi-k2-instruct
    groq       - qwen/qwen3-32b
    groq       - openai/gpt-oss-20b
    cerebras   - llama3.1-8b
    gemini     - gemini-2.5-flash

All keys are fetched from AWS Secrets Manager and cached per process.
"""
from __future__ import annotations

import contextvars
import json
import logging
import os
import random
import subprocess
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level key cache — populated on first call, never hardcoded
# ---------------------------------------------------------------------------
_openai_key: Optional[str] = None
_openrouter_key: Optional[str] = None
_groq_key: Optional[str] = None
_cerebras_key: Optional[str] = None
_gemini_key: Optional[str] = None
_anthropic_key: Optional[str] = None
_perplexity_key: Optional[str] = None


# ---------------------------------------------------------------------------
# Context tracking — set by Celery tasks before running skills
# ---------------------------------------------------------------------------
_ai_ctx: contextvars.ContextVar[dict] = contextvars.ContextVar("ai_ctx", default={})


def set_ai_context(tenant_id: str | None = None, job_id: str | None = None, tier: str = "free") -> None:
    """Call from Celery tasks before running skills to enable per-call usage logging."""
    _ai_ctx.set({"tenant_id": tenant_id, "job_id": job_id, "tier": tier})


def _log_usage(provider: str, model: str, duration_ms: int, success: bool, error: str | None = None) -> None:
    """Insert one row into ai_usage_logs via sync psycopg2. Never raises — logging must not break the main flow."""
    ctx = _ai_ctx.get()
    try:
        import uuid as _uuid
        import psycopg2 as _pg
        raw_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@postgres/investiq")
        # Use superuser URL to bypass RLS (usage logs are not tenant-scoped for admin reads)
        auth_raw = os.environ.get("AUTH_DATABASE_URL", raw_url)
        auth_url = auth_raw.replace("postgresql+asyncpg://", "postgresql://")
        conn = _pg.connect(auth_url)
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO ai_usage_logs
               (id, created_at, tenant_id, job_id, tier, provider, model, duration_ms, success, error)
               VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                str(_uuid.uuid4()),
                ctx.get("tenant_id"),
                ctx.get("job_id"),
                ctx.get("tier", "free"),
                provider,
                model,
                duration_ms,
                success,
                error[:300] if error else None,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("AI usage log failed (non-fatal): %s", exc)


class AIProviderError(Exception):
    """Raised when all configured AI providers fail."""


def _fetch_secret(secret_id: str, key: str) -> Optional[str]:
    """Fetch a single key from AWS Secrets Manager using AWS CLI.

    Runtime env vars take precedence over AWS Secrets Manager.

    This allows production hotfixes and per-environment overrides via `.env`
    or container environment variables without waiting for AWS secret rotation.
    Fallback: checks AWS Secrets Manager only when the environment variable
    is missing or blank.
    """
    env_value = os.environ.get(key)
    if env_value and env_value.strip():
        return env_value.strip()

    try:
        result = subprocess.run(
            [
                "python", "-m", "awscli", "secretsmanager", "get-secret-value",
                "--secret-id", secret_id,
                "--query", "SecretString",
                "--output", "text",
                "--region", "us-east-1",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout.strip())
            return data.get(key)
    except Exception as exc:
        logger.warning("AWS SM fetch failed for %s/%s: %s", secret_id, key, exc)

    return None


def _get_openai_key() -> Optional[str]:
    global _openai_key
    if _openai_key is None:
        _openai_key = _fetch_secret("tools/openai", "OPENAI_API_KEY")
    return _openai_key


def _get_openrouter_key() -> Optional[str]:
    global _openrouter_key
    if _openrouter_key is None:
        _openrouter_key = _fetch_secret("tools/openrouter", "OPENROUTER_API_KEY")
    return _openrouter_key


def _get_groq_key() -> Optional[str]:
    global _groq_key
    if _groq_key is None:
        _groq_key = _fetch_secret("tools/groq", "GROQ_API_KEY")
    return _groq_key


def _get_cerebras_key() -> Optional[str]:
    global _cerebras_key
    if _cerebras_key is None:
        _cerebras_key = _fetch_secret("tools/cerebras", "CEREBRAS_API_KEY")
    return _cerebras_key


def _get_gemini_key() -> Optional[str]:
    global _gemini_key
    if _gemini_key is None:
        _gemini_key = _fetch_secret("tools/gemini", "GEMINI_API_KEY")
    return _gemini_key


def _get_anthropic_key() -> Optional[str]:
    global _anthropic_key
    if _anthropic_key is None:
        _anthropic_key = _fetch_secret("tools/anthropic", "ANTHROPIC_API_KEY")
    return _anthropic_key


def _get_perplexity_key() -> Optional[str]:
    global _perplexity_key
    if _perplexity_key is None:
        _perplexity_key = _fetch_secret("tools/perplexity", "PERPLEXITY_API_KEY")
    return _perplexity_key


def _is_quota_error(status_code: int, body: str) -> bool:
    """Detect quota/billing errors that should trigger provider fallback."""
    if status_code in (402, 429):
        return True
    if status_code == 400 and "insufficient_quota" in body.lower():
        return True
    return False


# ---------------------------------------------------------------------------
# Free-tier model pool — randomly rotated per call
# ---------------------------------------------------------------------------
# Each entry: (provider_name, model_id, api_style)
# api_style: "openai_compat" | "gemini"
_FREE_MODEL_POOL = [
    ("groq", "llama-3.1-8b-instant",                        "openai_compat"),
    ("groq", "llama-3.3-70b-versatile",                     "openai_compat"),
    ("groq", "meta-llama/llama-4-scout-17b-16e-instruct",   "openai_compat"),
    ("groq", "moonshotai/kimi-k2-instruct",                 "openai_compat"),
    ("groq", "qwen/qwen3-32b",                              "openai_compat"),
    ("groq", "openai/gpt-oss-20b",                         "openai_compat"),
    ("cerebras", "llama3.1-8b",                             "openai_compat"),
    ("gemini", "gemini-2.5-flash",                          "gemini"),
]

_PROVIDER_URLS = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "cerebras": "https://api.cerebras.ai/v1/chat/completions",
}

_PROVIDER_KEY_FN = {
    "groq": _get_groq_key,
    "cerebras": _get_cerebras_key,
}


async def _call_openai_compat(
    url: str,
    api_key: str,
    model: str,
    messages: list,
    extra_headers: dict | None = None,
    max_tokens: int = 1500,
) -> str:
    """Call an OpenAI-compatible chat completions endpoint."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            url,
            headers=headers,
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.3,
            },
        )
        body = resp.text
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        raise httpx.HTTPStatusError(
            f"HTTP {resp.status_code}: {body[:200]}", request=resp.request, response=resp
        )


async def _call_gemini(api_key: str, model: str, messages: list) -> str:
    """Call Gemini via REST API."""
    # Convert messages to Gemini format
    parts = []
    system_text = ""
    for m in messages:
        if m["role"] == "system":
            system_text = m["content"]
        elif m["role"] == "user":
            parts.append({"text": m["content"]})

    payload: dict = {"contents": [{"parts": parts}]}
    if system_text:
        payload["system_instruction"] = {"parts": [{"text": system_text}]}

    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json=payload,
        )
        body = resp.text
        if resp.status_code == 200:
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        raise httpx.HTTPStatusError(
            f"HTTP {resp.status_code}: {body[:200]}", request=resp.request, response=resp
        )


async def _call_free_pool(messages: list, max_tokens: int = 1500, label: str = "free") -> str:
    """Try free models in random order until one succeeds.

    Args:
        messages: Chat messages list.
        max_tokens: Max tokens in response.
        label: Log label — "free" or "admin-free".

    Raises:
        AIProviderError: If every free model fails or times out.
    """
    pool = list(_FREE_MODEL_POOL)
    random.shuffle(pool)

    errors = []
    for provider, model, style in pool:
        _t0 = time.time()
        try:
            if style == "gemini":
                key = _get_gemini_key()
                if not key:
                    errors.append(f"gemini/{model}: no key")
                    continue
                content = await _call_gemini(key, model, messages)
            else:
                key_fn = _PROVIDER_KEY_FN.get(provider)
                key = key_fn() if key_fn else None
                if not key:
                    errors.append(f"{provider}/{model}: no key")
                    continue
                url = _PROVIDER_URLS[provider]
                content = await _call_openai_compat(url, key, model, messages, max_tokens=max_tokens)

            logger.info("AI call completed via %s (model=%s) [%s]", provider, model, label)
            _log_usage(provider, model, int((time.time() - _t0) * 1000), True)
            return content

        except httpx.TimeoutException as exc:
            logger.warning("Free model %s/%s timed out — trying next: %s", provider, model, exc)
            _log_usage(provider, model, int((time.time() - _t0) * 1000), False, f"timeout: {exc}")
            errors.append(f"{provider}/{model}: timeout")
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code if exc.response else "?"
            logger.warning(
                "Free model %s/%s failed (HTTP %s) — trying next",
                provider, model, code
            )
            _log_usage(provider, model, int((time.time() - _t0) * 1000), False, f"HTTP {code}")
            errors.append(f"{provider}/{model}: HTTP {code}")
        except Exception as exc:
            logger.warning("Free model %s/%s exception — trying next: %s", provider, model, exc)
            _log_usage(provider, model, int((time.time() - _t0) * 1000), False, str(exc)[:300])
            errors.append(f"{provider}/{model}: {exc}")

    raise AIProviderError(
        f"All free models failed. Errors: {'; '.join(errors[:3])}"
    )


async def _call_anthropic(api_key: str, model: str, messages: list, max_tokens: int = 2000) -> str:
    """Call Anthropic Messages API (claude-* models)."""
    system_text = ""
    user_messages = []
    for m in messages:
        if m["role"] == "system":
            system_text = m["content"]
        else:
            user_messages.append({"role": m["role"], "content": m["content"]})

    payload: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": user_messages,
    }
    if system_text:
        payload["system"] = system_text

    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        body = resp.text
        if resp.status_code == 200:
            return resp.json()["content"][0]["text"]
        raise httpx.HTTPStatusError(
            f"HTTP {resp.status_code}: {body[:200]}", request=resp.request, response=resp
        )


async def _call_ultra_chain(messages: list, max_tokens: int = 2000, label: str = "ultra") -> str:
    """Try premium providers in quality order: Anthropic → GPT-4o → Perplexity → DeepSeek-R1 → Gemini-2.5-Pro.

    Each failure logs usage and moves to the next provider.
    Raises AIProviderError if all ultra providers fail (caller falls back to paid chain).
    """
    # 1. Anthropic claude-sonnet-4-6
    anthropic_key = _get_anthropic_key()
    if anthropic_key:
        _t0 = time.time()
        try:
            content = await _call_anthropic(anthropic_key, "claude-sonnet-4-6", messages, max_tokens=max_tokens)
            logger.info("AI call completed via Anthropic (claude-sonnet-4-6) [%s]", label)
            _log_usage("anthropic", "claude-sonnet-4-6", int((time.time() - _t0) * 1000), True)
            return content
        except httpx.TimeoutException as exc:
            logger.warning("Anthropic timed out — falling back: %s", exc)
            _log_usage("anthropic", "claude-sonnet-4-6", int((time.time() - _t0) * 1000), False, f"timeout: {exc}")
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code if exc.response else 0
            if _is_quota_error(code, str(exc)):
                logger.warning("[QUOTA_ALERT] Anthropic quota/credits exhausted — falling back to GPT-4o")
            else:
                logger.error("Anthropic error — falling back to GPT-4o: %s", exc)
            _log_usage("anthropic", "claude-sonnet-4-6", int((time.time() - _t0) * 1000), False, f"HTTP {code}" + (" [QUOTA]" if _is_quota_error(code, str(exc)) else ""))
        except Exception as exc:
            logger.warning("Anthropic exception — falling back to GPT-4o: %s", exc)
            _log_usage("anthropic", "claude-sonnet-4-6", int((time.time() - _t0) * 1000), False, str(exc)[:300])
    else:
        logger.warning("Anthropic key not available — skipping to GPT-4o")

    # 2. OpenAI gpt-4o (full, not mini)
    openai_key = _get_openai_key()
    if openai_key:
        _t0 = time.time()
        try:
            content = await _call_openai_compat(
                "https://api.openai.com/v1/chat/completions",
                openai_key, "gpt-4o", messages, max_tokens=max_tokens,
            )
            logger.info("AI call completed via OpenAI (gpt-4o) [%s]", label)
            _log_usage("openai", "gpt-4o", int((time.time() - _t0) * 1000), True)
            return content
        except httpx.TimeoutException as exc:
            logger.warning("OpenAI gpt-4o timed out — falling back: %s", exc)
            _log_usage("openai", "gpt-4o", int((time.time() - _t0) * 1000), False, f"timeout: {exc}")
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code if exc.response else 0
            is_quota = _is_quota_error(code, str(exc))
            if is_quota:
                logger.warning("[QUOTA_ALERT] OpenAI (gpt-4o) quota/credits exhausted — falling back to Perplexity")
            else:
                logger.error("OpenAI gpt-4o error — falling back: %s", exc)
            _log_usage("openai", "gpt-4o", int((time.time() - _t0) * 1000), False, f"HTTP {code}" + (" [QUOTA]" if is_quota else ""))
        except Exception as exc:
            logger.warning("OpenAI gpt-4o exception — falling back: %s", exc)
            _log_usage("openai", "gpt-4o", int((time.time() - _t0) * 1000), False, str(exc)[:300])
    else:
        logger.warning("OpenAI key not available — skipping to Perplexity")

    # 3. OpenRouter perplexity/sonar-pro (real-time market context)
    openrouter_key = _get_openrouter_key()
    if openrouter_key:
        _t0 = time.time()
        try:
            content = await _call_openai_compat(
                "https://openrouter.ai/api/v1/chat/completions",
                openrouter_key,
                "perplexity/sonar-pro",
                messages,
                extra_headers={
                    "HTTP-Referer": "https://investiq.com.br",
                    "X-Title": "InvestIQ Ultra Analysis",
                },
                max_tokens=max_tokens,
            )
            logger.info("AI call completed via OpenRouter (perplexity/sonar-pro) [%s]", label)
            _log_usage("openrouter", "perplexity/sonar-pro", int((time.time() - _t0) * 1000), True)
            return content
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code if exc.response else 0
            is_quota = _is_quota_error(code, str(exc))
            if is_quota:
                logger.warning("[QUOTA_ALERT] Perplexity/sonar-pro quota exhausted — falling back to DeepSeek-R1")
            else:
                logger.warning("Perplexity/sonar-pro failed (HTTP %s) — falling back to DeepSeek-R1", code)
            _log_usage("openrouter", "perplexity/sonar-pro", int((time.time() - _t0) * 1000), False, f"HTTP {code}" + (" [QUOTA]" if is_quota else ""))
        except Exception as exc:
            logger.warning("Perplexity/sonar-pro exception — falling back to DeepSeek-R1: %s", exc)
            _log_usage("openrouter", "perplexity/sonar-pro", int((time.time() - _t0) * 1000), False, str(exc)[:300])

    # 4. OpenRouter deepseek/deepseek-r1 (quantitative reasoning)
    if openrouter_key:
        _t0 = time.time()
        try:
            content = await _call_openai_compat(
                "https://openrouter.ai/api/v1/chat/completions",
                openrouter_key,
                "deepseek/deepseek-r1",
                messages,
                extra_headers={
                    "HTTP-Referer": "https://investiq.com.br",
                    "X-Title": "InvestIQ Ultra Analysis",
                },
                max_tokens=max_tokens,
            )
            logger.info("AI call completed via OpenRouter (deepseek/deepseek-r1) [%s]", label)
            _log_usage("openrouter", "deepseek/deepseek-r1", int((time.time() - _t0) * 1000), True)
            return content
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code if exc.response else 0
            is_quota = _is_quota_error(code, str(exc))
            if is_quota:
                logger.warning("[QUOTA_ALERT] DeepSeek-R1 quota exhausted — falling back to Gemini 2.5 Pro")
            else:
                logger.warning("DeepSeek-R1 failed (HTTP %s) — falling back to Gemini 2.5 Pro", code)
            _log_usage("openrouter", "deepseek/deepseek-r1", int((time.time() - _t0) * 1000), False, f"HTTP {code}" + (" [QUOTA]" if is_quota else ""))
        except Exception as exc:
            logger.warning("DeepSeek-R1 exception — falling back to Gemini 2.5 Pro: %s", exc)
            _log_usage("openrouter", "deepseek/deepseek-r1", int((time.time() - _t0) * 1000), False, str(exc)[:300])
    else:
        logger.warning("OpenRouter key not available — skipping to Gemini 2.5 Pro")

    # 5. Gemini 2.5 Pro
    gemini_key = _get_gemini_key()
    if gemini_key:
        _t0 = time.time()
        try:
            content = await _call_gemini(gemini_key, "gemini-2.5-pro", messages)
            logger.info("AI call completed via Gemini (gemini-2.5-pro) [%s]", label)
            _log_usage("gemini", "gemini-2.5-pro", int((time.time() - _t0) * 1000), True)
            return content
        except Exception as exc:
            logger.error("Gemini 2.5 Pro failed: %s", exc)
            _log_usage("gemini", "gemini-2.5-pro", int((time.time() - _t0) * 1000), False, str(exc)[:300])
    else:
        logger.warning("Gemini key not available")

    raise AIProviderError(
        f"All ultra providers failed [{label}]. Check Anthropic/OpenAI/OpenRouter/Gemini keys."
    )


async def _call_paid_chain(messages: list, model: str, max_tokens: int = 1500, label: str = "paid") -> str:
    """Try paid providers: OpenAI → OpenRouter → Groq.

    Args:
        messages: Chat messages list.
        model: Model name for OpenAI (first provider).
        max_tokens: Max tokens in response.
        label: Log label — "paid" or "admin-paid-fallback".

    Raises:
        AIProviderError: If all paid providers fail.
    """
    # Provider 1: OpenAI
    openai_key = _get_openai_key()
    if openai_key:
        _t0 = time.time()
        try:
            content = await _call_openai_compat(
                "https://api.openai.com/v1/chat/completions",
                openai_key, model, messages, max_tokens=max_tokens,
            )
            logger.info("AI call completed via OpenAI (model=%s) [%s]", model, label)
            _log_usage("openai", model, int((time.time() - _t0) * 1000), True)
            return content
        except httpx.TimeoutException as exc:
            logger.warning("OpenAI timed out — falling back: %s", exc)
            _log_usage("openai", model, int((time.time() - _t0) * 1000), False, f"timeout: {exc}")
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code if exc.response else 0
            if _is_quota_error(code, str(exc)):
                logger.warning("OpenAI quota/rate error — falling back to OpenRouter")
            else:
                logger.error("OpenAI error — falling back to OpenRouter: %s", exc)
            _log_usage("openai", model, int((time.time() - _t0) * 1000), False, f"HTTP {code}")
        except Exception as exc:
            logger.warning("OpenAI exception — falling back to OpenRouter: %s", exc)
            _log_usage("openai", model, int((time.time() - _t0) * 1000), False, str(exc)[:300])
    else:
        logger.warning("OpenAI key not available — skipping to OpenRouter")

    # Provider 2: OpenRouter (DeepSeek Chat) — one retry on timeout
    openrouter_key = _get_openrouter_key()
    if openrouter_key:
        for attempt in range(2):
            _t0 = time.time()
            try:
                content = await _call_openai_compat(
                    "https://openrouter.ai/api/v1/chat/completions",
                    openrouter_key,
                    "deepseek/deepseek-chat",
                    messages,
                    extra_headers={
                        "HTTP-Referer": "https://investiq.com.br",
                        "X-Title": "InvestIQ AI Analysis",
                    },
                    max_tokens=max_tokens,
                )
                logger.info("AI call completed via OpenRouter (deepseek/deepseek-chat) [%s]", label)
                _log_usage("openrouter", "deepseek/deepseek-chat", int((time.time() - _t0) * 1000), True)
                return content
            except httpx.TimeoutException as exc:
                _log_usage("openrouter", "deepseek/deepseek-chat", int((time.time() - _t0) * 1000), False, f"timeout attempt {attempt+1}")
                if attempt == 0:
                    logger.warning("OpenRouter timeout attempt 1 — retrying: %s", exc)
                else:
                    logger.error("OpenRouter timeout attempt 2 — falling back to Groq: %s", exc)
            except httpx.HTTPStatusError as exc:
                code = exc.response.status_code if exc.response else 0
                _log_usage("openrouter", "deepseek/deepseek-chat", int((time.time() - _t0) * 1000), False, f"HTTP {code}")
                if _is_quota_error(code, str(exc)):
                    logger.warning("OpenRouter quota/rate error — falling back to Groq")
                else:
                    logger.error("OpenRouter error — falling back to Groq: %s", exc)
                break
            except Exception as exc:
                _log_usage("openrouter", "deepseek/deepseek-chat", int((time.time() - _t0) * 1000), False, str(exc)[:300])
                logger.error("OpenRouter exception — falling back to Groq: %s", exc)
                break
    else:
        logger.warning("OpenRouter key not available — skipping to Groq")

    # Provider 3: Groq (last paid fallback)
    groq_key = _get_groq_key()
    if groq_key:
        _t0 = time.time()
        try:
            content = await _call_openai_compat(
                "https://api.groq.com/openai/v1/chat/completions",
                groq_key,
                "llama-3.3-70b-versatile",
                messages,
                max_tokens=max_tokens,
            )
            logger.info("AI call completed via Groq (llama-3.3-70b-versatile) [%s]", label)
            _log_usage("groq", "llama-3.3-70b-versatile", int((time.time() - _t0) * 1000), True)
            return content
        except httpx.TimeoutException as exc:
            logger.error("Groq timed out: %s", exc)
            _log_usage("groq", "llama-3.3-70b-versatile", int((time.time() - _t0) * 1000), False, f"timeout: {exc}")
        except Exception as exc:
            logger.error("Groq failed: %s", exc)
            _log_usage("groq", "llama-3.3-70b-versatile", int((time.time() - _t0) * 1000), False, str(exc)[:300])
    else:
        logger.warning("Groq key not available")

    raise AIProviderError(
        f"All paid providers failed [{label}]. Check OpenAI/OpenRouter/Groq keys in AWS SM."
    )


async def call_llm(
    prompt: str,
    system: str = "",
    model: str = "gpt-4o-mini",
    tier: str = "free",
    max_tokens: int = 1500,
) -> str:
    """Call an LLM with automatic provider fallback based on user tier.

    Args:
        prompt: User message content.
        system: Optional system/instruction message.
        model: OpenAI model name (used for paid path only).
        tier: Routing tier — one of:
            "free"  → free model pool only (trial/free-plan users).
            "paid"  → paid chain first (OpenAI→OpenRouter→Groq), then free pool as fallback.
            "ultra" → premium chain (Anthropic→GPT-4o→Perplexity→DeepSeek-R1→Gemini-2.5-Pro),
                      then paid chain, then free pool as last resort.
            "admin" → free pool first, paid chain as last resort.
        max_tokens: Maximum tokens in the response.

    Returns:
        Text response from the LLM.

    Raises:
        AIProviderError: If all providers for the tier fail.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    if tier == "free":
        # Free/trial users: free pool only, no paid fallback
        return await _call_free_pool(messages, max_tokens=max_tokens, label="free")

    if tier == "ultra":
        # Ultra users: premium chain → paid chain → free pool (never fail)
        try:
            return await _call_ultra_chain(messages, max_tokens=max(max_tokens, 2000), label="ultra")
        except AIProviderError:
            logger.warning("All ultra providers failed — falling back to paid chain")
        try:
            return await _call_paid_chain(messages, model=model, max_tokens=max_tokens, label="ultra-paid-fallback")
        except AIProviderError:
            logger.warning("All paid providers failed for ultra user — falling back to free pool")
            return await _call_free_pool(messages, max_tokens=max_tokens, label="ultra-free-fallback")

    if tier == "paid":
        # Paying users: paid chain first, free pool as ultimate fallback
        try:
            return await _call_paid_chain(messages, model=model, max_tokens=max_tokens, label="paid")
        except AIProviderError:
            logger.warning("All paid providers failed — falling back to free pool for paid user")
            return await _call_free_pool(messages, max_tokens=max_tokens, label="paid-free-fallback")

    if tier == "admin":
        # Admin: free pool first (save costs), paid chain only if everything free fails
        try:
            return await _call_free_pool(messages, max_tokens=max_tokens, label="admin-free")
        except AIProviderError:
            logger.warning("All free models failed for admin — falling back to paid chain")
            return await _call_paid_chain(messages, model=model, max_tokens=max_tokens, label="admin-paid-fallback")

    # Unknown tier — default to free pool
    logger.warning("Unknown tier '%s' — defaulting to free pool", tier)
    return await _call_free_pool(messages, max_tokens=max_tokens, label=f"unknown-{tier}")
