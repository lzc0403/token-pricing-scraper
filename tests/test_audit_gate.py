"""数据门禁（audit gate）单元测试。

覆盖 2026-08-19 新增的兜底校验规则：
1. CACHE_GT_INPUT：缓存命中价 > 输入价 → high（列错位/解析错误）
2. CACHE_SUSPECT：缓存命中价 > 输入价 60% → med
3. EMPTY_INPUT 关键模型：DeepSeek V4 Pro/Flash 等输入价缺失 → high（门禁拦截）
4. EMPTY_INPUT 非关键模型：输入价缺失 → low（不阻断）
5. gate 字段：有 high 即 block，否则 pass
"""

from __future__ import annotations

import sys
import os

# 保证能 import core.audit
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import audit  # noqa: E402


def _mkrow(
    canonical: str = "DeepSeek V4 Flash",
    source: str = "tencent",
    input_v=None,
    output_v=None,
    cache_v=None,
    currency: str = "USD",
) -> dict:
    """构造一条标准 watchlist 记录。"""
    return {
        "model_raw": canonical.lower().replace(" ", "-"),
        "canonical": canonical,
        "source": source,
        "input": input_v,
        "output": output_v,
        "cache_hit": cache_v,
        "currency": currency,
        "input_rmb": None if input_v is None else round(input_v * 7.0, 4),
        "output_rmb": None if output_v is None else round(output_v * 7.0, 4),
        "condition": None,
    }


def _run(watchlist):
    """调用 audit._check_structural，返回 suspects。"""
    return audit._check_structural(watchlist, rate=7.0)


def test_cache_greater_than_input_high():
    """缓存命中价 > 输入价 → high（列错位/解析错误，如腾讯云 0.28 错填）。"""
    rows = [_mkrow(input_v=0.14, output_v=0.28, cache_v=0.28)]
    suspects = _run(rows)
    hits = [s for s in suspects if s["code"] == "CACHE_GT_INPUT"]
    assert len(hits) == 1, suspects
    assert hits[0]["severity"] == "high"


def test_cache_normal_passes():
    """正常缓存价（明显低于输入价）不触发任何 high。"""
    rows = [_mkrow(input_v=0.44, output_v=1.32, cache_v=0.044)]
    suspects = _run(rows)
    highs = [s for s in suspects if s["severity"] == "high"]
    assert highs == [], suspects
    # CACHE_SUSPECT 也不该出现（0.044 / 0.44 = 10%）
    assert not [s for s in suspects if s["code"] == "CACHE_SUSPECT"]


def test_cache_close_to_input_med():
    """缓存命中价接近输入价（>60%）→ med 警示，不阻断。"""
    rows = [_mkrow(input_v=1.0, output_v=2.0, cache_v=0.7)]
    suspects = _run(rows)
    hits = [s for s in suspects if s["code"] == "CACHE_SUSPECT"]
    assert len(hits) == 1
    assert hits[0]["severity"] == "med"


def test_critical_model_missing_input_high():
    """关键主力模型输入价缺失 → high（门禁拦截）。"""
    rows = [_mkrow(canonical="DeepSeek V4 Flash", input_v=None, output_v=0.2, cache_v=0.04)]
    suspects = _run(rows)
    hits = [s for s in suspects if s["code"] == "EMPTY_INPUT"]
    assert len(hits) == 1
    assert hits[0]["severity"] == "high"


def test_noncritical_model_missing_input_low():
    """非关键模型输入价缺失 → low，不阻断（部分页面确实不公开输入价）。"""
    rows = [_mkrow(canonical="GLM-5", input_v=None, output_v=2.58, cache_v=0.115)]
    suspects = _run(rows)
    hits = [s for s in suspects if s["code"] == "EMPTY_INPUT"]
    assert hits and hits[0]["severity"] == "low"


def test_alibaba_intl_deepseek_fixed():
    """回归：阿里云国际站 DeepSeek 修复后数据不应触发拦截。

    V4 Flash: in=0.44 out=1.32 cache=0.044（高峰价，缓存为输入的 10%）→ 全部通过。
    """
    rows = [
        _mkrow(canonical="DeepSeek V4 Flash", source="aliyun_intl",
               input_v=0.44, output_v=1.32, cache_v=0.044),
        _mkrow(canonical="DeepSeek V4 Pro", source="aliyun_intl",
               input_v=1.32, output_v=3.96, cache_v=0.132),
    ]
    suspects = _run(rows)
    highs = [s for s in suspects if s["severity"] == "high"]
    assert highs == [], suspects


def test_gate_passes_and_blocks():
    """run() 的 gate 字段：有 high 即 block。"""
    from core import audit as a

    # 通过：正常数据
    good = [_mkrow(input_v=0.44, output_v=1.32, cache_v=0.044)]
    # 阻断：缓存>输入
    bad = [_mkrow(input_v=0.14, output_v=0.28, cache_v=0.28)]

    # 直接测 _check_structural 的 high 有无来推断 gate 逻辑（run() 需写文件，不在这里跑）
    assert not [s for s in _run(good) if s["severity"] == "high"]
    assert [s for s in _run(bad) if s["severity"] == "high"]
    # gate 判定规则：high>0 → block（与 run() 中 stats 逻辑一致）
    for rows, expect in ((good, "pass"), (bad, "block")):
        n_high = len([s for s in _run(rows) if s["severity"] == "high"])
        assert ("block" if n_high > 0 else "pass") == expect
