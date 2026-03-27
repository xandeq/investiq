"""Imports module — broker PDF and CSV import pipeline.

This module provides:
- SQLAlchemy models: ImportFile, ImportJob, ImportStaging
- Pydantic schemas for API responses
- Parser cascade: correpy → pdfplumber → GPT-4o
- Celery tasks: parse_pdf_import, parse_csv_import
- FastAPI router with 7 endpoints
"""
