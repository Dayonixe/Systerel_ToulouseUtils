import pytest

from automation.refectory.scraper import _extract_section_text


def test_missing_current_offers_section_means_no_active_offer() -> None:
    html = """
    <main>
      <h1>Conditions des offres en cours</h1>
      <section>
        <h2>Offres de bienvenue</h2>
        <p>Une offre réservée aux nouveaux clients.</p>
      </section>
    </main>
    """

    assert _extract_section_text(html) == "Offres en cours\nOffres de bienvenue"


def test_unknown_page_structure_still_fails() -> None:
    with pytest.raises(RuntimeError, match="Offres en cours"):
        _extract_section_text("<main><h1>Page indisponible</h1></main>")
