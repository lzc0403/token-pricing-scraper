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
    # 结构区段
    assert "【今日概览】" in msg
    assert "变动模型" in msg
    assert "2026-08-22" in msg
    # 模型分组展示（含来源中文名与币种符号）
    assert "GPT-5｜OpenAI官网" in msg
    assert "$5→$4" in msg
    assert "DeepSeek V4｜DeepSeek官网" in msg
    assert "¥12→¥13" in msg
    # 涨跌幅符号
    assert "%" in msg
    # 站点链接
    assert "token-pricing-scraper" in msg
    # 默认追加关键词「官网价格」，规避飞书 code:19024
    assert "官网价格" in msg


def test_build_message_condition_display():
    """同来源不同计费口径应分行展示且带可读口径标签。"""
    deltas = [
        {"canonical": "DS V4 Flash", "source": "tencent", "field": "input",
         "old": 0.14, "new": 0.22, "currency": "USD", "condition": "空闲时段 | 原厂直供"},
        {"canonical": "DS V4 Flash", "source": "tencent", "field": "input",
         "old": 0.14, "new": 0.44, "currency": "USD", "condition": "腾讯云自建"},
    ]
    msg = notifier.build_message(deltas, "2026-08-24")
    assert "腾讯云国际·原厂直供·闲时价" in msg
    assert "腾讯云自建" in msg
    # 不再出现内部 source id
    assert "[tencent]" not in msg and "｜tencent" not in msg


def test_build_message_major_minor_split():
    """大幅变动进重点区，小幅变动折叠。"""
    deltas = [
        {"canonical": "BigCut", "source": "openai", "field": "input", "old": 10.0, "new": 2.0, "currency": "USD"},   # -80%
        {"canonical": "SmallMove", "source": "openai", "field": "output", "old": 1.0, "new": 1.1, "currency": "USD"},  # +10%
    ]
    msg = notifier.build_message(deltas, "2026-08-24")
    assert "重点变动" in msg
    assert "■ BigCut｜OpenAI官网" in msg
    assert "· SmallMove｜OpenAI官网：" in msg


def test_build_message_peak_reminder():
    """同字段多个新价 → 峰谷分时提醒。"""
    deltas = [
        {"canonical": "DS V4 Flash", "source": "tencent", "field": "input", "old": 0.14, "new": 0.22, "currency": "USD"},
        {"canonical": "DS V4 Flash", "source": "tencent", "field": "input", "old": 0.14, "new": 0.44, "currency": "USD"},
    ]
    msg = notifier.build_message(deltas, "2026-08-24")
    assert "峰谷分时计费" in msg


def test_build_message_all_down_reminder():
    """全线降价 ≥3 条 → 采购窗口提醒。"""
    deltas = [
        {"canonical": "A", "source": "s", "field": "input", "old": 2.0, "new": 1.0, "currency": "CNY"},
        {"canonical": "B", "source": "s", "field": "input", "old": 4.0, "new": 2.0, "currency": "CNY"},
        {"canonical": "C", "source": "s", "field": "output", "old": 8.0, "new": 4.0, "currency": "CNY"},
    ]
    msg = notifier.build_message(deltas, "2026-08-24")
    assert "全线降价" in msg and "放量" in msg


def test_build_message_custom_keyword():
    msg = notifier.build_message(DELTAS, "2026-08-22", keyword="Token 播报")
    assert "[关键词：Token 播报]" in msg


def test_build_message_keyword_env(monkeypatch):
    monkeypatch.setenv("PRICE_KEYWORD", "价格变动")
    msg = notifier.build_message(DELTAS, "2026-08-22")
    assert "[关键词：价格变动]" in msg


def test_payload_feishu():
    p = notifier._payload("hi", "feishu")
    assert p["msg_type"] == "text"
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
