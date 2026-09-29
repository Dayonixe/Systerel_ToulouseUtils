from __future__ import annotations

from pathlib import Path
import re
import time

from bs4 import BeautifulSoup
from playwright.sync_api import (
    Error as PlaywrightError,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)


SOURCE_URL = "https://www.refectory.fr/conditions-des-offres-en-cours"
MAX_ATTEMPTS = 3
NAVIGATION_TIMEOUT_MS = 60_000
CONTENT_TIMEOUT_MS = 20_000
DIAGNOSTICS_DIR = Path("artifacts/refectory")


def _wait_for_offers(page: Page) -> None:
    heading = page.locator("h2").filter(has_text=re.compile(r"^\s*Offres en cours\s*$", re.IGNORECASE)).first
    heading.wait_for(state="visible", timeout=CONTENT_TIMEOUT_MS)
    heading.locator(
        "xpath=following-sibling::*[self::p or self::h2][normalize-space()][1]"
    ).wait_for(state="visible", timeout=CONTENT_TIMEOUT_MS)


def _handle_cookie_banner(page: Page) -> None:
    for label in ("Tout refuser", "Tout accepter"):
        try:
            page.get_by_text(label, exact=True).first.click(timeout=3_000)
            return
        except PlaywrightTimeoutError:
            continue


def _save_diagnostics(page: Page, status: str, error: Exception) -> None:
    try:
        DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)
        (DIAGNOSTICS_DIR / "failure.txt").write_text(
            f"Requested URL: {SOURCE_URL}\nFinal URL: {page.url}\nHTTP status: {status}\nError: {error}\n",
            encoding="utf-8",
        )
        (DIAGNOSTICS_DIR / "failure.html").write_text(page.content(), encoding="utf-8")
    except Exception as diagnostic_error:  # Diagnostics must not mask the root cause.
        print(f"Unable to save text diagnostics: {diagnostic_error}", flush=True)

    try:
        page.screenshot(path=str(DIAGNOSTICS_DIR / "failure.png"), timeout=5_000)
    except Exception as diagnostic_error:
        print(f"Unable to save screenshot diagnostics: {diagnostic_error}", flush=True)


def _extract_section_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    heading = next(
        (
            candidate
            for candidate in soup.find_all("h2")
            if candidate.get_text(" ", strip=True).casefold() == "offres en cours"
        ),
        None,
    )
    if heading is None:
        raise RuntimeError("La section 'Offres en cours' est introuvable")

    container = heading.find_parent()
    if container is None:
        raise RuntimeError("Le conteneur des offres Refectory est introuvable")
    return container.get_text("\n", strip=True)


def load_offers_text() -> str:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(locale="fr-FR")
        try:
            for attempt in range(1, MAX_ATTEMPTS + 1):
                status = "unknown"
                try:
                    response = page.goto(
                        SOURCE_URL,
                        wait_until="domcontentloaded",
                        timeout=NAVIGATION_TIMEOUT_MS,
                    )
                    status = str(response.status) if response else "no response"
                    if response is not None and not response.ok:
                        raise RuntimeError(f"La page Refectory répond avec le statut HTTP {status}")
                    _handle_cookie_banner(page)
                    _wait_for_offers(page)
                    return _extract_section_text(page.content())
                except (PlaywrightError, RuntimeError) as error:
                    print(
                        f"Tentative {attempt}/{MAX_ATTEMPTS} échouée — HTTP {status}: {error}",
                        flush=True,
                    )
                    if attempt == MAX_ATTEMPTS:
                        _save_diagnostics(page, status, error)
                        raise
                    time.sleep(2 * attempt)
        finally:
            browser.close()

    raise RuntimeError("Extraction Refectory interrompue")
