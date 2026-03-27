"""Quick test runner to validate AI module imports and tests."""
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_ai_skills.py", "-v", "--tb=short", "-x", "--timeout=60"],
    cwd="D:/_DEV/claude-code/financas/backend",
    capture_output=True,
    text=True,
    timeout=180,
)
print("STDOUT:", result.stdout[-4000:] if len(result.stdout) > 4000 else result.stdout)
print("STDERR:", result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr)
print("RETURNCODE:", result.returncode)
