from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Callable
from urllib.parse import urlparse

import requests

from .models import Offer
from .storage import read_json, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "public" / "data"
APPROVED_CODES_FILENAME = "refectory-approved-codes.json"
OFFERS_FILENAME = "refectory-offers.json"
MAX_FEED_SIZE = 512_000
FEED_TIMEOUT_SECONDS = 30
FEED_RETRY_DELAYS_SECONDS = (2, 5)

OFFER_ID_PATTERN = re.compile(
    r"^refectory-(?:\d{4}-\d{2}-\d{2}|sans-debut)-"
    r"(?:\d{4}-\d{2}-\d{2}|sans-fin)-[0-9a-f]{12}$"
)
CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]{2,31}$")
APPROVED_STATUSES = {
    "approved",
    "approuve",
    "approuvé",
    "approuvée",
    "validé",
    "valide",
    "validée",
}


@dataclass(frozen=True, slots=True)
class ApprovedCode:
    offer_id: str
    code: str
    confirmation_count: int = 1
    approved_at: str | None = None
    last_confirmed_at: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "offerId": self.offer_id,
            "code": self.code,
            "confirmationCount": self.confirmation_count,
            "approvedAt": self.approved_at,
            "lastConfirmedAt": self.last_confirmed_at,
        }


def normalise_code(raw_code: object) -> str:
    code = str(raw_code or "").strip().upper()
    if not CODE_PATTERN.fullmatch(code):
        raise ValueError("Le code doit contenir 3 à 32 lettres, chiffres ou tirets")
    return code


def _normalise_status(raw_status: object) -> str:
    return str(raw_status or "").strip().casefold()


def _parse_record(raw_record: object) -> ApprovedCode:
    if not isinstance(raw_record, dict):
        raise ValueError("Chaque code approuvé doit être un objet JSON")

    offer_id = str(raw_record.get("offerId") or raw_record.get("offer_id") or "").strip()
    if not OFFER_ID_PATTERN.fullmatch(offer_id):
        raise ValueError(f"Identifiant d'offre invalide : {offer_id!r}")

    try:
        confirmation_count = max(1, int(raw_record.get("confirmationCount", 1)))
    except (TypeError, ValueError) as error:
        raise ValueError(f"Nombre de confirmations invalide pour {offer_id}") from error

    return ApprovedCode(
        offer_id=offer_id,
        code=normalise_code(raw_record.get("code")),
        confirmation_count=confirmation_count,
        approved_at=str(raw_record.get("approvedAt") or "") or None,
        last_confirmed_at=str(raw_record.get("lastConfirmedAt") or "") or None,
    )


def load_approved_codes(data_dir: Path = DEFAULT_DATA_DIR) -> dict[str, ApprovedCode]:
    payload = read_json(
        data_dir / APPROVED_CODES_FILENAME,
        {"schemaVersion": 1, "codes": []},
    )
    if payload.get("schemaVersion") != 1 or not isinstance(payload.get("codes"), list):
        raise ValueError("Le registre des codes approuvés n'utilise pas le schéma attendu")

    records: dict[str, ApprovedCode] = {}
    for raw_record in payload["codes"]:
        record = _parse_record(raw_record)
        previous = records.get(record.offer_id)
        if previous and previous.code != record.code:
            raise ValueError(f"Plusieurs codes approuvés existent pour {record.offer_id}")
        records[record.offer_id] = record
    return records


def apply_approved_codes(
    offers: list[Offer],
    approved_codes: dict[str, ApprovedCode],
) -> list[Offer]:
    return [
        offer.with_contributor_code(
            approved_codes[offer.identifier].code,
            approved_codes[offer.identifier].confirmation_count,
        )
        if offer.identifier in approved_codes
        else offer
        for offer in offers
    ]


def _is_retryable_status(status_code: int) -> bool:
    return status_code in {408, 425, 429} or 500 <= status_code < 600


def _feed_error_summary(
    error: requests.RequestException | requests.JSONDecodeError,
    response: requests.Response | None,
) -> str:
    if isinstance(error, requests.Timeout):
        return "délai dépassé"
    if isinstance(error, requests.ConnectionError):
        return "connexion interrompue"
    if isinstance(error, requests.JSONDecodeError):
        status = response.status_code if response is not None else "inconnu"
        return f"réponse JSON invalide (HTTP {status})"
    if isinstance(error, requests.HTTPError) and response is not None:
        return f"HTTP {response.status_code}"
    return type(error).__name__


def fetch_approved_feed(feed_url: str) -> dict[str, Any]:
    parsed_url = urlparse(feed_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise ValueError("L'URL du flux approuvé doit utiliser HTTPS")

    attempts = len(FEED_RETRY_DELAYS_SECONDS) + 1
    for attempt in range(attempts):
        response: requests.Response | None = None
        try:
            response = requests.get(
                feed_url,
                headers={"User-Agent": "Systerel-ToulouseUtils/1.0"},
                timeout=FEED_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            if len(response.content) > MAX_FEED_SIZE:
                raise ValueError("Le flux approuvé dépasse la taille maximale autorisée")
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Le flux approuvé doit contenir un objet JSON")
            return payload
        except (
            requests.Timeout,
            requests.ConnectionError,
            requests.HTTPError,
            requests.JSONDecodeError,
        ) as error:
            should_retry = (
                isinstance(error, (requests.Timeout, requests.ConnectionError))
                or isinstance(error, requests.JSONDecodeError)
                or (
                    response is not None
                    and _is_retryable_status(response.status_code)
                )
            )
            summary = _feed_error_summary(error, response)
            if not should_retry or attempt == attempts - 1:
                raise RuntimeError(
                    f"Flux de contributions indisponible après "
                    f"{attempt + 1} tentative(s) : {summary}"
                ) from error

            delay = FEED_RETRY_DELAYS_SECONDS[attempt]
            print(
                f"Flux de contributions temporairement indisponible "
                f"(tentative {attempt + 1}/{attempts}) : {summary}. "
                f"Nouvelle tentative dans {delay} s.",
                file=sys.stderr,
            )
            time.sleep(delay)

    raise RuntimeError("Le flux approuvé n'a renvoyé aucune réponse")


def _incoming_records(payload: dict[str, Any]) -> list[ApprovedCode]:
    if payload.get("schemaVersion") != 1 or not isinstance(payload.get("codes"), list):
        raise ValueError("Le flux approuvé n'utilise pas le schéma attendu")

    records: list[ApprovedCode] = []
    for raw_record in payload["codes"]:
        if not isinstance(raw_record, dict):
            raise ValueError("Chaque soumission doit être un objet JSON")
        status = _normalise_status(raw_record.get("status"))
        if status and status not in APPROVED_STATUSES:
            continue
        records.append(_parse_record(raw_record))
    return records


def _aggregate_records(
    records: list[ApprovedCode],
    known_offer_ids: set[str],
) -> dict[str, ApprovedCode]:
    aggregated: dict[str, ApprovedCode] = {}
    for record in records:
        if record.offer_id not in known_offer_ids:
            print(f"Soumission ignorée pour une offre inconnue : {record.offer_id}")
            continue

        previous = aggregated.get(record.offer_id)
        if previous and previous.code != record.code:
            raise ValueError(f"Conflit de codes soumis pour {record.offer_id}")

        aggregated[record.offer_id] = ApprovedCode(
            offer_id=record.offer_id,
            code=record.code,
            confirmation_count=(previous.confirmation_count if previous else 0)
            + record.confirmation_count,
        )
    return aggregated


def _merge_records(
    existing: dict[str, ApprovedCode],
    incoming: dict[str, ApprovedCode],
    timestamp: str,
) -> dict[str, ApprovedCode]:
    merged = dict(existing)
    for offer_id, record in incoming.items():
        previous = existing.get(offer_id)
        if previous and previous.code != record.code:
            raise ValueError(
                f"Le code soumis pour {offer_id} diffère du code déjà approuvé"
            )

        confirmation_count = max(
            previous.confirmation_count if previous else 0,
            record.confirmation_count,
        )
        changed = (
            previous is None
            or confirmation_count != previous.confirmation_count
        )
        merged[offer_id] = ApprovedCode(
            offer_id=offer_id,
            code=record.code,
            confirmation_count=confirmation_count,
            approved_at=previous.approved_at if previous else timestamp,
            last_confirmed_at=timestamp if changed else previous.last_confirmed_at,
        )
    return merged


def _update_offer_feed(
    offers_payload: dict[str, Any],
    approved_codes: dict[str, ApprovedCode],
) -> dict[str, Any]:
    raw_offers = offers_payload.get("offers")
    if not isinstance(raw_offers, list):
        raise ValueError("Le flux des offres locales est invalide")

    offers: list[object] = []
    for raw_offer in raw_offers:
        if not isinstance(raw_offer, dict):
            raise ValueError("Une offre locale est invalide")
        offer = dict(raw_offer)
        record = approved_codes.get(str(offer.get("id") or ""))
        if record:
            current_code = str(offer.get("code") or "").strip().upper()
            code_source = offer.get("codeSource")
            if not current_code:
                offer["code"] = record.code
                offer["codeSource"] = "contributor"
                offer["confirmationCount"] = record.confirmation_count
            elif code_source == "contributor" and current_code == record.code:
                offer["confirmationCount"] = record.confirmation_count
            elif code_source == "contributor":
                raise ValueError(
                    f"Le flux local contient un code contradictoire pour {record.offer_id}"
                )
        offers.append(offer)
    return {**offers_payload, "offers": offers}


def sync_once(
    feed_url: str,
    data_dir: Path = DEFAULT_DATA_DIR,
    now: datetime | None = None,
    fetch_payload: Callable[[str], dict[str, Any]] = fetch_approved_feed,
) -> int:
    if not feed_url.strip():
        print("Flux de contributions non configuré : synchronisation ignorée.")
        return 0

    timestamp = (now or datetime.now().astimezone()).isoformat(timespec="seconds")
    offers_path = data_dir / OFFERS_FILENAME
    offers_payload = read_json(
        offers_path,
        {"schemaVersion": 1, "offers": []},
    )
    raw_offers = offers_payload.get("offers")
    if not isinstance(raw_offers, list):
        raise ValueError("Le flux des offres locales est invalide")
    known_offer_ids = {
        str(offer.get("id"))
        for offer in raw_offers
        if isinstance(offer, dict) and offer.get("id")
    }

    existing = load_approved_codes(data_dir)
    incoming = _aggregate_records(
        _incoming_records(fetch_payload(feed_url)),
        known_offer_ids,
    )
    merged = _merge_records(existing, incoming, timestamp)

    write_json(
        data_dir / APPROVED_CODES_FILENAME,
        {
            "schemaVersion": 1,
            "codes": [merged[key].as_dict() for key in sorted(merged)],
        },
    )
    write_json(offers_path, _update_offer_feed(offers_payload, merged))
    print(
        f"Synchronisation des contributions terminée : "
        f"{len(incoming)} offre(s) confirmée(s)."
    )
    return 0


def main() -> int:
    try:
        return sync_once(os.environ.get("REFECTORY_CODES_FEED_URL", ""))
    except Exception as error:
        print(f"Échec de la synchronisation des contributions : {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
