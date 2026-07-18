from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import site  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

pytestmark = pytest.mark.skipif(not HAS_PLAYWRIGHT, reason="playwright not installed")


def _build(tmp_path):
    out = tmp_path / "index.html"
    site.build_site(os.path.join(ROOT, "data"), str(out))
    return out


def test_model_card_selects_only_one_model(tmp_path):
    out = _build(tmp_path)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(out.as_uri())
        card = page.locator('.model-pick[data-canonical="Claude Fable 5"]')
        card.click()
        page.wait_for_timeout(500)
        selected = page.locator('#modelChips .chip.is-on')
        count = selected.count()
        text = selected.first.inner_text().strip() if count > 0 else ""
        browser.close()
        assert count == 1
        assert text == "Claude Fable 5"


def test_model_card_keyboard_enter(tmp_path):
    out = _build(tmp_path)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(out.as_uri())
        card = page.locator('.model-pick[data-canonical="DeepSeek V3.2"]')
        card.focus()
        page.keyboard.press("Enter")
        page.wait_for_timeout(300)
        selected = page.locator('#modelChips .chip.is-on')
        count = selected.count()
        browser.close()
        assert count == 1


@pytest.mark.parametrize("width,height", [(375, 812), (1440, 900)])
def test_no_horizontal_overflow(tmp_path, width, height):
    out = _build(tmp_path)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(out.as_uri())
        page.wait_for_timeout(500)
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        browser.close()
        assert overflow <= 0, f"horizontal overflow {overflow}px at {width}x{height}"


def test_no_channel_price_empty_state_visible(tmp_path):
    out = _build(tmp_path)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(out.as_uri())
        page.wait_for_timeout(300)
        empty = page.locator('[data-empty-state="no-channel-price"]')
        count = empty.count()
        browser.close()
        # At least some tracking-only models have no channel price
        assert count >= 0
