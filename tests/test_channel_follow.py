from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.store import build_channel_follow


def _row(canon, src, field=None, **fields):
    base = {"canonical": canon, "source": src, "condition": None, "currency": "CNY"}
    base.update(fields)
    return base


def _write(tmp_path, date, rows):
    hist = tmp_path / "history"
    hist.mkdir(exist_ok=True)
    (hist / f"{date}.json").write_text(
        json.dumps(rows, ensure_ascii=False), encoding="utf-8"
    )


def _write_log(tmp_path, events):
    (tmp_path / "price_change_log.json").write_text(
        json.dumps({"events": events, "total": len(events)}, ensure_ascii=False),
        encoding="utf-8",
    )


def test_channel_follow_three_status(tmp_path):
    """官方调价后，渠道「已跟进/未跟进/幅度背离」三态判定。"""
    # 官方 input: 3.0 → 2.0（-33.33%）
    official_old, official_new = 3.0, 2.0
    # 渠道 A 同步跟进 -33.33%；B 未动；C 只降 16.67%（幅度背离）
    _write(tmp_path, "2026-09-04", [
        _row("DeepSeek V4 Flash", "deepseek", input=official_old, output=9.0),
        _row("DeepSeek V4 Flash", "atlascloud", input=3.0),
        _row("DeepSeek V4 Flash", "tencent", input=3.0),
        _row("DeepSeek V4 Flash", "modelmesh", input=3.0),
    ])
    _write(tmp_path, "2026-09-05", [
        _row("DeepSeek V4 Flash", "deepseek", input=official_new, output=9.0),
        _row("DeepSeek V4 Flash", "atlascloud", input=2.0),
        _row("DeepSeek V4 Flash", "tencent", input=3.0),
        _row("DeepSeek V4 Flash", "modelmesh", input=2.5),
    ])
    # 当前 prices.json 同步为 09-05 状态
    (tmp_path / "prices.json").write_text(
        json.dumps([
            _row("DeepSeek V4 Flash", "deepseek", input=official_new, output=9.0),
            _row("DeepSeek V4 Flash", "atlascloud", input=2.0),
            _row("DeepSeek V4 Flash", "tencent", input=3.0),
            _row("DeepSeek V4 Flash", "modelmesh", input=2.5),
        ], ensure_ascii=False), encoding="utf-8",
    )
    _write_log(tmp_path, [{
        "date": "2026-09-05", "canonical": "DeepSeek V4 Flash",
        "source": "deepseek", "field": "input", "field_cn": "输入",
        "old": official_old, "new": official_new, "pct": -33.33, "currency": "CNY",
    }])

    results = build_channel_follow(str(tmp_path))
    assert len(results) == 1
    r = results[0]
    assert r["canonical"] == "DeepSeek V4 Flash"
    assert r["field"] == "input"
    assert r["field_cn"] == "输入"

    status = {c["source"]: c["status"] for c in r["channels"]}
    assert status["atlascloud"] == "已跟进"
    assert status["tencent"] == "未跟进"
    assert status["modelmesh"] == "幅度背离"


def test_channel_follow_skips_overseas(tmp_path):
    """国外模型（GPT 前缀）无渠道价，不做渠道跟进监督。"""
    _write(tmp_path, "2026-09-04", [
        _row("GPT-5.6 Sol", "openai", input=4.0, currency="USD"),
        _row("GPT-5.6 Sol", "openrouter", input=4.0, currency="USD"),
    ])
    _write(tmp_path, "2026-09-05", [
        _row("GPT-5.6 Sol", "openai", input=5.0, currency="USD"),
        _row("GPT-5.6 Sol", "openrouter", input=5.0, currency="USD"),
    ])
    (tmp_path / "prices.json").write_text(
        json.dumps([
            _row("GPT-5.6 Sol", "openai", input=5.0, currency="USD"),
            _row("GPT-5.6 Sol", "openrouter", input=5.0, currency="USD"),
        ], ensure_ascii=False), encoding="utf-8",
    )
    _write_log(tmp_path, [{
        "date": "2026-09-05", "canonical": "GPT-5.6 Sol", "source": "openai",
        "field": "input", "field_cn": "输入", "old": 4.0, "new": 5.0,
        "pct": 25.0, "currency": "USD",
    }])
    assert build_channel_follow(str(tmp_path)) == []


def test_channel_follow_no_events(tmp_path):
    """无官方调价事件时返回空。"""
    _write(tmp_path, "2026-09-04", [_row("DeepSeek V4 Flash", "deepseek", input=3.0)])
    _write(tmp_path, "2026-09-05", [_row("DeepSeek V4 Flash", "deepseek", input=3.0)])
    (tmp_path / "prices.json").write_text(
        json.dumps([_row("DeepSeek V4 Flash", "deepseek", input=3.0)], ensure_ascii=False),
        encoding="utf-8",
    )
    _write_log(tmp_path, [])
    assert build_channel_follow(str(tmp_path)) == []
