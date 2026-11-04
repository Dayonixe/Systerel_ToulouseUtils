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


def test_daily_offer_format_is_split_and_parsed() -> None:
    text = """
Offres en cours
Opération 1 jour = 1 bon plan :
Jeudi 05/11/2026 :
Pour toute livraison le 05/11 d'une commande d'un montant minimum de 13€, on vous offre un muffin banoffee.
Mercredi 04/11/2026 :
Pour toute commande réalisée le 04/11, bénéficiez de 2€ offerts sur votre commande d'un montant minimum de 8€90 en utilisant le code reçu par mail ou notification app.
Mardi 03/11/2026
: Pour toute livraison le 03/11 d'une commande contenant une entrée et un plat, on vous offre un cannelé choco.
Lundi 02/11/2026 :
Pour toute commande réalisée le 02/11, bénéficiez de 2€ offerts sur votre commande d'un montant minimum de 13€ en utilisant le code VIVELUNDI.
Offres de bienvenue
"""

    offers = analyse_offers(text, reference=date(2026, 11, 4))

    assert len(offers) == 4
    assert [(offer.start_date, offer.end_date) for offer in offers] == [
        (date(2026, 11, 5), date(2026, 11, 5)),
        (date(2026, 11, 4), date(2026, 11, 4)),
        (date(2026, 11, 3), date(2026, 11, 3)),
        (date(2026, 11, 2), date(2026, 11, 2)),
    ]
    assert [offer.is_currently_valid for offer in offers] == [False, True, False, False]
    assert [offer.code for offer in offers] == [None, None, None, "VIVELUNDI"]
    assert [offer.requires_code for offer in offers] == [False, True, False, True]
    assert [offer.discount_label for offer in offers] == [None, "2 € offerts", None, "2 € offerts"]
    assert [offer.minimum_order_label for offer in offers] == ["13 €", "8,90 €", None, "13 €"]
    assert "Opération 1 jour" not in offers[0].original_text
