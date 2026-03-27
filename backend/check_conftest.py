"""Check if conftest can be imported directly."""
import sys
import os
import time

os.environ["JWT_PRIVATE_KEY"] = "test"
os.environ["JWT_PUBLIC_KEY"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"

print("Step 1: import cryptography...", flush=True)
t0 = time.time()
from cryptography.hazmat.primitives.asymmetric import rsa
print(f"  OK ({time.time()-t0:.2f}s)", flush=True)

print("Step 2: generate RSA key...", flush=True)
t0 = time.time()
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
print(f"  OK ({time.time()-t0:.2f}s)", flush=True)

print("Step 3: import app.core.db...", flush=True)
t0 = time.time()
from app.core.db import get_db
print(f"  OK ({time.time()-t0:.2f}s)", flush=True)

print("Step 4: import app.main...", flush=True)
t0 = time.time()
from app.main import app
print(f"  OK ({time.time()-t0:.2f}s)", flush=True)

print("All done!", flush=True)
