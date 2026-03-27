"""GPT-4o vision-based last-resort parser for broker PDFs.

Used when both correpy and pdfplumber return empty results. Converts PDF pages
to images and sends them to GPT-4o with a structured extraction prompt.

IMPORTANT: This function is SYNCHRONOUS — called from a Celery task.
Use requests library (not httpx.AsyncClient) for the API call.

API key is fetched from AWS Secrets Manager using the same pattern as
app.modules.ai.provider. The function is self-contained to avoid circular deps.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import subprocess
from decimal import Decimal
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

# Module-level key cache — fetched once per worker process
_openai_key: Optional[str] = None


def _fetch_secret(secret_id: str, key: str) -> Optional[str]:
    """Fetch a single key from AWS Secrets Manager via CLI subprocess.

    Mirrors the pattern in app.modules.ai.provider — copied to avoid circular deps.
    Falls back to environment variable if AWS CLI fails.
    """
    import os
    # Check env var first (test/CI environments)
    env_key = key.upper().replace("-", "_")
    env_val = os.environ.get(env_key)
    if env_val:
        return env_val

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
        if result.returncode == 0:
            secret_json = json.loads(result.stdout.strip())
            return secret_json.get(key)
    except Exception as exc:
        logger.warning("gpt4o_parser: failed to fetch secret %s: %s", secret_id, exc)

    return None


def _get_openai_key() -> Optional[str]:
    """Return cached OpenAI API key (fetched from AWS SM on first call)."""
    global _openai_key
    if _openai_key is None:
        _openai_key = _fetch_secret("tools/openai", "OPENAI_API_KEY")
    return _openai_key


_EXTRACTION_PROMPT = """You are analyzing a Brazilian broker nota de corretagem (brokerage note) PDF image.

Extract ALL stock transactions from this image and return them as a JSON array.
Each object must have these exact fields:
- "ticker": string — B3 ticker symbol (e.g. "PETR4", "VALE3", "ITUB4")
- "transaction_type": "buy" or "sell" — C=compra=buy, V=venda=sell
- "transaction_date": "YYYY-MM-DD" string — date of the transaction
- "quantity": number — number of shares (integer)
- "unit_price": number — price per share in BRL (decimal)
- "total_value": number — total transaction value in BRL (quantity * unit_price)
- "irrf_withheld": number — IRRF tax withheld (0 if not shown)

Return ONLY the JSON array with no extra text. Example:
[{"ticker":"PETR4","transaction_type":"buy","transaction_date":"2025-01-15","quantity":100,"unit_price":38.50,"total_value":3850.00,"irrf_withheld":0}]

If no transactions found, return an empty array: []"""


def parse_with_gpt4o(pdf_bytes: bytes) -> list[dict[str, Any]]:
    """Extract transactions from a broker PDF using GPT-4o vision.

    Converts each PDF page to a JPEG image (150 DPI) and sends them all
    to GPT-4o in a single request for structured extraction.

    Args:
        pdf_bytes: Raw bytes of the PDF file.

    Returns:
        List of transaction dicts with parser_source="gpt4o".
        Returns empty list on any error or if GPT-4o returns no transactions.
    """
    api_key = _get_openai_key()
    if not api_key:
        logger.warning("gpt4o_parser: no OpenAI API key available — skipping GPT-4o")
        return []

    try:
        from pdf2image import convert_from_bytes

        # Convert PDF to images at 150 DPI — sufficient for text extraction
        images = convert_from_bytes(pdf_bytes, dpi=150, fmt="jpeg")
        if not images:
            logger.debug("gpt4o_parser: pdf2image returned no images")
            return []

        # Encode images as base64 JPEG
        image_contents = []
        for img in images[:5]:  # max 5 pages to control token cost
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            image_contents.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{b64}",
                    "detail": "high",
                },
            })

        # Build GPT-4o request
        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": _EXTRACTION_PROMPT}]
                + image_contents,
            }
        ]

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o",
                "messages": messages,
                "max_tokens": 2000,
                "temperature": 0,
            },
            timeout=60,
        )
        response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        # Strip markdown code fences if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        content = content.strip()

        raw_transactions = json.loads(content)
        if not isinstance(raw_transactions, list):
            logger.warning("gpt4o_parser: response was not a list")
            return []

        results = []
        for item in raw_transactions:
            try:
                from datetime import date
                txn_date = date.fromisoformat(str(item.get("transaction_date", "")))
                quantity = Decimal(str(item.get("quantity", 0)))
                unit_price = Decimal(str(item.get("unit_price", 0)))
                total_value = Decimal(str(item.get("total_value", 0))) or (quantity * unit_price)
                irrf = Decimal(str(item.get("irrf_withheld", 0)))

                results.append({
                    "ticker": str(item.get("ticker", "")).upper()[:20],
                    "asset_class": "acao",
                    "transaction_type": str(item.get("transaction_type", "buy")).lower(),
                    "transaction_date": txn_date,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_value": total_value,
                    "brokerage_fee": Decimal("0"),
                    "irrf_withheld": irrf,
                    "parser_source": "gpt4o",
                })
            except Exception as item_exc:
                logger.warning("gpt4o_parser: error processing item %s: %s", item, item_exc)
                continue

        logger.info("gpt4o_parser: extracted %d transactions", len(results))
        return results

    except Exception as exc:
        logger.debug("gpt4o_parser: failed (%s)", exc)
        return []
