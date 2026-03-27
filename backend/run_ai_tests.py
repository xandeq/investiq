"""Run just the AI skills tests directly."""
import subprocess
import sys
import os

env = os.environ.copy()
env["PYTHONUNBUFFERED"] = "1"

# Run just the AI skills tests with a very short timeout per test
result = subprocess.run(
    [
        sys.executable, "-m", "pytest",
        "tests/test_ai_skills.py",
        "-v",
        "--tb=short",
        "--timeout=10",
        "--collect-only",
    ],
    cwd="D:/_DEV/claude-code/financas/backend",
    capture_output=True,
    text=True,
    timeout=60,
    env=env,
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
print("RETURNCODE:", result.returncode)
