from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIGN_IN_PAGE = ROOT / "app" / "sign-in" / "index.html"
ROUTE_LOADER = ROOT / "app" / "route-loader.js"
TRUTH_KERNEL = ROOT / "frontend" / "TruthKernel.dc.html"
TRUTH_STUDIO = ROOT / "frontend" / "Truth-Kernel-Studio.dc.html"
APP_ROUTE = ROOT / "app" / "route-loader.js"
AUTH_CLIENT = ROOT / "app" / "auth-client.js"


def test_sign_in_back_to_app_links_to_public_site() -> None:
    html = SIGN_IN_PAGE.read_text(encoding="utf-8")
    assert '<a class="ghost-link" href="/">Back to app</a>' in html


def test_route_loader_fallback_links_to_public_site() -> None:
    source = ROUTE_LOADER.read_text(encoding="utf-8")
    assert 'href="/">Return to the site</a>' in source


def test_truth_kernel_mobile_header_exposes_sign_in_link() -> None:
    html = TRUTH_KERNEL.read_text(encoding="utf-8")
    assert 'sc-if value="{{ isMobile }}"' in html
    assert 'href="{{ signInHref }}"' in html
    assert 'signInHref: "/app/sign-in?return=/app/overview"' in html


def test_truth_studio_header_exposes_auth_controls() -> None:
    html = TRUTH_STUDIO.read_text(encoding="utf-8")
    assert "data-auth-controls" in html
    assert "data-auth-signin-link" in html


def test_route_loader_injects_auth_client() -> None:
    source = APP_ROUTE.read_text(encoding="utf-8")
    assert "/app/auth-client.js" in source


def test_auth_client_compacts_session_badge_for_mobile() -> None:
    source = AUTH_CLIENT.read_text(encoding="utf-8")
    assert "max-width:min(38vw,220px)" in source
    assert "text-overflow:ellipsis" in source
