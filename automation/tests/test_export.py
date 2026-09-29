from datetime import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from automation.refectory.export import export_once


PARIS = ZoneInfo("Europe/Paris")


def test_export_keeps_active_toulouse_offers_even_without_code(tmp_path: Path) -> None:
    text = """
Offres en cours
Du 21/09 au 25/09, 2€ offerts avec le code TLSE2026. Uniquement à Toulouse.
Du 21/09 au 25/09, 1€ offert. Le code est envoyé par notification.
Du 21/09 au 25/09, 3€ offerts avec le code PARIS2026. Uniquement à Paris.
Du 01/09 au 02/09, 1€ offert avec le code OLD2026.
Offres de bienvenue
"""
    result = export_once(
        fetch_text=lambda: text,
        data_dir=tmp_path,
        now=datetime(2026, 9, 24, 8, 17, tzinfo=PARIS),
    )
    payload = json.loads((tmp_path / "refectory-offers.json").read_text(encoding="utf-8"))
    sync = json.loads((tmp_path / "refectory-sync.json").read_text(encoding="utf-8"))

    assert result == 0
    assert sorted(offer["code"] for offer in payload["offers"]) == ["", "TLSE2026"]
    assert sync["offerCount"] == 2
    assert sync["codeCount"] == 1
    assert sync["waitingForCodeCount"] == 1


def test_export_reuses_an_approved_code_for_the_whole_offer(tmp_path: Path) -> None:
    text = """
Offres en cours
Du 21/09 au 25/09, 2€ offerts pour un montant minimum de 8€. Code envoyé par SMS.
Offres de bienvenue
"""
    first_result = export_once(
        fetch_text=lambda: text,
        data_dir=tmp_path,
        now=datetime(2026, 9, 21, 8, 17, tzinfo=PARIS),
    )
    first_feed = json.loads((tmp_path / "refectory-offers.json").read_text(encoding="utf-8"))
    offer_id = first_feed["offers"][0]["id"]
    approved = {
        "schemaVersion": 1,
        "codes": [
            {
                "offerId": offer_id,
                "code": "SEMAINE2",
                "confirmationCount": 2,
                "approvedAt": "2026-09-21T09:00:00+02:00",
                "lastConfirmedAt": "2026-09-21T09:05:00+02:00",
            }
        ],
    }
    (tmp_path / "refectory-approved-codes.json").write_text(
        json.dumps(approved),
        encoding="utf-8",
    )

    second_result = export_once(
        fetch_text=lambda: text.replace("SMS", "notification"),
        data_dir=tmp_path,
        now=datetime(2026, 9, 24, 8, 17, tzinfo=PARIS),
    )
    second_feed = json.loads((tmp_path / "refectory-offers.json").read_text(encoding="utf-8"))

    assert first_result == second_result == 0
    assert second_feed["offers"][0]["id"] == offer_id
    assert second_feed["offers"][0]["code"] == "SEMAINE2"
    assert second_feed["offers"][0]["codeSource"] == "contributor"
    assert second_feed["offers"][0]["confirmationCount"] == 2


def test_failed_export_preserves_last_valid_offers(tmp_path: Path) -> None:
    previous = {
        "schemaVersion": 1,
        "sourceUrl": "https://example.test",
        "offers": [{"id": "kept", "code": "KEEP"}],
    }
    (tmp_path / "refectory-offers.json").write_text(json.dumps(previous), encoding="utf-8")

    def fail() -> str:
        raise RuntimeError("source indisponible")

    result = export_once(
        fetch_text=fail,
        data_dir=tmp_path,
        now=datetime(2026, 9, 24, 8, 17, tzinfo=PARIS),
    )
    saved = json.loads((tmp_path / "refectory-offers.json").read_text(encoding="utf-8"))
    sync = json.loads((tmp_path / "refectory-sync.json").read_text(encoding="utf-8"))

    assert result == 1
    assert saved == previous
    assert sync["status"] == "error"
    assert sync["offerCount"] == 1
