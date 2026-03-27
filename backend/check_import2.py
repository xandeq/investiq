"""Check if celery_app import hangs."""
import sys
import time
import os

# Set up test environment like conftest does
os.environ["JWT_PRIVATE_KEY"] = "dummy"
os.environ["JWT_PUBLIC_KEY"] = "dummy"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"

print("Starting celery_app import...", flush=True)
t0 = time.time()

from app.celery_app import celery_app

print(f"celery_app imported OK ({time.time()-t0:.2f}s)", flush=True)
print(f"Celery tasks includes: {celery_app.conf.include}", flush=True)
