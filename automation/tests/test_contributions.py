from datetime import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import requests

from automation.refectory import contributions
from automation.refectory.contributions import fetch_approved_feed, sync_once


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


def _response(status_code: int, payload: dict[str, object]) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = json.dumps(payload).encode("utf-8")
    response.url = "https://example.test/codes"
    return response


def test_feed_fetch_retries_temporary_timeouts(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"schemaVersion": 1, "codes": []}
    responses: list[requests.Response | Exception] = [
        requests.Timeout("délai dépassé"),
        requests.ConnectionError("connexion interrompue"),
        _response(200, payload),
    ]
    delays: list[int] = []
    timeouts: list[int] = []

    def fake_get(*_args: object, **kwargs: object) -> requests.Response:
        timeouts.append(int(kwargs["timeout"]))
        result = responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(contributions.requests, "get", fake_get)
    monkeypatch.setattr(contributions.time, "sleep", delays.append)

    assert fetch_approved_feed("https://example.test/codes") == payload
    assert delays == [2, 5]
    assert timeouts == [30, 30, 30]


def test_feed_fetch_retries_temporary_http_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {"schemaVersion": 1, "codes": []}
    responses = [_response(503, {"error": "indisponible"}), _response(200, payload)]
    delays: list[int] = []

    def fake_get(*_args: object, **_kwargs: object) -> requests.Response:
        return responses.pop(0)

    monkeypatch.setattr(contributions.requests, "get", fake_get)
    monkeypatch.setattr(contributions.time, "sleep", delays.append)

    assert fetch_approved_feed("https://example.test/codes") == payload
    assert delays == [2]


def test_feed_fetch_does_not_retry_permanent_http_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    delays: list[int] = []

    def fake_get(*_args: object, **_kwargs: object) -> requests.Response:
        nonlocal calls
        calls += 1
        return _response(400, {"error": "requête invalide"})

    monkeypatch.setattr(contributions.requests, "get", fake_get)
    monkeypatch.setattr(contributions.time, "sleep", delays.append)

    with pytest.raises(RuntimeError, match="HTTP 400") as error:
        fetch_approved_feed("https://example.test/codes")

    assert calls == 1
    assert delays == []
    assert "example.test" not in str(error.value)


def test_feed_fetch_retries_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"schemaVersion": 1, "codes": []}
    invalid_response = requests.Response()
    invalid_response.status_code = 200
    invalid_response._content = b"<html>temporary upstream error</html>"
    invalid_response.url = "https://example.test/codes"
    responses = [invalid_response, _response(200, payload)]
    delays: list[int] = []

    def fake_get(*_args: object, **_kwargs: object) -> requests.Response:
        return responses.pop(0)

    monkeypatch.setattr(contributions.requests, "get", fake_get)
    monkeypatch.setattr(contributions.time, "sleep", delays.append)

    assert fetch_approved_feed("https://example.test/codes") == payload
    assert delays == [2]


def test_approved_submissions_are_aggregated_and_attached(tmp_path: Path) -> None:
    _write_offer_feed(tmp_path)
    payload = {
        "schemaVersion": 1,
        "codes": [
            {"offerId": OFFER_ID, "code": "SEMAINE2"},
            {"offerId": OFFER_ID, "code": "semaine2"},
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
    assert "receivedVia" not in registry["codes"][0]
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
