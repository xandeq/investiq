# Phase 5: Import + Broker Integration - Research

**Researched:** 2026-03-15
**Domain:** PDF parsing (Brazilian broker notes), CSV import, async Celery pipeline, file storage, review UI
**Confidence:** HIGH (core patterns verified against existing codebase; MEDIUM on correpy broker coverage)

---

## Summary

Phase 5 adds two import channels to InvestIQ: (1) PDF upload of XP and Clear notas de corretagem, parsed asynchronously and presented for user review before any transaction is committed; (2) CSV import using a system-provided template. All original files must be stored permanently to support re-parsing when parsers improve.

The existing Celery + Redis + psycopg2 infrastructure (established in Phase 2, extended in Phase 4) is the direct foundation — the import pipeline follows the exact same pattern as the AI analysis pipeline: POST returns 202 + job_id, Celery task does the heavy work, result is polled by frontend. The key new complexity is the two-stage commit: parsed results are staged for user review and not written to `transactions` until the user confirms.

**Primary recommendation:** Use `correpy` (specialized B3/SINACOR parser, latest v0.6.0 June 2024) as the primary PDF parser, with `pdfplumber` as the fallback for non-SINACOR structured PDFs, and GPT-4o vision as the final fallback for unrecognized formats. Store raw files in a dedicated `import_files` table using PostgreSQL `bytea` (PDFs are < 2 MB; no S3 needed for v1). Stage parsed-but-unconfirmed transactions in an `import_staging` table, not in `transactions`, until the user confirms.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| IMP-01 | User can upload a nota de corretagem PDF from XP or Clear — parser assíncrono com revisão antes de confirmar | correpy + pdfplumber + GPT-4o fallback pipeline; Celery async task pattern from Phase 4; staging table for review-before-commit |
| IMP-02 | User can import transactions via CSV using the system's template — import is validated and shown for review before committing | CSV template design with Pydantic row validation; same staging table pattern; template download endpoint |
| IMP-03 | Sistema armazena arquivo original do import (PDF/CSV) para auditoria e reprocessamento | `import_files` table with `bytea` column; re-parse endpoint that reads stored bytes; permanent retention policy |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| correpy | 0.6.0 | Parse B3/SINACOR brokerage notes (XP, Clear, Rico, BTG, Necton) | Only specialized Python library for SINACOR format; returns structured BrokerageNote objects with transactions; actively maintained |
| pdfplumber | 0.11.x | Extract tables from structured PDFs (fallback for non-SINACOR) | Purpose-built for table extraction; coordinate-based; better than pymupdf for structured financial tables |
| pdf2image | 1.17.x | Convert PDF pages to PIL images (for GPT-4o vision fallback) | Required for vision API; wraps pdftoppm; `convert_from_bytes()` works in Celery tasks |
| pandas | 2.2.0 | CSV parsing and validation (already installed) | Already in requirements.txt; DataFrame → Pydantic model validation pattern |
| python-multipart | 0.0.9 | Handle file upload in FastAPI (already installed) | Already in requirements.txt; `UploadFile` pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| boto3 | latest | AWS Secrets Manager (for OpenAI key in GPT-4o fallback) | GPT-4o fallback path only; same lazy-import pattern as brapi.py |
| openai | latest | GPT-4o vision call for unrecognized PDF formats | Already in requirements via ai module; reuse existing provider.py fallback logic |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| correpy (B3 parser) | PyMuPDF raw extraction | correpy handles the SINACOR structure — PyMuPDF just gives raw text/chars; correpy saves weeks of layout engineering |
| pdfplumber (fallback) | PyMuPDF | pdfplumber excels at table extraction (our case); PyMuPDF is faster for bulk but less configurable for table detection |
| PostgreSQL bytea (file storage) | AWS S3 | bytea is simpler, transactional, no added infrastructure; PDFs < 2 MB; S3 adds boto3 + IAM complexity for v1 |
| Staging table | Redis temporary storage | Staging table is durable, queryable, naturally tenant-isolated via RLS; Redis TTL risks data loss during review |

**Installation (new packages only):**
```bash
pip install correpy pdfplumber pdf2image
# pdf2image also requires system dependency: poppler-utils (added to Dockerfile)
```

**Dockerfile addition:**
```dockerfile
RUN apt-get update && apt-get install -y poppler-utils && rm -rf /var/lib/apt/lists/*
```

---

## Architecture Patterns

### Recommended Module Structure
```
backend/app/modules/
└── imports/
    ├── __init__.py
    ├── models.py          # ImportFile, ImportStaging SQLAlchemy models
    ├── schemas.py         # Pydantic request/response schemas
    ├── router.py          # POST /imports/pdf, POST /imports/csv, GET /imports/jobs/{id}, POST /imports/jobs/{id}/confirm
    ├── service.py         # ImportService: orchestrates staging + commit
    ├── tasks.py           # Celery tasks: parse_pdf_import, parse_csv_import (same pattern as ai/tasks.py)
    └── parsers/
        ├── __init__.py
        ├── correpy_parser.py   # Primary: correpy ParserFactory wrapper
        ├── pdfplumber_parser.py # Fallback 1: structured pdfplumber extraction
        ├── gpt4o_parser.py      # Fallback 2: vision API with pdf2image
        └── csv_parser.py        # CSV template validator + row parser
```

### Pattern 1: Two-Stage Import Pipeline (Upload → Stage → Confirm)

**What:** File upload creates a job (like AI pipeline). Celery task parses file and writes rows to `import_staging`. User reviews/edits staged rows, then POSTs confirm — which copies staged rows into `transactions`.

**When to use:** Always. Never write directly to `transactions` from import without user review.

**Flow:**
```
POST /imports/pdf  (multipart/form-data)
  → Save raw bytes to import_files table
  → Create import_job row (status=pending)
  → Dispatch Celery task parse_pdf_import(job_id, file_id, tenant_id)
  → Return 202 + job_id

[Celery] parse_pdf_import:
  → Fetch bytes from import_files
  → Try correpy → pdfplumber → GPT-4o fallback
  → Write rows to import_staging (status=staged)
  → Update import_job (status=completed, staging_count=N)

GET /imports/jobs/{job_id}   (poll, same pattern as AI jobs)
  → Return status + staged rows when completed

POST /imports/jobs/{job_id}/confirm
  → Validate staging rows still belong to tenant
  → Run duplicate detection (hash check)
  → INSERT into transactions (skipping duplicates)
  → Mark import_job status=confirmed
  → Delete staging rows

POST /imports/jobs/{job_id}/cancel
  → Mark import_job status=cancelled
  → Delete staging rows
```

### Pattern 2: correpy Parser (Primary Path)

**What:** correpy's `ParserFactory` handles the SINACOR format used by XP, Clear, Rico, BTG, Necton.

**When to use:** First attempt, before any fallback.

```python
# Source: https://github.com/thiagosalvatore/correpy (v0.6.0)
import io
from correpy.parsers.brokerage_notes.parser_factory import ParserFactory

def parse_with_correpy(pdf_bytes: bytes, password: str | None = None) -> list[dict]:
    content = io.BytesIO(pdf_bytes)
    content.seek(0)
    notes = ParserFactory(brokerage_note=content, password=password or "").parse()
    transactions = []
    for note in notes:
        for txn in note.transactions:
            transactions.append({
                "reference_date": note.reference_date,
                "ticker": _clean_ticker(txn.security.name),
                "transaction_type": "buy" if txn.transaction_type.name == "BUY" else "sell",
                "quantity": txn.amount,
                "unit_price": txn.unit_price,
                "total_value": txn.amount * txn.unit_price,
                "irrf_withheld": txn.source_withheld_taxes,
                "brokerage_fee": note.operational_fee,
                "source": "correpy",
            })
    return transactions
```

**Data returned by correpy `BrokerageNote`:**
- `reference_id` — note number
- `reference_date` — pregão date
- `settlement_fee`, `registration_fee`, `term_fee`, `ana_fee`, `emoluments`, `operational_fee`, `execution`, `custody_fee` — fee breakdown
- `taxes`, `others`, `source_withheld_taxes` (IRRF)
- `transactions: list[Transaction]` — each with `transaction_type` (BUY/SELL enum), `amount` (Decimal), `unit_price` (Decimal), `security.name`, `source_withheld_taxes`

**Known limitation:** `security.name` returns the raw SINACOR asset description (e.g. "PETROBRAS PN N2"). Ticker extraction requires normalization — strip suffix codes, map to B3 tickers.

### Pattern 3: pdfplumber Fallback

**What:** For PDFs that correpy fails on (non-SINACOR format or unrecognized brokers), attempt table extraction with pdfplumber.

```python
# Source: https://github.com/jsvine/pdfplumber (official docs)
import pdfplumber
import io

TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "intersection_tolerance": 5,
    "snap_tolerance": 3,
}

def parse_with_pdfplumber(pdf_bytes: bytes) -> list[dict]:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        all_rows = []
        for page in pdf.pages:
            tables = page.extract_tables(TABLE_SETTINGS)
            for table in tables:
                all_rows.extend(table)
    return _normalize_pdfplumber_rows(all_rows)
```

### Pattern 4: GPT-4o Vision Fallback

**What:** Convert PDF to images, send to GPT-4o with a structured extraction prompt. Trigger only when correpy and pdfplumber both fail to extract >0 transactions.

**Cost:** ~$0.003–$0.006 per page (image tokens + output tokens). Nota de corretagem is typically 1-2 pages. Acceptable for rare fallback.

```python
# Source: OpenAI Cookbook - Parse PDF docs for RAG
from pdf2image import convert_from_bytes
import base64
import json

def parse_with_gpt4o(pdf_bytes: bytes, openai_client) -> list[dict]:
    images = convert_from_bytes(pdf_bytes, dpi=150)
    image_messages = []
    for img in images:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        image_messages.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"},
        })

    prompt = """Extract ALL transactions from this Brazilian brokerage note (nota de corretagem).
Return a JSON array. Each item must have:
- date (YYYY-MM-DD)
- ticker (B3 ticker, e.g. PETR4)
- transaction_type ("buy" or "sell")
- quantity (number)
- unit_price (number)
- total_value (number)
- irrf_withheld (number, 0 if absent)

Return ONLY valid JSON, no markdown."""

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": [{"type": "text", "text": prompt}] + image_messages}],
        max_tokens=2000,
    )
    return json.loads(response.choices[0].message.content)
```

### Pattern 5: Celery Task (mirrors ai/tasks.py)

**What:** Celery task that reads file bytes from DB (not passed as parameter — bytes too large for task payload), runs parser cascade, writes to staging.

```python
# Mirrors app/modules/ai/tasks.py pattern exactly
@shared_task(name="imports.parse_pdf_import", bind=True, max_retries=2)
def parse_pdf_import(self, job_id: str, file_id: str, tenant_id: str) -> dict:
    _update_import_job_status(job_id, "running")
    try:
        with get_sync_db_session(tenant_id=tenant_id) as session:
            file_row = session.get(ImportFile, file_id)
            pdf_bytes = file_row.file_bytes  # bytea column

        transactions = _parse_with_cascade(pdf_bytes)
        _write_staging_rows(job_id, tenant_id, transactions)
        _update_import_job_status(job_id, "completed", staging_count=len(transactions))
        return {"job_id": job_id, "count": len(transactions)}
    except Exception as exc:
        _update_import_job_status(job_id, "failed", error_message=str(exc))
        raise
```

**CRITICAL:** Do NOT pass `pdf_bytes` as a Celery task argument. Large binary payloads break Redis broker serialization. Always store to DB first, read inside the task.

### Pattern 6: Duplicate Detection

**What:** Before committing staged rows to `transactions`, compute a deterministic hash per transaction and check against existing rows.

**Hash composition:** SHA-256 of `(tenant_id, ticker, transaction_type, transaction_date, quantity, unit_price)` — rounded to 8 decimal places for floats.

```python
import hashlib
from decimal import Decimal

def compute_transaction_hash(tenant_id: str, ticker: str, txn_type: str,
                             date: str, quantity: Decimal, unit_price: Decimal) -> str:
    parts = "|".join([
        tenant_id,
        ticker.upper(),
        txn_type,
        str(date),
        f"{quantity:.8f}",
        f"{unit_price:.8f}",
    ])
    return hashlib.sha256(parts.encode()).hexdigest()
```

Add `import_hash` column to `transactions` table with a unique constraint scoped to `(tenant_id, import_hash)`. This allows `INSERT ... ON CONFLICT DO NOTHING` for idempotent re-imports.

### Pattern 7: CSV Template Design

**What:** A downloadable CSV template with exactly the columns needed to populate the `transactions` table.

**Template columns (required):**
```
ticker,asset_class,transaction_type,transaction_date,quantity,unit_price,brokerage_fee,irrf_withheld,notes
PETR4,acao,buy,2025-01-15,100,38.50,4.90,0,
BBAS3,acao,sell,2025-01-20,50,55.20,2.90,0.028,
HGLG11,FII,dividend,2025-02-01,0,1.20,0,0,Dividendo mensal
```

**Validation using Pydantic:**
```python
from pydantic import BaseModel, field_validator
from decimal import Decimal
from datetime import date

class CSVTransactionRow(BaseModel):
    ticker: str
    asset_class: str  # validated against AssetClass enum
    transaction_type: str  # validated against TransactionType enum
    transaction_date: date
    quantity: Decimal
    unit_price: Decimal
    brokerage_fee: Decimal = Decimal("0")
    irrf_withheld: Decimal = Decimal("0")
    notes: str = ""

    @field_validator("ticker")
    @classmethod
    def ticker_uppercase(cls, v: str) -> str:
        return v.strip().upper()
```

### Pattern 8: File Storage (PostgreSQL bytea)

**What:** Store raw PDF/CSV bytes in a dedicated `import_files` table using `bytea`.

**Why not S3 for v1:**
- PDFs are 100-500 KB, CSVs < 100 KB — well within TOAST threshold
- No S3 bucket setup, IAM policy, or boto3 S3 calls needed
- Files travel atomically with transaction data (no orphaned S3 objects)
- Easy re-parse: `SELECT file_bytes FROM import_files WHERE id = :file_id`

**Schema:**
```python
class ImportFile(Base):
    __tablename__ = "import_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10))  # "pdf" | "csv"
    original_filename: Mapped[str] = mapped_column(String(255))
    file_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    # RLS: policies apply to tenant_id
```

**File size validation in router (before storing):**
```python
MAX_PDF_SIZE = 10 * 1024 * 1024   # 10 MB
MAX_CSV_SIZE = 1 * 1024 * 1024    # 1 MB
```

### Pattern 9: FastAPI File Upload Endpoint

**What:** `POST /imports/pdf` accepts `multipart/form-data` with `UploadFile`.

```python
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status

@router.post("/pdf", response_model=ImportJobResponse, status_code=202)
async def upload_pdf(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> ImportJobResponse:
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(400, "Only PDF files accepted")

    content = await file.read()
    if len(content) > MAX_PDF_SIZE:
        raise HTTPException(413, f"File exceeds {MAX_PDF_SIZE // (1024*1024)} MB limit")

    # Save file bytes to import_files
    import_file = ImportFile(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        file_type="pdf",
        original_filename=file.filename or "upload.pdf",
        file_bytes=content,
        file_size_bytes=len(content),
    )
    db.add(import_file)
    await db.flush()

    # Create job and dispatch Celery task
    job = ImportJob(id=str(uuid.uuid4()), tenant_id=tenant_id,
                    file_id=import_file.id, status="pending")
    db.add(job)
    await db.flush()

    from app.modules.imports.tasks import parse_pdf_import
    parse_pdf_import.delay(job.id, import_file.id, tenant_id)

    return ImportJobResponse(id=job.id, status="pending", ...)
```

### Pattern 10: Frontend Review UI

**What:** Upload dropzone + polling + review table. Same TanStack Query polling pattern as AI analysis page.

**Key shadcn/ui components:**
- `react-dropzone` + shadcn `Card` — file drop area
- shadcn `DataTable` (TanStack Table) with editable cells — staged transaction review
- shadcn `Badge` — status indicator (staged / duplicate / confirmed)
- shadcn `Button` (Confirm / Cancel) — commit or discard import
- shadcn `Sheet` — detail panel for editing individual staged rows

**Upload flow:** `<input type="file">` inside a form → `fetch('/api/imports/pdf', {method: 'POST', body: formData})` → receive `job_id` → poll `GET /imports/jobs/{job_id}` every 2s → render staged rows in DataTable when status=completed → user reviews → POST confirm.

**Note:** Use API route (`fetch`) not Next.js Server Actions for file upload to the FastAPI backend. Server Actions are for Next.js server-side mutations only. File upload to an external API uses `FormData` + `fetch`.

### Anti-Patterns to Avoid
- **Pass PDF bytes as Celery task argument:** Celery serializes arguments to JSON/Redis. Large binaries break serialization and consume broker memory. Store to DB, read inside task.
- **Write directly to `transactions` from import task:** Parser output must be staged and user-confirmed. Direct write bypasses duplicate detection and user review requirements.
- **Use asyncpg in Celery tasks:** Established project decision. Celery tasks use `get_sync_db_session` (psycopg2) with `asyncio.run()` bridge for any async skill calls.
- **Parse inside the HTTP request handler:** PDF parsing can take 2-30 seconds (especially GPT-4o fallback). Always dispatch to Celery.
- **Trust correpy ticker output directly:** `security.name` is the raw SINACOR descriptor (e.g., "PETROBRAS PN N2"). Requires normalization to extract "PETR4".

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SINACOR PDF parsing | Custom regex/text extractor | correpy ParserFactory | SINACOR format has subtle layout variants per broker version; correpy handles all known cases |
| Table detection without borders | Manual coordinate parsing | pdfplumber with `vertical_strategy="text"` | pdfplumber handles borderless tables via word alignment detection |
| PDF → image conversion | PIL direct PDF render | pdf2image (poppler wrapper) | Poppler handles all PDF versions including encrypted; PIL cannot render PDFs natively |
| CSV validation error messages | Custom validator | Pydantic v2 field validators + pandas read_csv | row-level error reporting with field-level messages out of the box |
| Duplicate detection SQL | Manual SELECT + compare | Unique index on `(tenant_id, import_hash)` + ON CONFLICT | PostgreSQL ACID guarantees prevent race conditions on concurrent imports |

**Key insight:** The SINACOR format has been implemented by correpy across 11 releases — it handles edge cases across XP, Clear, Rico, BTG, and Necton PDFs. Custom re-implementation would require the same real-world test corpus.

---

## Common Pitfalls

### Pitfall 1: correpy requires empty string password for unencrypted PDFs
**What goes wrong:** `ParserFactory(brokerage_note=content)` raises on unencrypted PDFs if password is not passed; or passes `None` which causes internal error.
**Why it happens:** The library's internal PDF decryption path calls decrypt("") for unencrypted PDFs, but `None` propagates differently.
**How to avoid:** Always pass `password=""` (empty string) for unencrypted PDFs. Wrap in try/except and fall through to pdfplumber fallback.
**Warning signs:** `PdfReadError` or `AttributeError` in correpy on what appears to be a valid PDF.

### Pitfall 2: SINACOR ticker names are not B3 tickers
**What goes wrong:** correpy returns `security.name = "PETROBRAS PN N2"` — inserting this directly as `ticker` into transactions breaks portfolio calculations.
**Why it happens:** SINACOR stores human-readable names, not B3 ticker codes.
**How to avoid:** Implement a `_normalize_ticker(name: str) -> str` function. Strip suffixes (PN, ON, N1, N2, NM, UNT, F, DRN), uppercase, take last 5-6 chars or use a known mapping dict.
**Warning signs:** Transaction tickers that don't match the B3 ticker format (4-5 alphanumeric chars + optional number).

### Pitfall 3: pdf2image requires poppler system dependency
**What goes wrong:** `ModuleNotFoundError` or `PDFInfoNotInstalledError` when calling `convert_from_bytes`.
**Why it happens:** pdf2image wraps `pdftoppm` from the `poppler-utils` system package, not included in the base Python Docker image.
**How to avoid:** Add `RUN apt-get update && apt-get install -y poppler-utils` to the Dockerfile before `pip install`. Must be in the same image as the Celery worker.
**Warning signs:** Import error at Celery worker startup, not at parse time.

### Pitfall 4: Multi-page nota de corretagem tables span pages
**What goes wrong:** pdfplumber extracts each page independently; a transaction table that starts on page 1 and ends on page 2 gets split into two incomplete tables.
**Why it happens:** pdfplumber operates page-by-page by default.
**How to avoid:** After extracting tables per page, concatenate table rows using the header row as the anchor — match header columns from page 1 to subsequent pages.

### Pitfall 5: Bytea column size and PostgreSQL TOAST
**What goes wrong:** Developer assumes bytea column causes issues with large files. Actually not a problem for PDFs < 10 MB — PostgreSQL TOAST transparently handles it.
**Why it happens:** Misunderstanding TOAST; confusion with other databases.
**How to avoid:** No special handling needed for files < 1 GB. TOAST activates automatically above ~2 KB. Just use `LargeBinary` in SQLAlchemy.
**Warning signs:** None — don't over-engineer this.

### Pitfall 6: Frontend file upload to external API via Server Actions
**What goes wrong:** Developer puts `'use server'` action on file upload form and tries to call the FastAPI backend — Next.js Server Actions are for Next.js server-side code, not external API calls.
**Why it happens:** Conflating Next.js Server Actions (which run on Next.js server) with external API calls.
**How to avoid:** Use `fetch` with `FormData` from a Client Component. Or proxy through a Next.js API Route if CORS is a concern.

### Pitfall 7: Celery task receives stale file bytes (cache invalidation)
**What goes wrong:** A re-parse task fetches file bytes from DB but reads a cached/stale session object.
**Why it happens:** Sync session caching in psycopg2 engine.
**How to avoid:** Always open a fresh `get_sync_db_session()` context when reading file bytes inside a Celery task. Never pass session objects across task boundaries.

---

## Code Examples

### correpy Installation and Basic Parse
```python
# Source: https://github.com/thiagosalvatore/correpy (v0.6.0)
# pip install correpy

import io
from correpy.parsers.brokerage_notes.parser_factory import ParserFactory
from decimal import Decimal

def parse_nota_de_corretagem(pdf_bytes: bytes) -> list[dict]:
    """Primary parser: handles XP, Clear, Rico, BTG, Necton (SINACOR format)."""
    try:
        content = io.BytesIO(pdf_bytes)
        content.seek(0)
        notes = ParserFactory(brokerage_note=content, password="").parse()

        result = []
        for note in notes:
            for txn in note.transactions:
                result.append({
                    "reference_date": note.reference_date,
                    "security_name": txn.security.name,  # needs ticker normalization
                    "transaction_type": "buy" if txn.transaction_type.name == "BUY" else "sell",
                    "quantity": txn.amount,
                    "unit_price": txn.unit_price,
                    "total_value": txn.amount * txn.unit_price,
                    "irrf": txn.source_withheld_taxes or Decimal("0"),
                    "operational_fee": note.operational_fee or Decimal("0"),
                    "source": "correpy",
                })
        return result
    except Exception:
        return []  # signal fallback needed
```

### pdfplumber Table Extraction (Fallback)
```python
# Source: https://github.com/jsvine/pdfplumber (official docs)
# pip install pdfplumber

import pdfplumber
import io

_TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "intersection_tolerance": 5,
    "snap_tolerance": 3,
    "join_tolerance": 3,
    "edge_min_length": 3,
}

def parse_with_pdfplumber(pdf_bytes: bytes) -> list[list]:
    """Extract raw table rows from all pages."""
    all_tables = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables(_TABLE_SETTINGS)
            all_tables.extend(tables)
    return all_tables
```

### Pydantic CSV Row Validation
```python
# Source: https://docs.pydantic.dev/latest/examples/files/
from pydantic import BaseModel, field_validator, model_validator
from decimal import Decimal
from datetime import date
import pandas as pd
import io

VALID_ASSET_CLASSES = {"acao", "FII", "renda_fixa", "BDR", "ETF"}
VALID_TRANSACTION_TYPES = {"buy", "sell", "dividend", "jscp", "amortization"}

class CSVTransactionRow(BaseModel):
    ticker: str
    asset_class: str
    transaction_type: str
    transaction_date: date
    quantity: Decimal
    unit_price: Decimal
    brokerage_fee: Decimal = Decimal("0")
    irrf_withheld: Decimal = Decimal("0")
    notes: str = ""

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("asset_class")
    @classmethod
    def validate_asset_class(cls, v: str) -> str:
        if v not in VALID_ASSET_CLASSES:
            raise ValueError(f"asset_class must be one of {VALID_ASSET_CLASSES}")
        return v

    @field_validator("transaction_type")
    @classmethod
    def validate_txn_type(cls, v: str) -> str:
        if v not in VALID_TRANSACTION_TYPES:
            raise ValueError(f"transaction_type must be one of {VALID_TRANSACTION_TYPES}")
        return v

def parse_csv(csv_bytes: bytes) -> tuple[list[CSVTransactionRow], list[dict]]:
    """Returns (valid_rows, errors). errors have {row, field, message}."""
    df = pd.read_csv(io.BytesIO(csv_bytes))
    valid_rows, errors = [], []
    for i, row in df.iterrows():
        try:
            valid_rows.append(CSVTransactionRow(**row.to_dict()))
        except Exception as e:
            errors.append({"row": i + 2, "error": str(e)})
    return valid_rows, errors
```

### Duplicate Detection Hash
```python
import hashlib
from decimal import Decimal
from datetime import date

def import_hash(tenant_id: str, ticker: str, txn_type: str,
                txn_date: date, quantity: Decimal, unit_price: Decimal) -> str:
    """Deterministic fingerprint for deduplication. Use as unique constraint."""
    parts = "|".join([
        tenant_id,
        ticker.upper(),
        txn_type.lower(),
        str(txn_date),
        f"{quantity:.8f}",
        f"{unit_price:.8f}",
    ])
    return hashlib.sha256(parts.encode("utf-8")).hexdigest()
```

### TanStack Query Polling (Frontend — matches AI pattern)
```typescript
// Same pattern as src/features/ai/hooks/useJobPolling.ts
// Source: TanStack Query v5 docs - https://tanstack.com/query/v5/docs/framework/react/guides/query-options

import { useQuery } from "@tanstack/react-query"

export function useImportJobPolling(jobId: string | null) {
  return useQuery({
    queryKey: ["import-job", jobId],
    queryFn: () => fetchImportJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === "pending" || status === "running" ? 2000 : false
    },
  })
}
```

---

## Nota de Corretagem: Field Reference

Brazilian brokerage notes (notas de corretagem) in SINACOR/B3 format have this structure:

### Header Fields
- Note number, number of pages
- Data do pregão (trading date)
- Broker name and CNPJ
- Client number, CPF/CNPJ, client name

### Transaction Table (Quadrant B) — one row per trade
| Column | Content |
|--------|---------|
| C/V | "C" (compra/buy) or "V" (venda/sell) |
| Mercado | Market type (Bovespa / BMF / fracionário) |
| Prazo | Settlement period |
| Especificação do título | Asset name (SINACOR descriptor) |
| Obs. / Tipo negócio | Day trade "D" or Swing trade blank |
| Quantidade | Share quantity (integer for standard, decimal for fracionário) |
| Preço/Ajuste | Unit price (Decimal, BRL) |
| Valor da operação | Total = qty × price (BRL) |
| D/C | "D" debit or "C" credit |

### Summary Totals (Quadrant C)
- Valor total: sum by market segment
- Debentures, Ações, Opções, Futuros, Títulos Públicos subtotals

### Fees (Quadrant D)
- Taxa de liquidação (0.0250%)
- Emolumentos / taxa de negociação (0.0050%)
- Taxa operacional (corretagem)
- Taxa de registro
- ISS (when applicable)
- IRRF: 1% day trade, 0.005% swing trade (on gross profit for swing above threshold)

### Key Difference: XP model vs B3/SINACOR model
- B3 model: standardized for Receita Federal / IR calculators
- XP model: more detailed, includes asset classifications and additional metadata
- correpy parses the B3/SINACOR model (the standardized one)

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom regex PDF text extraction | correpy ParserFactory for SINACOR | 2021+ | Handles all broker format variants without per-broker regex |
| Store files in S3 for all sizes | PostgreSQL bytea for small files (< 10 MB) | Ongoing | Simpler infrastructure for v1; migrate to S3 only when scale requires |
| Write imports directly to ledger | Stage → review → confirm two-phase commit | Financial app best practice | Prevents irreversible data corruption from malformed imports |
| Single parser attempt | Parser cascade (correpy → pdfplumber → GPT-4o) | 2024-2025 | Handles format variations without hardcoding per-broker logic |

**Deprecated/outdated:**
- `PyPDF2`: Superseded by `pypdf` (successor project). Neither is needed here — correpy and pdfplumber handle extraction.
- `pdfminer.six` directly: pdfplumber wraps pdfminer with better table API; use pdfplumber.
- `python-jose`: Project uses PyJWT directly (established decision from Phase 1).

---

## Open Questions

1. **Ticker normalization accuracy**
   - What we know: correpy returns `security.name` as SINACOR descriptor (e.g., "PETROBRAS PN N2"), not B3 ticker ("PETR4").
   - What's unclear: The normalization rules are complex — "PN N2", "ON NM", "UNT N2", "DRN", fracionário suffix "F", rights "11" are all suffixes. A comprehensive mapping or regex is needed.
   - Recommendation: Build a `normalize_ticker(name)` function. Start with a regex that extracts the first 4-6 uppercase alphanumeric characters, then test against real XP/Clear PDFs. Accept that edge cases will exist and surface them to the user during review.
   - Blocker note from STATE.md: "Need Alexandre's real Clear and XP notas de corretagem as test fixtures before building PDF parsers — assumed formats will be wrong."

2. **correpy password-protected PDFs from XP**
   - What we know: XP issues password-protected notes where the password is the client's CPF (CNPJ).
   - What's unclear: Whether all users' notes are encrypted, or only some. Whether correpy handles this correctly.
   - Recommendation: Accept an optional `password` field in the upload form. Document that XP PDF passwords are typically the CPF. Handle `PdfReadError` gracefully and return a user-friendly error asking for password.

3. **GPT-4o fallback trigger threshold**
   - What we know: GPT-4o costs ~$0.003-0.006 per nota page. Correpy handles SINACOR. pdfplumber handles structured tables.
   - What's unclear: What percentage of real user uploads will actually need the GPT-4o fallback (non-SINACOR, non-structured PDFs from exotic brokers).
   - Recommendation: Trigger fallback only when correpy AND pdfplumber both return 0 transactions. Log fallback usage. If >5% of uploads hit GPT-4o fallback, investigate which broker is causing it.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (existing) |
| Config file | `backend/pytest.ini` (existing) |
| Quick run command | `cd backend && python -m pytest tests/test_imports.py -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| IMP-01 | `POST /imports/pdf` returns 202 + job_id | integration | `pytest tests/test_imports_api.py::test_upload_pdf_returns_202 -x` | ❌ Wave 0 |
| IMP-01 | Celery parse task writes staging rows | unit | `pytest tests/test_import_tasks.py::test_parse_pdf_writes_staging -x` | ❌ Wave 0 |
| IMP-01 | correpy parser extracts BUY/SELL from fixture | unit | `pytest tests/test_import_parsers.py::test_correpy_parser -x` | ❌ Wave 0 |
| IMP-01 | Parser cascade: correpy fails → pdfplumber fallback | unit | `pytest tests/test_import_parsers.py::test_fallback_to_pdfplumber -x` | ❌ Wave 0 |
| IMP-01 | `POST /imports/jobs/{id}/confirm` writes to transactions | integration | `pytest tests/test_imports_api.py::test_confirm_writes_transactions -x` | ❌ Wave 0 |
| IMP-02 | CSV template validation: valid rows pass | unit | `pytest tests/test_import_parsers.py::test_csv_valid_rows -x` | ❌ Wave 0 |
| IMP-02 | CSV template validation: invalid rows return errors | unit | `pytest tests/test_import_parsers.py::test_csv_invalid_rows -x` | ❌ Wave 0 |
| IMP-02 | `POST /imports/csv` returns 202 + staged rows | integration | `pytest tests/test_imports_api.py::test_upload_csv_returns_202 -x` | ❌ Wave 0 |
| IMP-03 | File bytes stored in import_files table | integration | `pytest tests/test_imports_api.py::test_file_bytes_stored -x` | ❌ Wave 0 |
| IMP-03 | Re-parse reads from stored bytes (no re-upload) | integration | `pytest tests/test_imports_api.py::test_reparse_from_stored_bytes -x` | ❌ Wave 0 |
| IMP-01 | Duplicate detection: same transaction rejected on re-import | integration | `pytest tests/test_imports_api.py::test_duplicate_detection -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_imports_api.py tests/test_import_parsers.py tests/test_import_tasks.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_imports_api.py` — covers IMP-01, IMP-02, IMP-03 API layer
- [ ] `tests/test_import_parsers.py` — covers correpy, pdfplumber, CSV parsers (unit, no DB)
- [ ] `tests/test_import_tasks.py` — covers Celery task cascade
- [ ] `tests/fixtures/sample_nota_corretagem.pdf` — minimal synthetic SINACOR PDF for unit tests (not real broker data)
- [ ] `tests/fixtures/sample_import.csv` — valid CSV template fixture
- [ ] `app/modules/imports/` — module does not exist yet

Note: conftest.py will need `import app.modules.imports.models` added to ensure `ImportFile`, `ImportJob`, `ImportStaging` are registered with `Base.metadata` before `create_all()`.

---

## Sources

### Primary (HIGH confidence)
- https://github.com/thiagosalvatore/correpy — correpy v0.6.0, BrokerageNote/Transaction data structures, supported brokers
- https://github.com/jsvine/pdfplumber — table_settings documentation, extraction strategies
- https://github.com/Belval/pdf2image — convert_from_bytes API
- Existing codebase: `app/modules/ai/tasks.py`, `app/modules/ai/router.py`, `app/core/db_sync.py` — established Celery + psycopg2 patterns to replicate

### Secondary (MEDIUM confidence)
- https://www.leoa.com.br/blog/nota-de-corretagem-xp — XP nota de corretagem field structure
- https://www.idinheiro.com.br/investimentos/nota-de-corretagem/ — SINACOR field reference (Quadrants A-D)
- https://cookbook.openai.com/examples/parse_pdf_docs_for_rag — GPT-4o PDF parsing approach and cost estimates
- https://mahdijafaridev.medium.com/handling-file-uploads-in-fastapi-from-basics-to-s3-integration-fc7e64f87d65 — FastAPI UploadFile + size validation pattern

### Tertiary (LOW confidence — needs validation against real PDFs)
- STATE.md blocker: "Need Alexandre's real Clear and XP notas de corretagem as test fixtures before building PDF parsers — assumed formats will be wrong" — ticker normalization logic in correpy_parser.py must be validated against real notes

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — correpy, pdfplumber, pdf2image are well-established; pdf2image system dependency (poppler) is documented
- Architecture: HIGH — mirrors Phase 4 AI pipeline exactly; staging pattern is well-understood
- Pitfalls: HIGH — ticker normalization issue is documented in correpy GitHub; bytea TOAST behavior is PostgreSQL documented; poppler dependency is well-known
- Nota de corretagem field structure: MEDIUM — sourced from consumer-facing explanatory articles, not official B3 spec; real PDFs may vary

**Research date:** 2026-03-15
**Valid until:** 2026-06-15 (correpy is stable; pdfplumber rarely breaking-changes table API)
