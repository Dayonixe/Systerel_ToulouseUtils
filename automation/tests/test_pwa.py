import json
from pathlib import Path
import struct
from urllib.parse import urljoin


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_DIR = PROJECT_ROOT / "public"
DEPLOYED_BASE_URL = "https://dayonixe.github.io/Systerel_ToulouseUtils/"


def _png_size(path: Path) -> tuple[int, int]:
    content = path.read_bytes()
    assert content[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", content[16:24])


def test_manifest_is_installable_and_subpath_safe() -> None:
    manifest_path = PUBLIC_DIR / "manifest.webmanifest"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_url = urljoin(DEPLOYED_BASE_URL, "manifest.webmanifest")

    assert manifest["name"] == "Le Hub Toulouse"
    assert manifest["short_name"] == "Le Hub"
    assert manifest["display"] == "standalone"
    assert manifest["theme_color"] == "#014489"
    assert manifest["background_color"] == "#060a10"
    assert urljoin(manifest_url, manifest["start_url"]) == DEPLOYED_BASE_URL
    assert urljoin(manifest_url, manifest["scope"]) == DEPLOYED_BASE_URL

    icons = manifest["icons"]
    assert {icon["sizes"] for icon in icons} >= {"192x192", "512x512"}
    assert any("maskable" in icon.get("purpose", "") for icon in icons)
    for icon in icons:
        icon_url = urljoin(manifest_url, icon["src"])
        assert icon_url.startswith(DEPLOYED_BASE_URL)
        assert not icon["src"].startswith("/")


def test_pwa_icon_files_have_the_declared_dimensions() -> None:
    assert _png_size(PUBLIC_DIR / "icons" / "pwa-192x192.png") == (192, 192)
    assert _png_size(PUBLIC_DIR / "icons" / "pwa-512x512.png") == (512, 512)
    assert _png_size(PUBLIC_DIR / "icons" / "pwa-maskable-512x512.png") == (
        512,
        512,
    )
    assert _png_size(PUBLIC_DIR / "icons" / "apple-touch-icon.png") == (180, 180)


def test_document_references_relative_pwa_assets() -> None:
    index_html = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")
    assert 'rel="manifest" href="%BASE_URL%manifest.webmanifest"' in index_html
    assert 'rel="icon" type="image/svg+xml" href="%BASE_URL%favicon.svg"' in index_html
    assert 'rel="apple-touch-icon" href="%BASE_URL%icons/apple-touch-icon.png"' in index_html
    assert 'name="theme-color" content="#060a10"' in index_html


def test_service_worker_is_present_and_keeps_dynamic_data_network_only() -> None:
    service_worker = (PUBLIC_DIR / "sw.js").read_text(encoding="utf-8")
    assert 'url.pathname.includes("/data/")' in service_worker
    assert 'url.pathname.endsWith(".json")' in service_worker
    assert "return;" in service_worker
