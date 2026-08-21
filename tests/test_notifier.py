from __future__ import annotations

import os
import sys
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import notifier  # noqa: E402

DELTAS = [
    {"canonical": "GPT-5", "source": "openai", "field": "input", "old": 5.0, "new": 4.0, "currency": "USD"},
    {"canonical": "DeepSeek V4", "source": "deepseek", "field": "output", "old": 12.0, "new": 13.0, "currency": "CNY"},
]


def test_build_message_format():
    msg = notifier.build_message(DELTAS, "2026-08-22")
    assert "2026-08-22" in msg
    assert "GPT-5" in msg
    assert "5.0USD → 4.0USD" in msg
    assert "DeepSeek V4" in msg
    assert "12.0CNY → 13.0CNY" in msg


def test_payload_feishu():
    p = notifier._payload("hi", "feishu")
    assert p["msg_type"] == "markdown"
    assert p["content"]["text"] == "hi"


def test_payload_wecom():
    p = notifier._payload("hi", "wecom")
    assert p["msgtype"] == "markdown"
    assert p["markdown"]["content"] == "hi"


def test_notify_skips_without_webhook(monkeypatch):
    monkeypatch.delenv("FEISHU_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("WECOM_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("PRICE_WEBHOOK_URL", raising=False)
    called = {}
    with mock.patch.object(notifier, "send_webhook", lambda *a, **k: called.setdefault("x", True)):
        ok = notifier.notify_price_changes(DELTAS, "2026-08-22")
    assert ok is False
    assert "x" not in called


def test_notify_sends_when_configured(monkeypatch):
    monkeypatch.setenv("FEISHU_WEBHOOK_URL", "https://example.com/hook")
    sent: dict = {}

    def fake_send(msg: str, url: str, wh_type: str) -> bool:
        sent["msg"] = msg
        sent["url"] = url
        sent["type"] = wh_type
        return True

    with mock.patch.object(notifier, "send_webhook", fake_send):
        ok = notifier.notify_price_changes(DELTAS, "2026-08-22")
    assert ok is True
    assert sent["url"] == "https://example.com/hook"
    assert sent["type"] == "feishu"
    assert "GPT-5" in sent["msg"]


def test_notify_no_deltas_returns_false(monkeypatch):
    monkeypatch.setenv("FEISHU_WEBHOOK_URL", "https://example.com/hook")
    called = False

    def fake_send(*args, **kwargs) -> bool:
        nonlocal called
        called = True
        return True

    with mock.patch.object(notifier, "send_webhook", fake_send):
        ok = notifier.notify_price_changes([], "2026-08-22")
    assert ok is False
    assert called is False
