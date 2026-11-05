import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def resolve_version(env_value: str) -> str:
    """APP_VERSION if set, else the latest git tag (local dev), else 'dev'."""
    if env_value:
        return env_value.removeprefix("v")
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "dev"
    tag = result.stdout.strip()
    return tag.removeprefix("v") if result.returncode == 0 and tag else "dev"
