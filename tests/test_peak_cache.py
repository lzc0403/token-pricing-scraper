"""峰谷缓存渲染与周末判档单元测试（离线，不依赖真实 data/）。

覆盖 2026-08-25 改动：
1. DeepSeek 官网缓存命中峰谷双档 → 缓存列渲染「闲 X / 高 Y」
2. PEAK_SCHEDULES 周末（周六/周日）全天闲时定义注入前端
3. 渲染函数对峰谷缓存行的回退逻辑
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import site_tpl as tpl  # noqa: E402
from core.site_data import PEAK_SCHEDULES  # noqa: E402


def _row(**overrides):
    r = {
        "canonical": "DeepSeek V4 Flash",
        "model": "DeepSeek V4 Flash",
        "source": "deepseek",
        "source_label": "DeepSeek",
        "currency": "CNY",
        "input": 3.0,
        "output": 9.0,
        "cache_hit": 0.1,
        "context": "1M",
        "condition": "峰谷计费",
        "peak_input_low": 1.5,
        "peak_input_high": 3.0,
        "peak_output_low": 4.5,
        "peak_output_high": 9.0,
        "peak_cache_low": 0.05,
        "peak_cache_high": 0.1,
        "input_rmb": 3.0,
        "output_rmb": 9.0,
    }
    r.update(overrides)
    return r


def test_cache_column_renders_peak_duo():
    """峰谷行缓存列应渲染「闲 0.05 / 高 0.1」，而非单值。"""
    html = tpl._table_row(_row(), kind="official", price_mode="cny")
    assert "闲 0.05" in html
    assert "高 0.1" in html
    assert "c-cache" in html


def test_cache_column_plain_when_no_peak():
    """无峰谷缓存字段时缓存列回退单值（input/output 峰谷不受影响）。"""
    import re

    r = _row(peak_cache_low=None, peak_cache_high=None, cache_hit=2.0)
    html = tpl._table_row(r, kind="official", price_mode="cny")
    # 缓存列（c-cache 单元格）为单值 2，不带「闲/高」双档
    m = re.search(r'<td class="num c-cache">(.*?)</td>', html)
    assert m, "c-cache 单元格缺失"
    cache_cell = m.group(1)
    assert "2" in cache_cell
    assert "闲" not in cache_cell
    assert "高" not in cache_cell
    # input/output 列峰谷不受影响（peak_input_* 仍在）
    assert "闲 1.5" in html


def test_peak_schedules_deepseek_weekend_off():
    """DeepSeek 官方：周六/周日全天空闲（weekend_off=True）。"""
    sched = PEAK_SCHEDULES["deepseek_official"]
    assert sched.get("weekend_off") is True
    # 高峰窗口保持 09-12 / 14-18
    assert sched["peak"] == [[9, 12], [14, 18]]


def test_peak_schedules_aliyun_intl_no_weekend():
    """阿里云国际站：无周末全天规则，按小时窗口（闲时 22-08）判档。"""
    sched = PEAK_SCHEDULES["aliyun_intl"]
    assert sched.get("weekend_off") is False
    assert sched["off"] == [[22, 24], [0, 8]]


def test_kimi_ai_label_mapping():
    """kimi_ai 展示名与官方双币种识别。"""
    from core.site_data import SOURCE_LABELS, _is_official_any_currency

    assert SOURCE_LABELS["kimi_ai"] == "Kimi国际站"
    row = {"source": "kimi_ai", "currency": "USD"}
    assert _is_official_any_currency("Kimi K3", row) is True
    assert _is_official_any_currency("Kimi K2.6", row) is True
