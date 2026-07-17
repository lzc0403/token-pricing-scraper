"""汇率换算：将各源原始货币价格补充为人民币等价（input_rmb / output_rmb）。"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

DEFAULT_RATE = 7.2


def get_rate() -> float:
    """从环境变量读取 USD->CNY 汇率，默认 7.2。"""
    return float(os.environ.get("USD_CNY_RATE", str(DEFAULT_RATE)))


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
