from __future__ import annotations

import json
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
    # 默认追加关键词「定价」，规避飞书 code:19024
    assert "定价" in msg


def test_build_message_custom_keyword():
    msg = notifier.build_message(DELTAS, "2026-08-22", keyword="Token 播报")
    assert "[关键词：Token 播报]" in msg


def test_build_message_keyword_env(monkeypatch):
    monkeypatch.setenv("PRICE_KEYWORD", "价格变动")
    msg = notifier.build_message(DELTAS, "2026-08-22")
    assert "[关键词：价格变动]" in msg


def test_payload_feishu():
    p = notifier._payload("hi", "feishu")
    assert p["msg_type"] == "markdown"
    assert p["content"]["text"] == "hi"


def test_payload_wecom():
    p = notifier._payload("hi", "wecom")
    assert p["msgtype"] == "markdown"
    assert p["markdown"]["content"] == "hi"


def test_send_webhook_logs_19024(monkeypatch):
    """飞书返回 code:19024 时应记录关键词未命中警告。"""
    body = json.dumps({"code": 19024, "msg": "Key Words Not Found"})

    class FakeResp:
        def __init__(self, b):
            self._b = b

        def read(self):
            return self._b.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    with mock.patch.object(
        notifier.urllib.request, "urlopen",
        lambda *a, **k: FakeResp(body),
    ), mock.patch.object(notifier.logger, "warning") as warn, mock.patch.object(
        notifier.logger, "info"
    ) as info:
        ok = notifier.send_webhook("hi", "https://example.com/hook", "feishu")
    assert ok is True  # 网络层未被判定为失败，仅记录警告
    assert any("19024" in str(c[0][0]) for c in warn.call_args_list if c and c[0])


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
