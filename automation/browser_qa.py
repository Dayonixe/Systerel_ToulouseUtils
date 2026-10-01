from __future__ import annotations

from datetime import datetime, timedelta
import json
from pathlib import Path
import sys
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from playwright.sync_api import Browser, Page, sync_playwright


DEFAULT_URL = "http://127.0.0.1:5173"
ARTIFACTS = Path("artifacts/qa")
AXE_SCRIPT = Path("node_modules/axe-core/axe.min.js")
EXPECTED_ICON_SIZES = {
    "192x192": (192, 192),
    "512x512": (512, 512),
}


def _assert_page_shape(page: Page) -> None:
    assert page.locator("header").count() == 1
    assert page.locator("main").count() == 1
    assert page.locator("footer").count() == 1
    assert page.locator("h1").count() == 1
    assert page.locator("#offers-title").count() == 1
    has_overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
    assert not has_overflow, "La page déborde horizontalement"


def _assert_pwa(page: Page, base_url: str) -> None:
    manifest_href = page.locator('link[rel="manifest"]').get_attribute("href")
    assert manifest_href, "Le document ne référence aucun manifest"
    manifest_url = urljoin(base_url, manifest_href)
    manifest_response = page.request.get(manifest_url)
    assert manifest_response.ok, (
        f"Manifest inaccessible : {manifest_response.status} {manifest_url}"
    )
    manifest = manifest_response.json()

    assert manifest["name"] == "Le Hub Toulouse"
    assert manifest["short_name"] == "Le Hub"
    assert manifest["display"] == "standalone"
    expected_scope = urljoin(base_url, "./")
    assert urljoin(manifest_url, manifest["start_url"]) == expected_scope
    assert urljoin(manifest_url, manifest["scope"]) == expected_scope

    icon_sizes = {icon["sizes"] for icon in manifest["icons"]}
    assert EXPECTED_ICON_SIZES.keys() <= icon_sizes
    assert any("maskable" in icon.get("purpose", "") for icon in manifest["icons"])
    for icon in manifest["icons"]:
        expected_size = EXPECTED_ICON_SIZES[icon["sizes"]]
        icon_url = urljoin(manifest_url, icon["src"])
        icon_response = page.request.get(icon_url)
        assert icon_response.ok, f"Icône inaccessible : {icon_response.status} {icon_url}"
        dimensions = page.evaluate(
            """
            async ({ url }) => {
              const image = new Image();
              image.src = url;
              await image.decode();
              return [image.naturalWidth, image.naturalHeight];
            }
            """,
            {"url": icon_url},
        )
        assert tuple(dimensions) == expected_size

    service_worker_url = urljoin(expected_scope, "sw.js")
    service_worker_response = page.request.get(service_worker_url)
    assert service_worker_response.ok, (
        f"Service worker inaccessible : {service_worker_response.status} "
        f"{service_worker_url}"
    )
    registration_scope = page.evaluate(
        """
        async () => {
          if (!('serviceWorker' in navigator)) {
            throw new Error('Service workers indisponibles');
          }
          const timeout = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('Service worker non prêt après 8 s')), 8000);
          });
          const registration = await Promise.race([
            navigator.serviceWorker.ready,
            timeout,
          ]);
          return registration.scope;
        }
        """
    )
    assert registration_scope == expected_scope

    devtools = page.context.new_cdp_session(page)
    try:
        app_manifest = devtools.send("Page.getAppManifest")
        assert not app_manifest.get("errors"), (
            f"Erreurs de manifest Chromium : {app_manifest['errors']}"
        )
        installability = devtools.send("Page.getInstallabilityErrors")
        assert not installability["installabilityErrors"], (
            "Erreurs d’installabilité Chromium : "
            f"{installability['installabilityErrors']}"
        )
    finally:
        devtools.detach()


def _assert_accessibility(page: Page, state: str) -> None:
    page.add_script_tag(path=str(AXE_SCRIPT))
    report = page.evaluate(
        """
        async () => await axe.run(document, {
          runOnly: {
            type: 'tag',
            values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']
          }
        })
        """
    )
    violations = []
    for violation in report["violations"]:
        targets = ", ".join(
            "/".join(node["target"]) for node in violation.get("nodes", [])
        )
        violations.append(
            f"{violation['id']} ({violation.get('impact', 'impact inconnu')}) : {targets}"
        )
    assert not violations, f"Violations WCAG dans l’état {state} : {violations}"


def _capture_empty_state(browser: Browser, base_url: str, width: int, height: int) -> None:
    page = browser.new_page(viewport={"width": width, "height": height}, locale="fr-FR")
    source_url = "https://www.refectory.fr/conditions-des-offres-en-cours"
    empty_feed = {"schemaVersion": 1, "sourceUrl": source_url, "offers": []}
    sync = {
        "schemaVersion": 1,
        "sourceUrl": source_url,
        "status": "ok",
        "lastAttemptAt": datetime.now(ZoneInfo("Europe/Paris")).isoformat(timespec="seconds"),
        "lastSuccessAt": datetime.now(ZoneInfo("Europe/Paris")).isoformat(timespec="seconds"),
        "offerCount": 0,
        "codeCount": 0,
        "waitingForCodeCount": 0,
        "message": None,
    }
    page.route(
        "**/data/refectory-offers.json",
        lambda route: route.fulfill(content_type="application/json", body=json.dumps(empty_feed)),
    )
    page.route(
        "**/data/refectory-sync.json",
        lambda route: route.fulfill(content_type="application/json", body=json.dumps(sync)),
    )
    page.goto(base_url, wait_until="networkidle")
    page.get_by_role("heading", name="Aucune offre active aujourd’hui").wait_for()
    _assert_page_shape(page)
    _assert_accessibility(page, f"vide {width}px")
    assert page.get_by_role("link", name="Consulter la source").get_attribute("href") == (
        "https://www.refectory.fr/conditions-des-offres-en-cours"
    )
    page.screenshot(path=str(ARTIFACTS / f"dashboard-empty-{width}.png"), full_page=True)
    page.close()


def _capture_offer_state(browser: Browser, base_url: str) -> None:
    context = browser.new_context(
        viewport={"width": 1440, "height": 1000},
        locale="fr-FR",
        permissions=["clipboard-read", "clipboard-write"],
    )
    page = context.new_page()
    source_url = "https://www.refectory.fr/conditions-des-offres-en-cours"
    now = datetime.now(ZoneInfo("Europe/Paris"))
    start_date = (now.date() - timedelta(days=1)).isoformat()
    end_date = (now.date() + timedelta(days=2)).isoformat()
    timestamp = now.isoformat(timespec="seconds")
    feed = {
        "schemaVersion": 1,
        "sourceUrl": source_url,
        "offers": [
            {
                "id": "qa-offer",
                "originalText": "2 € offerts dès 7,90 € d’achat avec le code QA2026.",
                "startDate": start_date,
                "endDate": end_date,
                "code": "QA2026",
                "codeSource": "contributor",
                "confirmationCount": 2,
                "discountLabel": "2 € offerts",
                "minimumOrderLabel": "7,90 €",
                "cities": ["Toulouse"],
                "scope": "toulouse",
                "isCurrentlyValid": True,
            },
            {
                "id": "qa-waiting-offer",
                "originalText": "1 € offert. Le code est envoyé par notification.",
                "startDate": start_date,
                "endDate": end_date,
                "code": "",
                "codeSource": None,
                "confirmationCount": 0,
                "discountLabel": "1 € offert",
                "minimumOrderLabel": None,
                "cities": [],
                "scope": "global",
                "isCurrentlyValid": True,
            }
        ],
    }
    sync = {
        "schemaVersion": 1,
        "sourceUrl": source_url,
        "status": "ok",
        "lastAttemptAt": timestamp,
        "lastSuccessAt": timestamp,
        "offerCount": 2,
        "codeCount": 1,
        "waitingForCodeCount": 1,
        "message": None,
    }
    page.route(
        "**/data/refectory-offers.json",
        lambda route: route.fulfill(content_type="application/json", body=json.dumps(feed)),
    )
    page.route(
        "**/data/refectory-sync.json",
        lambda route: route.fulfill(content_type="application/json", body=json.dumps(sync)),
    )
    page.goto(base_url, wait_until="networkidle")
    page.get_by_text("QA2026", exact=True).wait_for()
    page.get_by_text("Code recherché", exact=True).wait_for()
    page.get_by_text("Vous avez reçu le code ?", exact=True).wait_for()
    _assert_page_shape(page)
    _assert_accessibility(page, "avec offre")
    page.locator(".code-button").click()
    page.get_by_text("Code copié", exact=True).wait_for()
    page.screenshot(path=str(ARTIFACTS / "dashboard-offer-1440.png"), full_page=True)
    context.close()


def run(base_url: str = DEFAULT_URL) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []
    failed_requests: list[str] = []
    bad_responses: list[str] = []

    def record_failed_request(request) -> None:
        failure = request.failure or "échec inconnu"
        if "ERR_ABORTED" not in failure:
            failed_requests.append(f"{request.url} ({failure})")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        monitor = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="fr-FR")
        monitor.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        monitor.on("pageerror", lambda error: page_errors.append(str(error)))
        monitor.on("requestfailed", record_failed_request)
        monitor.on(
            "response",
            lambda response: bad_responses.append(f"{response.status} {response.url}")
            if response.status >= 400
            else None,
        )
        monitor.goto(base_url, wait_until="networkidle")
        _assert_page_shape(monitor)
        _assert_pwa(monitor, base_url)
        monitor.close()

        _capture_empty_state(browser, base_url, 375, 812)
        _capture_empty_state(browser, base_url, 768, 1024)
        _capture_offer_state(browser, base_url)
        browser.close()

    assert not console_errors, f"Erreurs console : {console_errors}"
    assert not page_errors, f"Erreurs JavaScript : {page_errors}"
    assert not failed_requests, f"Requêtes en échec : {failed_requests}"
    assert not bad_responses, f"Réponses HTTP en échec : {bad_responses}"
    print(
        "QA navigateur réussie : PWA, desktop, tablette, mobile, "
        "offre avec code et code recherché."
    )


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL)
