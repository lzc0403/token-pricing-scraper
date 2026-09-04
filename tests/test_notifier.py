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


def test_consolidate_tiers_synced():
    """闲时/高峰两档同比例变动 → 合并为一条刊例调整，不重复计数。"""
    deltas = [
        {"canonical": "DS V4 Flash", "source": "tencent", "field": "input",
         "old": 1.0, "new": 2.0, "currency": "USD", "condition": "空闲时段 | 原厂直供"},
        {"canonical": "DS V4 Flash", "source": "tencent", "field": "output",
         "old": 2.0, "new": 4.0, "currency": "USD", "condition": "空闲时段 | 原厂直供"},
        {"canonical": "DS V4 Flash", "source": "tencent", "field": "input",
         "old": 2.0, "new": 4.0, "currency": "USD", "condition": "高峰时段 | 原厂直供"},
        {"canonical": "DS V4 Flash", "source": "tencent", "field": "output",
         "old": 4.0, "new": 8.0, "currency": "USD", "condition": "高峰时段 | 原厂直供"},
    ]
    out, structural = notifier.consolidate_tiers(deltas)
    assert structural == []
    # 只保留闲时档两条（入/出），高峰被归并
    assert len(out) == 2
    assert all(d["tier_sync"] for d in out)
    msg = notifier.build_message(deltas, "2026-08-25")
    assert "刊例同调" in msg
    # 概览计数不重复：2 处而非 4 处
    assert "2 处" in msg


def test_consolidate_tiers_structural():
    """仅一档变动 / 两档幅度背离 → 判定为峰谷结构调整并提醒。"""
    deltas = [
        {"canonical": "DS V4 Flash", "source": "tencent", "field": "input",
         "old": 1.0, "new": 1.0, "currency": "USD", "condition": "空闲时段 | 原厂直供"},
        {"canonical": "DS V4 Flash", "source": "tencent", "field": "output",
         "old": 2.0, "new": 3.0, "currency": "USD", "condition": "高峰时段 | 原厂直供"},
    ]
    out, structural = notifier.consolidate_tiers(deltas)
    assert structural == ["DS V4 Flash"]
    assert len(out) == 2
    msg = notifier.build_message(deltas, "2026-08-25")
    assert "峰谷结构调整" in msg


# ---------------------------------------------------------------------------
# 官网基准行情判别
# ---------------------------------------------------------------------------

def test_official_source_mirror():
    """notifier 的官网源判定必须与 site_data 展示口径镜像一致，防止漂移。"""
    from core.site_data import OFFICIAL_SOURCE, _is_official_any_currency

    # 逐条对照 site_data 的判定：site_data 认为是官方的，notifier 也必须是
    for canon, src in OFFICIAL_SOURCE.items():
        assert notifier.is_official_source(canon, src), (canon, src)
    # 多币种厂商双站
    for canon, src in [
        ("DeepSeek V4 Flash", "deepseek"), ("DeepSeek V4 Flash", "deepseek_us"),
        ("GLM-5.2", "bigmodel"), ("GLM-5.2", "zai"),
        ("Kimi K3", "kimi"), ("Kimi K3", "kimi_ai"),
    ]:
        assert notifier.is_official_source(canon, src), (canon, src)
    # 渠道源不能误判
    for canon, src in [("DeepSeek V4 Flash", "tencent"), ("GLM-5.2", "openrouter")]:
        assert not notifier.is_official_source(canon, src), (canon, src)
    # site_data 官方行 ↔ notifier 判定一致（抽样真实结构）
    row = {"source": "deepseek"}
    assert _is_official_any_currency("DeepSeek V4 Pro", row)


def test_market_alert_official_lead():
    """官网调价 + 渠道未跟进 → 市场行情警报。"""
    deltas = [
        # DeepSeek 官网 input 从 0.14 上浮到 0.22
        {"canonical": "DeepSeek V4 Flash", "source": "deepseek", "field": "input",
         "old": 1.0, "new": 1.57, "currency": "CNY"},
        # 腾讯云渠道没动（不在 deltas 中）
    ]
    msg = notifier.build_message(deltas, "2026-08-25")
    assert "市场行情" in msg
    assert "渠道未跟进" in msg


def test_market_quiet_when_channel_follows():
    """官网调价 + 渠道同幅跟进 → 正常播报，不发市场行情警报，行标「跟进官网」。"""
    deltas = [
        {"canonical": "DeepSeek V4 Flash", "source": "deepseek", "field": "input",
         "old": 1.0, "new": 1.57, "currency": "CNY"},   # +57%
        {"canonical": "DeepSeek V4 Flash", "source": "tencent_cn", "field": "input",
         "old": 1.0, "new": 1.6, "currency": "CNY"},    # +60%，±10pp 内视为跟进
    ]
    msg = notifier.build_message(deltas, "2026-08-25")
    assert "市场行情" not in msg
    assert "跟进官网" in msg


def test_market_alert_cross_currency():
    """跨币种可比：CNY 官网涨、USD 渠道同幅跟 → 不报警；背离则报。"""
    # 同幅（+50% vs +52%）：不报
    synced = [
        {"canonical": "DeepSeek V4 Flash", "source": "deepseek", "field": "input",
         "old": 2.0, "new": 3.0, "currency": "CNY"},     # +50%
        {"canonical": "DeepSeek V4 Flash", "source": "tencent", "field": "input",
         "old": 0.28, "new": 0.426, "currency": "USD"},  # +52%
    ]
    assert "市场行情" not in notifier.build_message(synced, "2026-08-25")
    # 背离（+50% vs -30%）：报警
    diverged = [
        {"canonical": "DeepSeek V4 Flash", "source": "deepseek", "field": "input",
         "old": 2.0, "new": 3.0, "currency": "CNY"},
        {"canonical": "DeepSeek V4 Flash", "source": "tencent", "field": "input",
         "old": 1.0, "new": 0.7, "currency": "USD"},
    ]
    assert "市场行情" in notifier.build_message(diverged, "2026-08-25")


def test_channel_own_change_no_alert():
    """渠道自己乱调价（无官网变动）→ 不触发市场行情警报。"""
    deltas = [
        {"canonical": "DeepSeek V4 Flash", "source": "tencent", "field": "input",
         "old": 0.14, "new": 0.44, "currency": "USD"},
    ]
    msg = notifier.build_message(deltas, "2026-08-25")
    assert "市场行情" not in msg


# ---------------------------------------------------------------------------
# 官方调价预警（无条件列出，供人工跟进）
# ---------------------------------------------------------------------------

_OFFICIAL_DELTAS = [
    # OpenAI 官方：输入 +25%（OpenRouter 同步）、缓存写入 +20%（无渠道同步）
    {"canonical": "GPT-5.6 Sol", "source": "openai", "field": "input",
     "old": 4.0, "new": 5.0, "currency": "USD"},
    {"canonical": "GPT-5.6 Sol", "source": "openai", "field": "cache_write",
     "old": 5.0, "new": 6.0, "currency": "USD"},
    {"canonical": "GPT-5.6 Sol", "source": "openrouter", "field": "input",
     "old": 4.0, "new": 5.0, "currency": "USD"},
    # 渠道独立调价（非官方，不应进预警区）
    {"canonical": "GLM-5.2", "source": "tencent_cn", "field": "input",
     "old": 8.0, "new": 7.0, "currency": "CNY",
     "condition": "原厂直供"},
]


def test_official_alerts_only_official_sources():
    """预警区只含官方源调价，渠道自有变动不进。"""
    alerts = notifier._official_price_alerts(_OFFICIAL_DELTAS)
    assert [a["canonical"] for a in alerts] == ["GPT-5.6 Sol"]
    assert alerts[0]["source_label"] == "OpenAI官网"


def test_official_alerts_sorted_by_magnitude():
    """多个官方调价按最大幅度降序。"""
    deltas = _OFFICIAL_DELTAS + [
        {"canonical": "Claude Opus 5", "source": "anthropic", "field": "input",
         "old": 5.0, "new": 4.0, "currency": "USD"},  # -20%
        {"canonical": "DeepSeek V4 Pro", "source": "deepseek", "field": "output",
         "old": 24.0, "new": 30.0, "currency": "CNY"},  # +25%
    ]
    alerts = notifier._official_price_alerts(deltas)
    assert [a["canonical"] for a in alerts][0] in ("GPT-5.6 Sol", "DeepSeek V4 Pro")
    assert alerts[0]["max_pct"] >= alerts[-1]["max_pct"]


def test_official_alert_follow_status_is_field_level():
    """跟进状态按字段判定：输入已同步、缓存写入未同步。"""
    alerts = notifier._official_price_alerts(_OFFICIAL_DELTAS)
    items = {it["field"]: it for it in alerts[0]["items"]}
    assert items["input"]["followed"] is True
    assert items["input"]["followers"] == ["OpenRouter"]
    assert items["cache_write"]["followed"] is False
    assert items["cache_write"]["followers"] == []


def test_official_alert_block_in_message():
    """纯文本日报含置顶官方调价区块。"""
    msg = notifier.build_message(_OFFICIAL_DELTAS, "2026-09-02")
    assert "官方调价（1 个模型，需跟进）" in msg
    assert "GPT-5.6 Sol · OpenAI官网" in msg
    assert "缓存写入 $5→$6 ↑20%" in msg
    # 区块在总表之前（置顶）
    assert msg.index("官方调价") < msg.index("模型｜来源｜变动")


def test_official_alert_block_in_card():
    """飞书卡片在 KPI 之后、总表之前插入预警区。"""
    card = notifier.build_card(_OFFICIAL_DELTAS, "2026-09-02")["card"]
    contents = [
        e.get("text", {}).get("content", "")
        for e in card.get("elements", [])
        if isinstance(e, dict) and e.get("tag") == "div"
    ]
    assert any("官方调价（1 个模型，需跟进）" in c for c in contents)
    assert any("缓存写入 $5→$6 ↑20%｜渠道同步：未见" in c for c in contents)


def test_no_official_change_no_alert_block():
    """无官方调价时不应出现预警区，且总表表头照常输出。"""
    deltas = [
        {"canonical": "GLM-5.2", "source": "tencent_cn", "field": "input",
         "old": 8.0, "new": 7.0, "currency": "CNY", "condition": "原厂直供"},
    ]
    msg = notifier.build_message(deltas, "2026-09-02")
    assert "官方调价" not in msg
    assert "模型｜来源｜变动" in msg
    card = notifier.build_card(deltas, "2026-09-02")["card"]
    assert all("官方调价" not in json.dumps(e, ensure_ascii=False)
               for e in card.get("elements", []))
