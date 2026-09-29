from datetime import date

from automation.refectory.parser import (
    analyse_offers,
    extract_code,
    extract_discount,
    extract_minimum_order,
    parse_offer_dates,
)


def test_end_date_is_inclusive() -> None:
    text = """
Offres en cours
Du 21/09 au 25/09, 2€ offerts avec le code TOULOUSE2. Uniquement à Toulouse.
Offres de bienvenue
"""
    offers = analyse_offers(text, reference=date(2026, 9, 25))
    assert offers[0].is_currently_valid is True


def test_range_crosses_new_year() -> None:
    start, end = parse_offer_dates("Du 28/12 au 05/01", reference=date(2027, 1, 2))
    assert start == date(2026, 12, 28)
    assert end == date(2027, 1, 5)


def test_code_requires_promotional_context() -> None:
    assert extract_code("REFECTORY propose une offre sans code") is None
    assert extract_code("Utilisez le code BONPLAN25 dans votre panier") == "BONPLAN25"


def test_discount_and_minimum_are_not_confused() -> None:
    text = "1€ de réduction avec le code TEST123 pour un montant minimum de 7€90"
    assert extract_discount(text) == "1 € offerts"
    assert extract_minimum_order(text) == "7,90 €"


def test_toulouse_and_global_offers_are_distinguished() -> None:
    text = """
Offres en cours
Du 21/09 au 25/09, 1€ offert avec le code GLOBAL1.
Du 21/09 au 25/09, 2€ offerts avec le code TLSE2. Uniquement à Toulouse.
Du 21/09 au 25/09, 3€ offerts avec le code PARIS3. Uniquement à Paris.
Offres de bienvenue
"""
    offers = analyse_offers(text, reference=date(2026, 9, 24))
    assert [offer.scope for offer in offers] == ["global", "toulouse", "city"]
    assert [offer.applies_to_toulouse() for offer in offers] == [True, True, False]


def test_offer_identifier_does_not_change_when_the_code_or_wording_changes() -> None:
    without_code = """
Offres en cours
Du 21/09 au 25/09, 2€ offerts pour un montant minimum de 8€. Code envoyé par SMS.
Offres de bienvenue
"""
    with_code = """
Offres en cours
Du 21/09 au 25/09 : 2€ offerts dès 8€, utilisez le code SEMAINE2.
Offres de bienvenue
"""

    first = analyse_offers(without_code, reference=date(2026, 9, 21))[0]
    second = analyse_offers(with_code, reference=date(2026, 9, 24))[0]

    assert first.identifier == second.identifier
