from __future__ import annotations

from pathlib import Path
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OFFERS_PATH = PROJECT_ROOT / "public" / "data" / "refectory-offers.json"
SYNC_PATH = PROJECT_ROOT / "public" / "data" / "refectory-sync.json"
APPROVED_CODES_PATH = PROJECT_ROOT / "public" / "data" / "refectory-approved-codes.json"
DATA_PATHS = (OFFERS_PATH, APPROVED_CODES_PATH)


def _run(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(arguments, cwd=PROJECT_ROOT, check=check, text=True, capture_output=True)


def _data_changed() -> bool:
    result = _run(
        "git",
        "diff",
        "--quiet",
        "--",
        *(str(path) for path in DATA_PATHS),
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or "Unable to compare published Refectory data")
    return result.returncode == 1


def maintain() -> bool:
    if not _data_changed():
        print("No published Refectory data changed; no commit required.")
        return False

    _run("git", "config", "user.name", "github-actions[bot]")
    _run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    paths = [str(OFFERS_PATH), str(APPROVED_CODES_PATH), str(SYNC_PATH)]
    _run("git", "add", "--", *paths)

    cached = _run("git", "diff", "--cached", "--quiet", check=False)
    if cached.returncode == 0:
        print("No staged Refectory data change to commit.")
        return False

    message = "data: refresh Refectory offers and codes [skip ci]"
    _run("git", "commit", "-m", message)
    _run("git", "push")
    print(message)
    return True


def main() -> int:
    maintain()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
