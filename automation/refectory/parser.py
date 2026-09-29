from __future__ import annotations

from datetime import date
import hashlib
import re
import unicodedata

from .models import Offer


KNOWN_CITIES = (
    "Antony",
    "Aulnay",
    "Avelin",
    "Bordeaux",
    "Caen",
    "Clermont",
    "Corbas",
    "Dijon",
    "Gennevilliers",
    "Grenoble",
    "Lille",
    "Limonest",
    "Lyon",
    "Marseille",
    "Metz",
    "Montpellier",
    "Nancy",
    "Nantes",
    "Nice",
    "Paris",
    "Rennes",
    "Rouen",
    "Strasbourg",
    "Toulouse",
    "Tours",
    "Trappes",
    "Vaulx-en-Velin",
)

MONTHS_FR = {
    "janvier": 1,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "decembre": 12,
}

SECTION_ENDINGS = ("offres de bienvenue", "parrainage")


def _ascii(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(character)
    )


def _best_range(
    start_day: int,
    start_month: int,
    end_day: int,
    end_month: int,
    reference: date,
) -> tuple[date, date]:
    candidates: list[tuple[date, date]] = []
    for start_year in range(reference.year - 1, reference.year + 2):
        end_year = start_year + (1 if (end_month, end_day) < (start_month, start_day) else 0)
        candidates.append(
            (
                date(start_year, start_month, start_day),
                date(end_year, end_month, end_day),
            )
        )

    containing_reference = [period for period in candidates if period[0] <= reference <= period[1]]
    if containing_reference:
        return containing_reference[0]

    return min(
        candidates,
        key=lambda period: min(abs((reference - period[0]).days), abs((reference - period[1]).days)),
    )


def parse_offer_dates(text: str, reference: date | None = None) -> tuple[date | None, date | None]:
    """Extract an inclusive validity period, including year transitions."""

    reference = reference or date.today()
    full_numeric = re.search(
        r"\bdu\s+(\d{1,2})/(\d{1,2})/(\d{4})\s+au\s+(\d{1,2})/(\d{1,2})/(\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    if full_numeric:
        start_day, start_month, start_year, end_day, end_month, end_year = map(int, full_numeric.groups())
        return (
            date(start_year, start_month, start_day),
            date(end_year, end_month, end_day),
        )

    numeric = re.search(
        r"\bdu\s+(\d{1,2})/(\d{1,2})\s+au\s+(\d{1,2})/(\d{1,2})",
        text,
        flags=re.IGNORECASE,
    )
    if numeric:
        start_day, start_month, end_day, end_month = map(int, numeric.groups())
        return _best_range(start_day, start_month, end_day, end_month, reference)

    textual = re.search(
        r"\bdu\s+(\d{1,2})(?:er)?\s+au\s+(\d{1,2})(?:er)?\s+([a-zA-ZÀ-ÿ-]+)",
        text,
        flags=re.IGNORECASE,
    )
    if textual:
        start_day, end_day, month_name = textual.groups()
        month = MONTHS_FR.get(_ascii(month_name).lower())
        if month:
            return _best_range(int(start_day), month, int(end_day), month, reference)

    return None, None


def extract_code(text: str) -> str | None:
    """Extract a code only when introduced by explicit promotional wording."""

    patterns = (
        r"(?:avec|indiquant|utilisez?|saisissez?)\s+(?:le\s+)?code(?:\s+promo)?\s*[:\-]?\s*[\"“]?([A-Z0-9][A-Z0-9-]{3,})",
        r"code\s+promo(?:tionnel)?\s*[:\-]?\s*[\"“]?([A-Z0-9][A-Z0-9-]{3,})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return None


def _format_euros(raw_amount: str) -> str:
    amount = raw_amount.strip().replace(".", ",")
    compact = re.fullmatch(r"(\d+)€(\d{1,2})", amount)
    if compact:
        return f"{compact.group(1)},{compact.group(2).ljust(2, '0')} €"
    if not amount.endswith("€"):
        amount = f"{amount} €"
    else:
        amount = amount[:-1].rstrip() + " €"
    return amount


def extract_discount(text: str) -> str | None:
    percent = re.search(r"(?:-|de\s+)(\d{1,2})\s*%", text, flags=re.IGNORECASE)
    if percent:
        return f"-{percent.group(1)} %"

    patterns = (
        r"(\d+(?:[.,]\d+)?)\s*€\s+(?:de\s+)?(?:réduction|offerts?|offertes?)",
        r"(?:réduction|remise)\s+(?:immédiate\s+)?de\s+(\d+(?:[.,]\d+)?)\s*€",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return f"{_format_euros(match.group(1))} offerts"
    return None


def extract_minimum_order(text: str) -> str | None:
    match = re.search(
        r"(?:montant\s+minimum(?:\s+de)?|minimum\s+de|dès)\s*([0-9]+(?:[€.,][0-9]{1,2})?\s*€?)",
        text,
        flags=re.IGNORECASE,
    )
    return _format_euros(match.group(1)) if match else None


def extract_cities(text: str) -> tuple[str, ...]:
    matches: list[tuple[int, str]] = []
    for city in KNOWN_CITIES:
        match = re.search(rf"\b{re.escape(city)}\b", text, flags=re.IGNORECASE)
        if match:
            matches.append((match.start(), city))
    return tuple(city for _, city in sorted(matches))


def _split_offers(full_text: str) -> list[str]:
    lines = [line.strip() for line in full_text.splitlines() if line.strip()]
    try:
        start_index = next(index for index, line in enumerate(lines) if line.casefold() == "offres en cours")
    except StopIteration:
        return []

    section: list[str] = []
    for line in lines[start_index + 1 :]:
        if any(line.casefold().startswith(ending) for ending in SECTION_ENDINGS):
            break
        section.append(line)

    offers: list[list[str]] = []
    current: list[str] = []
    for line in section:
        if re.match(r"^du\s+\d", line, flags=re.IGNORECASE) and current:
            offers.append(current)
            current = []
        current.append(line)
    if current:
        offers.append(current)

    return ["\n".join(lines).strip() for lines in offers if lines]


def _identifier(
    start: date | None,
    end: date | None,
    discount: str | None,
    minimum_order: str | None,
    scope: str,
) -> str:
    """Build a semantic identifier that stays stable for the whole offer period."""

    start_key = start.isoformat() if start else "sans-debut"
    end_key = end.isoformat() if end else "sans-fin"
    fingerprint = "|".join((start_key, end_key, discount or "", minimum_order or "", scope))
    digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:12]
    return f"refectory-{start_key}-{end_key}-{digest}"


def analyse_offers(full_text: str, reference: date | None = None) -> list[Offer]:
    reference = reference or date.today()
    results: list[Offer] = []

    for offer_text in _split_offers(full_text):
        start, end = parse_offer_dates(offer_text, reference)
        code = extract_code(offer_text)
        cities = extract_cities(offer_text)
        scope = "toulouse" if "Toulouse" in cities else "city" if cities else "global"
        is_valid = bool(start and end and start <= reference <= end)
        discount = extract_discount(offer_text)
        minimum_order = extract_minimum_order(offer_text)

        results.append(
            Offer(
                identifier=_identifier(start, end, discount, minimum_order, scope),
                original_text=offer_text[:5000],
                start_date=start,
                end_date=end,
                code=code,
                discount_label=discount,
                minimum_order_label=minimum_order,
                cities=cities,
                scope=scope,
                is_currently_valid=is_valid,
                code_source="refectory" if code else None,
            )
        )

    return results
