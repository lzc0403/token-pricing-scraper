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
    # 标题 + 概览一行
    assert "Token 定价日报 2026-08-22" in msg
    assert "变动 2 模型 / 2 处" in msg
    # 表格行：模型｜来源｜变动（含来源中文名与币种符号）
    assert "GPT-5｜OpenAI官网｜" in msg
    assert "$5→$4" in msg
    assert "DeepSeek V4｜DeepSeek官网｜" in msg
    assert "¥12→¥13" in msg
    # 涨跌幅箭头百分比
    assert "↓25%" in msg or "↑8%" in msg
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
    assert "腾讯云国际·原厂·闲时" in msg
    assert "腾讯云国际·自建" in msg
    # 不再出现内部 source id
    assert "[tencent]" not in msg and "｜tencent" not in msg


def test_build_message_table_layout():
    """表格行按幅度降序排列，行内多字段空格分隔。"""
    deltas = [
        {"canonical": "BigCut", "source": "openai", "field": "input",
         "old": 10.0, "new": 2.0, "currency": "USD"},   # -80%
        {"canonical": "SmallMove", "source": "openai", "field": "output",
         "old": 1.0, "new": 1.1, "currency": "USD"},    # +10%
    ]
    msg = notifier.build_message(deltas, "2026-08-24")
    big = msg.index("BigCut")
    small = msg.index("SmallMove")
    assert big < small  # 幅度大的在前
    # 行格式含表格分隔符
    assert "BigCut｜OpenAI官网｜入 $10→$2 ↓80%" in msg
    assert "SmallMove｜OpenAI官网｜出 $1→$1.1 ↑10%" in msg


def test_build_message_peak_reminder():
    """同字段多个新价 → 峰谷分时提醒。"""
    deltas = [
        {"canonical": "DS V4 Flash", "source": "tencent", "field": "input", "old": 0.14, "new": 0.22, "currency": "USD"},
        {"canonical": "DS V4 Flash", "source": "tencent", "field": "input", "old": 0.14, "new": 0.44, "currency": "USD"},
    ]
    msg = notifier.build_message(deltas, "2026-08-24")
    assert "峰谷分时" in msg


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
    """飞书返回 code:19024 时应判为失败并记录关键词未命中警告。"""
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
    ), mock.patch.object(notifier.logger, "warning") as warn:
        ok = notifier.send_webhook("hi", "https://example.com/hook", "feishu")
    assert ok is False
    assert any("19024" in str(c[0][0]) for c in warn.call_args_list if c and c[0])


def test_build_card_structure():
    """interactive 卡片：涨红头部、三栏表格、脚注含关键词。"""
    card = notifier.build_card(DELTAS, "2026-08-22")
    assert card["msg_type"] == "interactive"
    header = card["card"]["header"]
    assert header["template"] in ("red", "green")
    assert "Token 定价日报" in header["title"]["content"]
    # 脚注含关键词（规避 19024）
    note = [e for e in card["card"]["elements"] if e.get("tag") == "note"]
    assert note and "官网价格" in note[0]["elements"][0]["content"]
    # 表格行包含模型与来源中文名
    md_texts = [
        el.get("content", "")
        for row in card["card"]["elements"] if row.get("tag") == "column_set"
        for col in row.get("columns", [])
        for el in col.get("elements", [])
    ]
    assert any("GPT-5" in t for t in md_texts)
    assert any("OpenAI官网" in t for t in md_texts)


def test_notify_feishu_prefers_card(monkeypatch):
    """飞书渠道应走卡片优先路径，携带纯文本兜底。"""
    monkeypatch.setenv("FEISHU_WEBHOOK_URL", "https://example.com/hook")
    seen: dict = {}
    with mock.patch.object(notifier, "_send_feishu_card",
                           lambda card, msg, url: seen.setdefault("ok", True)):
        ok = notifier.notify_price_changes(DELTAS, "2026-08-22")
    assert ok is True and seen.get("ok")


def test_send_feishu_card_fallback_to_text(monkeypatch):
    """卡片被拒时自动降级为纯文本重发。"""
    responses = iter([
        (False, "bad request"),          # 卡片网络失败
        (True, '{"code":0,"msg":"success"}'),  # text 成功
    ])
    with mock.patch.object(notifier, "_post", lambda url, data: next(responses)), \
         mock.patch.object(notifier.logger, "warning"):
        ok = notifier._send_feishu_card({"msg_type": "interactive"}, "hi", "https://example.com/hook")
    assert ok is True


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

    def fake_card(card, msg, url) -> bool:
        sent["msg"] = msg
        sent["card"] = card
        sent["url"] = url
        return True

    with mock.patch.object(notifier, "_send_feishu_card", fake_card):
        ok = notifier.notify_price_changes(DELTAS, "2026-08-22")
    assert ok is True
    assert sent["url"] == "https://example.com/hook"
    assert sent["card"]["msg_type"] == "interactive"
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
