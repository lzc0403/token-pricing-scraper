from __future__ import annotations

import json
import os
from typing import Any, Dict, List

import pytest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.site_data import _build_model_details, _normalize_row
from core.store import build_official_changes


# ============================================================
# build_official_changes：官方源调价 + 新品检测
# ============================================================

def make_row(canon, src, cond, **fields):
    return {"canonical": canon, "source": src, "condition": cond, **fields}


def test_build_official_changes_picks_up_official_change(tmp_path):
    """官方源价格变化应被检出并附带 field_cn、pct。"""
    (tmp_path / "prices.json").write_text(
        json.dumps([
            make_row("Gemini 3.8 Flash", "gemini", None,
                     input=0.75, output=3.75, cache_hit=0.075,
                     cache_storage=0.5, currency="USD"),
        ], ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "history").mkdir()
    (tmp_path / "history" / "2026-09-04.json").write_text(
        json.dumps([
            make_row("Gemini 3.8 Flash", "gemini", None,
                     input=1.0, output=3.75, cache_hit=0.075,
                     cache_storage=0.5, currency="USD"),
        ], ensure_ascii=False),
        encoding="utf-8",
    )
    oc = build_official_changes(str(tmp_path), lookback_days=7, today_iso="2026-09-05")
    assert oc["lookback_days"] == 7
    assert len(oc["changes"]) == 1
    ch = oc["changes"][0]
    assert ch["canonical"] == "Gemini 3.8 Flash"
    assert ch["field"] == "input"
    assert ch["old"] == 1.0 and ch["new"] == 0.75
    assert ch["pct"] == -25.0
    assert ch["field_cn"] == "输入"
    assert ch["source_label"] == "Gemini官网"


def test_build_official_changes_ignores_channels(tmp_path):
    """渠道源行（OpenRouter 等）的价格变化不应进入官方调价清单。"""
    (tmp_path / "prices.json").write_text(
        json.dumps([
            make_row("GPT-5.6 Sol", "openrouter", None,
                     input=99, output=99, currency="USD"),
            make_row("GPT-5.6 Sol", "openai", None,
                     input=5.0, output=20.0, currency="USD"),
        ], ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "history").mkdir()
    (tmp_path / "history" / "2026-09-04.json").write_text(
        json.dumps([
            make_row("GPT-5.6 Sol", "openrouter", None,
                     input=88, output=88, currency="USD"),
            make_row("GPT-5.6 Sol", "openai", None,
                     input=5.0, output=20.0, currency="USD"),
        ], ensure_ascii=False),
        encoding="utf-8",
    )
    oc = build_official_changes(str(tmp_path), 7, "2026-09-05")
    assert oc["changes"] == []  # openrouter 渠道源被过滤；openai 未变


def test_build_official_changes_detects_new_official_model(tmp_path):
    """新增官方源行（prev 快照中不存在）记入 new_models + known 持久化。"""
    (tmp_path / "prices.json").write_text(
        json.dumps([
            make_row("Claude Opus 5", "anthropic", None,
                     input=5.0, output=25.0, cache_write=6.25,
                     cache_hit=0.5, currency="USD"),
        ], ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "history").mkdir()
    (tmp_path / "history" / "2026-09-04.json").write_text(
        json.dumps([], ensure_ascii=False), encoding="utf-8"
    )
    oc = build_official_changes(str(tmp_path), 7, "2026-09-05")
    assert any(n["canonical"] == "Claude Opus 5" for n in oc["new_models"])
    # known_official.json 持久化
    known = json.loads((tmp_path / "known_official.json").read_text(encoding="utf-8"))
    assert "Claude Opus 5" in known and "anthropic" in known["Claude Opus 5"]


# ============================================================
# _build_model_details：4 维价格聚合 + Anthropic 双档 + Gemini 存储
# ============================================================

def _row(canon, source, **fields):
    fields.setdefault("model_raw", canon)
    fields.setdefault("currency", "USD")
    fields.setdefault("condition", None)
    return {"canonical": canon, "source": source, **fields}


def test_build_model_details_aggregates_rows():
    """同 canonical 多 source 行被聚合；官方源优先排在最前。"""
    norm = [
        _normalize_row(_row("GPT-5.6 Sol", "openai", input=4.0, output=20.0,
                            cache_write=5.0, cache_hit=0.4),
                       "GPT-5.6 Sol", None, None),
        _normalize_row(_row("GPT-5.6 Sol", "openrouter", input=4.0, output=20.0,
                            cache_hit=0.4),
                       "GPT-5.6 Sol", None, None),
        _normalize_row(_row("GPT-5.6 Sol", "openai", input=10.0, output=45.0,
                            cache_hit=1.0, condition="长文本 · >272K"),
                       "GPT-5.6 Sol", None, None),
    ]
    details = _build_model_details(norm)
    rows = details["GPT-5.6 Sol"]["rows"]
    assert len(rows) == 3
    # 官方源 openai 优先排在最前
    assert "openai" in rows[0]["source"]
    assert any(r["tier"] == "标准档" for r in rows)
    assert any(">272K" in (r["tier"] or "") for r in rows)


def test_build_model_details_anthropic_dual_cache_write():
    """Anthropic 缓存创建分 5m（=cache_write）和 1h（=2×input）两档派生。"""
    norm = [
        _normalize_row(_row("Claude Opus 5", "anthropic", input=5.0, output=25.0,
                            cache_write=6.25, cache_hit=0.5),
                       "Claude Opus 5", None, None),
    ]
    r = _build_model_details(norm)["Claude Opus 5"]["rows"][0]
    assert r["cache_write_5m"] == 6.25
    assert r["cache_write_1h"] == 10.0  # 2 × input
    assert r["tier"] == "标准档"


def test_build_model_details_gemini_storage():
    """Gemini 缓存存储价（$/1M tokens/小时）独立落 cache_storage 字段。"""
    norm = [
        _normalize_row(_row("Gemini 3.8 Flash", "gemini", input=0.75, output=3.75,
                            cache_hit=0.075, cache_storage=0.5),
                       "Gemini 3.8 Flash", None, None),
    ]
    r = _build_model_details(norm)["Gemini 3.8 Flash"]["rows"][0]
    assert r["cache_storage"] == 0.5
    # Google 没有按 token cache_write，确认如实空
    assert r["cache_write"] is None


# ============================================================
# 官方调价事件日志（append-only / 逐日 diff 回填）
# ============================================================

def test_backfill_official_change_log_detects_change(tmp_path):
    """相邻快照的官方源价格变化应逐日回填，且重复运行幂等。"""
    hist = tmp_path / "history"
    hist.mkdir()
    make = lambda inp: make_row("Gemini 3.8 Flash", "gemini", None,
                                input=inp, output=3.75, cache_hit=0.075,
                                cache_storage=0.5, currency="USD")
    (hist / "2026-09-04.json").write_text(
        json.dumps([make(1.0)], ensure_ascii=False), encoding="utf-8")
    (hist / "2026-09-05.json").write_text(
        json.dumps([make(0.75)], ensure_ascii=False), encoding="utf-8")

    from core.store import backfill_official_change_log
    pl = backfill_official_change_log(str(tmp_path))
    assert pl["total"] == 1
    e = pl["events"][0]
    assert e["date"] == "2026-09-05"
    assert e["canonical"] == "Gemini 3.8 Flash"
    assert e["field_cn"] == "输入"
    assert e["old"] == 1.0 and e["new"] == 0.75 and e["pct"] == -25.0
    # 幂等：再跑不再重复
    pl2 = backfill_official_change_log(str(tmp_path))
    assert pl2["total"] == 1


def test_backfill_official_change_log_skips_channels_and_noop(tmp_path):
    """渠道源变化不进事件日志；官方价未变时无事件。"""
    hist = tmp_path / "history"
    hist.mkdir()
    (hist / "2026-09-04.json").write_text(
        json.dumps([
            make_row("GPT-5.6 Sol", "openrouter", None, input=88, output=88, currency="USD"),
            make_row("GPT-5.6 Sol", "openai", None, input=4.0, output=20.0, currency="USD"),
        ], ensure_ascii=False), encoding="utf-8")
    (hist / "2026-09-05.json").write_text(
        json.dumps([
            make_row("GPT-5.6 Sol", "openrouter", None, input=99, output=99, currency="USD"),
            make_row("GPT-5.6 Sol", "openai", None, input=4.0, output=20.0, currency="USD"),
        ], ensure_ascii=False), encoding="utf-8")

    from core.store import backfill_official_change_log
    pl = backfill_official_change_log(str(tmp_path))
    assert pl["total"] == 0  # openrouter 渠道源被过滤；openai 官方价未变
