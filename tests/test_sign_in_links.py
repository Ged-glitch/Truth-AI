from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIGN_IN_PAGE = ROOT / "app" / "sign-in" / "index.html"
ROUTE_LOADER = ROOT / "app" / "route-loader.js"


def test_sign_in_back_to_app_links_to_public_site() -> None:
    html = SIGN_IN_PAGE.read_text(encoding="utf-8")
    assert '<a class="ghost-link" href="/">Back to app</a>' in html


def test_route_loader_fallback_links_to_public_site() -> None:
    source = ROUTE_LOADER.read_text(encoding="utf-8")
    assert 'href="/">Return to the site</a>' in source
