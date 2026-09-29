from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time


PROJECT_ROOT = Path(__file__).resolve().parent.parent
KEEPALIVE_PATH = PROJECT_ROOT / ".automation" / "keepalive.json"
OFFERS_PATH = PROJECT_ROOT / "public" / "data" / "refectory-offers.json"
SYNC_PATH = PROJECT_ROOT / "public" / "data" / "refectory-sync.json"
APPROVED_CODES_PATH = PROJECT_ROOT / "public" / "data" / "refectory-approved-codes.json"
DATA_PATHS = (OFFERS_PATH, APPROVED_CODES_PATH)


def should_commit(last_commit_epoch: int, now_epoch: int, data_changed: bool, threshold_days: int) -> bool:
    age_seconds = max(0, now_epoch - last_commit_epoch)
    return data_changed or age_seconds >= threshold_days * 86_400


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
        raise RuntimeError(result.stderr.strip() or "Impossible de comparer les offres")
    return result.returncode == 1


def _last_commit_epoch() -> int:
    result = _run("git", "log", "-1", "--format=%ct", check=False)
    return int(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip() else 0


def maintain(threshold_days: int) -> bool:
    now_epoch = int(time.time())
    last_commit = _last_commit_epoch()
    data_changed = _data_changed()
    due = should_commit(last_commit, now_epoch, data_changed, threshold_days)

    if not due:
        age_days = (now_epoch - last_commit) // 86_400
        print(f"Aucun commit requis : dernier commit il y a {age_days} jour(s).")
        return False

    if not data_changed:
        KEEPALIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        KEEPALIVE_PATH.write_text(
            json.dumps(
                {
                    "updatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "reason": f"Maintien du workflow avant {threshold_days} jours d'inactivité",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    _run("git", "config", "user.name", "github-actions[bot]")
    _run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    paths = [str(OFFERS_PATH), str(APPROVED_CODES_PATH), str(SYNC_PATH), str(KEEPALIVE_PATH)]
    _run("git", "add", "--", *paths)

    cached = _run("git", "diff", "--cached", "--quiet", check=False)
    if cached.returncode == 0:
        print("Aucun changement à committer.")
        return False

    message = "data: actualiser les offres Refectory [skip ci]" if data_changed else "chore: maintenir les workflows planifiés [skip ci]"
    _run("git", "commit", "-m", message)
    _run("git", "push")
    print(message)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold-days", type=int, default=55)
    args = parser.parse_args()
    maintain(args.threshold_days)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
