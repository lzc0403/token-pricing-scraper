"""汇率换算：将各源原始货币价格补充为人民币等价（input_rmb / output_rmb）。"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

DEFAULT_RATE = 7.2


def get_rate() -> float:
    """从环境变量读取 USD->CNY 汇率，默认 7.2。

    GitHub Actions 在 `secrets.USD_CNY_RATE` 未配置时会把 `${{ secrets.X }}`
    求值为**空字符串 `''`**（`os.environ.get` 拿到 `''` 而非 "未设置"）。
    因此当变量为空 / 不存在 / 非数字时一律回退到 `DEFAULT_RATE`，避免
    `float('')` 抛 `ValueError` 导致整个 CI 在 `currency.enrich` 处崩溃。
    """
    raw = os.environ.get("USD_CNY_RATE", "")
    raw = raw.strip() if raw else ""
    if not raw:
        return DEFAULT_RATE
    try:
        return float(raw)
    except (ValueError, TypeError):
        return DEFAULT_RATE


def to_rmb(price: Optional[float], currency: str, rate: float) -> Optional[float]:
    """将单个价格换算为人民币。

    - currency == "USD"：price * rate
    - currency == "CNY"：原值
    - price 为 None：原样返回 None
    """
    if price is None:
        return None
    if currency == "USD":
        return round(price * rate, 6)
    return price


def enrich(records: List[Dict[str, Any]], rate: Optional[float] = None) -> List[Dict[str, Any]]:
    """就地（并返回）为每条记录补充 input_rmb / output_rmb。"""
    if rate is None:
        rate = get_rate()
    for rec in records:
        currency = rec.get("currency", "CNY")
        rec["input_rmb"] = to_rmb(rec.get("input"), currency, rate)
        rec["output_rmb"] = to_rmb(rec.get("output"), currency, rate)
    return records
