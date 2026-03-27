"""Check which import is hanging."""
import sys
import time

print("Starting import check...", flush=True)

t0 = time.time()
print("Importing app.modules.ai.skills.dcf...", flush=True)
from app.modules.ai.skills.dcf import run_dcf
print(f"  OK ({time.time()-t0:.1f}s)", flush=True)

t0 = time.time()
print("Importing app.modules.ai.provider...", flush=True)
from app.modules.ai.provider import call_llm, AIProviderError
print(f"  OK ({time.time()-t0:.1f}s)", flush=True)

t0 = time.time()
print("Importing app.celery_app...", flush=True)
from app.celery_app import celery_app
print(f"  OK ({time.time()-t0:.1f}s)", flush=True)

t0 = time.time()
print("Importing app.modules.ai.tasks...", flush=True)
from app.modules.ai.tasks import run_asset_analysis, run_macro_analysis
print(f"  OK ({time.time()-t0:.1f}s)", flush=True)

print("All imports OK!", flush=True)
