from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
from typing import Callable
from zoneinfo import ZoneInfo

from .contributions import apply_approved_codes, load_approved_codes
from .parser import analyse_offers
from .scraper import SOURCE_URL, load_offers_text
from .storage import read_json, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "public" / "data"
PARIS = ZoneInfo("Europe/Paris")


def export_once(
    fetch_text: Callable[[], str] = load_offers_text,
    data_dir: Path = DEFAULT_DATA_DIR,
    now: datetime | None = None,
) -> int:
    now = now or datetime.now(PARIS)
    timestamp = now.isoformat(timespec="seconds")
    offers_path = data_dir / "refectory-offers.json"
    sync_path = data_dir / "refectory-sync.json"
    existing_feed = read_json(
        offers_path,
        {"schemaVersion": 1, "sourceUrl": SOURCE_URL, "offers": []},
    )
    existing_sync = read_json(
        sync_path,
        {
            "schemaVersion": 1,
            "sourceUrl": SOURCE_URL,
            "status": "pending",
            "lastAttemptAt": None,
            "lastSuccessAt": None,
            "offerCount": 0,
            "codeCount": 0,
            "waitingForCodeCount": 0,
            "message": None,
        },
    )

    try:
        parsed = analyse_offers(fetch_text(), reference=now.date())
        parsed = apply_approved_codes(parsed, load_approved_codes(data_dir))
        visible = [
            offer
            for offer in parsed
            if offer.is_currently_valid and offer.applies_to_toulouse()
        ]
        visible.sort(key=lambda offer: (offer.end_date or now.date(), offer.code or ""))
        code_count = sum(1 for offer in visible if offer.code)

        feed = {
            "schemaVersion": 1,
            "sourceUrl": SOURCE_URL,
            "offers": [offer.as_dict() for offer in visible],
        }
        sync = {
            "schemaVersion": 1,
            "sourceUrl": SOURCE_URL,
            "status": "ok",
            "lastAttemptAt": timestamp,
            "lastSuccessAt": timestamp,
            "offerCount": len(visible),
            "codeCount": code_count,
            "waitingForCodeCount": len(visible) - code_count,
            "message": None,
        }
        write_json(offers_path, feed)
        write_json(sync_path, sync)
        print(
            f"Export Refectory terminé : {len(visible)} offre(s), "
            f"dont {code_count} avec code."
        )
        return 0
    except Exception as error:
        previous_count = len(existing_feed.get("offers", []))
        sync = {
            **existing_sync,
            "schemaVersion": 1,
            "sourceUrl": SOURCE_URL,
            "status": "error",
            "lastAttemptAt": timestamp,
            "offerCount": previous_count,
            "codeCount": existing_sync.get("codeCount", previous_count),
            "waitingForCodeCount": existing_sync.get("waitingForCodeCount", 0),
            "message": "La dernière vérification a échoué ; les dernières offres valides sont conservées.",
        }
        write_json(sync_path, sync)
        print(f"Échec de l'export Refectory : {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(export_once())
