from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FAVICON_PATH = PROJECT_ROOT / "public" / "favicon.svg"
ICONS_DIR = PROJECT_ROOT / "public" / "icons"

MASKABLE_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="blue" x1="64" y1="32" x2="448" y2="480" gradientUnits="userSpaceOnUse">
      <stop stop-color="#07569f"/>
      <stop offset="1" stop-color="#014489"/>
    </linearGradient>
  </defs>
  <rect width="512" height="512" fill="url(#blue)"/>
  <rect x="165.33" y="144" width="58.67" height="224" fill="#fff"/>
  <rect x="288" y="144" width="58.67" height="224" fill="#fff"/>
  <rect x="224" y="222.93" width="64" height="59.74" fill="#fff"/>
</svg>
""".strip()


def _render(page: Page, svg: str, size: int, output: Path) -> None:
    page.set_viewport_size({"width": size, "height": size})
    page.set_content(
        "<style>html,body{margin:0;width:100%;height:100%;overflow:hidden}</style>"
        f"{svg}"
    )
    page.locator("svg").evaluate(
        "(element) => { element.style.width = '100%'; element.style.height = '100%'; }"
    )
    page.screenshot(path=str(output), omit_background=True)


def main() -> None:
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    favicon_svg = FAVICON_PATH.read_text(encoding="utf-8")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        _render(page, favicon_svg, 192, ICONS_DIR / "pwa-192x192.png")
        _render(page, favicon_svg, 512, ICONS_DIR / "pwa-512x512.png")
        _render(page, MASKABLE_SVG, 512, ICONS_DIR / "pwa-maskable-512x512.png")
        _render(page, MASKABLE_SVG, 180, ICONS_DIR / "apple-touch-icon.png")
        browser.close()

    print(f"Icônes PWA générées dans {ICONS_DIR}")


if __name__ == "__main__":
    main()
