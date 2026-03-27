---
phase: 5
slug: import-broker-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (existing) |
| **Config file** | `backend/pytest.ini` (existing) |
| **Quick run command** | `cd backend && python -m pytest tests/test_imports_api.py tests/test_import_parsers.py tests/test_import_tasks.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_imports_api.py tests/test_import_parsers.py tests/test_import_tasks.py -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 0 | IMP-01 | unit | `pytest tests/test_imports_api.py -x -q` | ❌ W0 | ⬜ pending |
| 5-01-02 | 01 | 0 | IMP-01/02/03 | unit | `pytest tests/test_import_parsers.py -x -q` | ❌ W0 | ⬜ pending |
| 5-01-03 | 01 | 0 | IMP-01 | unit | `pytest tests/test_import_tasks.py -x -q` | ❌ W0 | ⬜ pending |
| 5-01-04 | 01 | 1 | IMP-03 | unit/integration | `pytest tests/test_imports_api.py::test_file_bytes_stored -x` | ❌ W0 | ⬜ pending |
| 5-01-05 | 01 | 1 | IMP-01 | unit | `pytest tests/test_import_parsers.py::test_correpy_parser -x` | ❌ W0 | ⬜ pending |
| 5-01-06 | 01 | 1 | IMP-01 | unit | `pytest tests/test_import_parsers.py::test_fallback_to_pdfplumber -x` | ❌ W0 | ⬜ pending |
| 5-01-07 | 01 | 2 | IMP-01 | integration | `pytest tests/test_imports_api.py::test_upload_pdf_returns_202 -x` | ❌ W0 | ⬜ pending |
| 5-01-08 | 01 | 2 | IMP-02 | integration | `pytest tests/test_imports_api.py::test_upload_csv_returns_202 -x` | ❌ W0 | ⬜ pending |
| 5-01-09 | 01 | 2 | IMP-01 | integration | `pytest tests/test_imports_api.py::test_confirm_writes_transactions -x` | ❌ W0 | ⬜ pending |
| 5-01-10 | 01 | 2 | IMP-01 | integration | `pytest tests/test_imports_api.py::test_duplicate_detection -x` | ❌ W0 | ⬜ pending |
| 5-01-11 | 01 | 2 | IMP-03 | integration | `pytest tests/test_imports_api.py::test_reparse_from_stored_bytes -x` | ❌ W0 | ⬜ pending |
| 5-02-01 | 02 | 1 | IMP-01/02 | manual | Browser: upload PDF → review table visible | N/A | ⬜ pending |
| 5-02-02 | 02 | 1 | IMP-01 | manual | Browser: duplicate row flagged in review UI | N/A | ⬜ pending |
| 5-02-03 | 02 | 2 | IMP-01/02 | manual | Browser: edit staged row → confirm → transactions updated | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_imports_api.py` — stubs for IMP-01, IMP-02, IMP-03 API layer (all marked xfail until endpoints ship)
- [ ] `tests/test_import_parsers.py` — stubs for correpy parser, pdfplumber fallback, CSV validation (unit, no DB)
- [ ] `tests/test_import_tasks.py` — stubs for Celery parse task cascade
- [ ] `tests/fixtures/sample_nota_corretagem.pdf` — minimal synthetic SINACOR PDF fixture (not real broker data)
- [ ] `tests/fixtures/sample_import.csv` — valid CSV template fixture
- [ ] conftest.py updated — `import app.modules.imports.models` added for `Base.metadata` registration

*All Wave 0 test files must be created in Plan 05-01, Task 1 (Wave 0 step) before any pipeline code is written.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Upload PDF → review table appears in UI | IMP-01 | Browser file input interaction; Celery task runs in Docker | 1. Start stack. 2. Log in. 3. Go to /imports. 4. Upload sample_nota_corretagem.pdf. 5. Verify review table shows parsed rows within 10s. |
| Duplicate row flagged with visual indicator | IMP-01 | UI state — duplicate SHA-256 hit requires real DB state | 1. Import a PDF once and confirm. 2. Import same PDF again. 3. Verify duplicate rows highlighted/disabled in review table. |
| Edit a staged row → confirm → transaction recorded | IMP-01/02 | End-to-end user flow through review UI | 1. Upload CSV. 2. Edit one row price field inline. 3. Confirm. 4. Go to /portfolio. 5. Verify edited transaction appears. |
| Re-parse button reads stored bytes without re-upload | IMP-03 | Requires backend file storage + re-parse endpoint wired to UI | 1. Upload PDF. 2. Confirm. 3. Click "Re-parse" on import history. 4. Verify new staging rows created without file chooser appearing. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
