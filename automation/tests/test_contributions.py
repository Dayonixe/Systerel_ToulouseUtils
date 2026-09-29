from datetime import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from automation.refectory.contributions import sync_once


PARIS = ZoneInfo("Europe/Paris")
OFFER_ID = "refectory-2026-09-21-2026-09-25-a1b2c3d4e5f6"


def _write_offer_feed(data_dir: Path) -> None:
    payload = {
        "schemaVersion": 1,
        "sourceUrl": "https://example.test",
        "offers": [
            {
                "id": OFFER_ID,
                "code": "",
                "codeSource": None,
                "confirmationCount": 0,
            }
        ],
    }
    (data_dir / "refectory-offers.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def _read(data_dir: Path, filename: str) -> dict[str, object]:
    return json.loads((data_dir / filename).read_text(encoding="utf-8"))


def test_approved_submissions_are_aggregated_and_attached(tmp_path: Path) -> None:
    _write_offer_feed(tmp_path)
    payload = {
        "schemaVersion": 1,
        "codes": [
            {"offerId": OFFER_ID, "code": "SEMAINE2", "receivedVia": "SMS"},
            {"offerId": OFFER_ID, "code": "semaine2", "receivedVia": "Notification"},
            {"offerId": OFFER_ID, "code": "IGNORED", "status": "refusé"},
        ],
    }

    result = sync_once(
        "https://example.test/codes",
        data_dir=tmp_path,
        now=datetime(2026, 9, 21, 9, 0, tzinfo=PARIS),
        fetch_payload=lambda _: payload,
    )

    registry = _read(tmp_path, "refectory-approved-codes.json")
    feed = _read(tmp_path, "refectory-offers.json")
    assert result == 0
    assert registry["codes"][0]["confirmationCount"] == 2
    assert registry["codes"][0]["receivedVia"] == ["Notification", "SMS"]
    assert feed["offers"][0]["code"] == "SEMAINE2"
    assert feed["offers"][0]["codeSource"] == "contributor"

    sync_once(
        "https://example.test/codes",
        data_dir=tmp_path,
        now=datetime(2026, 9, 21, 9, 15, tzinfo=PARIS),
        fetch_payload=lambda _: {
            "schemaVersion": 1,
            "codes": payload["codes"][:2] + [{"offerId": OFFER_ID, "code": "SEMAINE2"}],
        },
    )
    refreshed_feed = _read(tmp_path, "refectory-offers.json")
    assert refreshed_feed["offers"][0]["confirmationCount"] == 3


def test_empty_feed_does_not_reset_a_weekly_code(tmp_path: Path) -> None:
    _write_offer_feed(tmp_path)
    existing = {
        "schemaVersion": 1,
        "codes": [
            {
                "offerId": OFFER_ID,
                "code": "SEMAINE2",
                "confirmationCount": 1,
                "receivedVia": ["SMS"],
                "approvedAt": "2026-09-21T09:00:00+02:00",
                "lastConfirmedAt": "2026-09-21T09:00:00+02:00",
            }
        ],
    }
    (tmp_path / "refectory-approved-codes.json").write_text(
        json.dumps(existing),
        encoding="utf-8",
    )

    sync_once(
        "https://example.test/codes",
        data_dir=tmp_path,
        now=datetime(2026, 9, 24, 9, 0, tzinfo=PARIS),
        fetch_payload=lambda _: {"schemaVersion": 1, "codes": []},
    )

    registry = _read(tmp_path, "refectory-approved-codes.json")
    feed = _read(tmp_path, "refectory-offers.json")
    assert registry["codes"][0]["code"] == "SEMAINE2"
    assert registry["codes"][0]["lastConfirmedAt"] == "2026-09-21T09:00:00+02:00"
    assert feed["offers"][0]["code"] == "SEMAINE2"


def test_conflicting_code_never_overwrites_the_approved_code(tmp_path: Path) -> None:
    _write_offer_feed(tmp_path)
    existing = {
        "schemaVersion": 1,
        "codes": [
            {
                "offerId": OFFER_ID,
                "code": "SEMAINE2",
                "confirmationCount": 1,
                "receivedVia": [],
                "approvedAt": "2026-09-21T09:00:00+02:00",
                "lastConfirmedAt": "2026-09-21T09:00:00+02:00",
            }
        ],
    }
    registry_path = tmp_path / "refectory-approved-codes.json"
    registry_path.write_text(json.dumps(existing), encoding="utf-8")

    with pytest.raises(ValueError, match="diffère du code déjà approuvé"):
        sync_once(
            "https://example.test/codes",
            data_dir=tmp_path,
            now=datetime(2026, 9, 24, 9, 0, tzinfo=PARIS),
            fetch_payload=lambda _: {
                "schemaVersion": 1,
                "codes": [{"offerId": OFFER_ID, "code": "AUTRECODE"}],
            },
        )

    assert json.loads(registry_path.read_text(encoding="utf-8")) == existing
