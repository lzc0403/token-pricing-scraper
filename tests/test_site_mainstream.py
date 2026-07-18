from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import site  # noqa: E402


def test_site_data_merges_catalog_canons_into_filters():
    data = site._build_site_data(os.path.join(ROOT, "data"))
    catalog_canons = {
        m["canonical"]
        for vendors in data["mainstream_sections"].values()
        for vendor in vendors
        for m in vendor["models"]
    }
    assert catalog_canons <= set(data["filter_meta"]["models"])


def test_site_data_has_six_domestic_vendor_slots():
    data = site._build_site_data(os.path.join(ROOT, "data"))
    assert [v["id"] for v in data["mainstream_sections"]["domestic"]] == [
        "deepseek", "qwen", "glm", "kimi", "minimax", "doubao"
    ]


def test_site_data_has_three_overseas_vendor_slots():
    data = site._build_site_data(os.path.join(ROOT, "data"))
    assert [v["id"] for v in data["mainstream_sections"]["overseas"]] == [
        "openai", "anthropic", "google"
    ]


def test_site_data_claude_four_models_renderable():
    data = site._build_site_data(os.path.join(ROOT, "data"))
    overseas = data["mainstream_sections"]["overseas"]
    anthropic = next(v for v in overseas if v["id"] == "anthropic")
    canons = {m["canonical"] for m in anthropic["models"]}
    assert {
        "Claude Fable 5", "Claude Opus 4.8", "Claude Sonnet 5", "Claude Haiku 4.5"
    } <= canons


def test_site_data_mainstream_models_have_display_tier():
    data = site._build_site_data(os.path.join(ROOT, "data"))
    for vendors in data["mainstream_sections"].values():
        for vendor in vendors:
            for model in vendor["models"]:
                assert "display_tier" in model
                assert "context_label" in model
                assert "has_channel_price" in model


def test_site_data_has_mainstream_flags():
    data = site._build_site_data(os.path.join(ROOT, "data"))
    assert "has_domestic_mainstream" in data
    assert "has_overseas_mainstream" in data
    assert isinstance(data["has_domestic_mainstream"], bool)
    assert isinstance(data["has_overseas_mainstream"], bool)


def test_build_site_generates_without_error(tmp_path):
    out = tmp_path / "index.html"
    site.build_site(os.path.join(ROOT, "data"), str(out))
    html = out.read_text(encoding="utf-8")
    assert len(html) > 1000


def test_generated_html_has_symmetric_mainstream_sections(tmp_path):
    out = tmp_path / "index.html"
    site.build_site(os.path.join(ROOT, "data"), str(out))
    html = out.read_text(encoding="utf-8")
    assert 'data-section="domestic-mainstream"' in html
    assert 'data-section="overseas-mainstream"' in html
    assert html.count('data-vendor="') >= 9
    for name in ["Fable 5", "Opus 4.8", "Sonnet 5", "Haiku 4.5"]:
        assert name in html
    assert 'data-empty-state="no-channel-price"' in html


def test_generated_html_claude_context_attributes(tmp_path):
    out = tmp_path / "index.html"
    site.build_site(os.path.join(ROOT, "data"), str(out))
    html = out.read_text(encoding="utf-8")
    # Fable 5, Opus 4.8, Sonnet 5 = 1M; Haiku 4.5 = 200K
    assert 'data-context="1000000"' in html
    assert 'data-context="200000"' in html


def test_generated_html_model_cards_have_canonical_attr(tmp_path):
    out = tmp_path / "index.html"
    site.build_site(os.path.join(ROOT, "data"), str(out))
    html = out.read_text(encoding="utf-8")
    assert 'data-canonical="Claude Fable 5"' in html
    assert 'data-canonical="DeepSeek V3.2"' in html


def test_generated_html_no_seedance_in_domestic_mainstream(tmp_path):
    out = tmp_path / "index.html"
    site.build_site(os.path.join(ROOT, "data"), str(out))
    html = out.read_text(encoding="utf-8")
    # Seedance is a video model, must not appear in domestic text mainstream cards
    domestic_start = html.find('data-section="domestic-mainstream"')
    overseas_start = html.find('data-section="overseas-mainstream"')
    if domestic_start >= 0 and overseas_start >= 0:
        domestic_html = html[domestic_start:overseas_start]
        assert "Seedance" not in domestic_html
