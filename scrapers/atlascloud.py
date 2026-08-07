"""AtlasCloud（atlascloud.ai）LLM 定价解析器。

数据源：https://console.atlascloud.ai/api/v1/models
稳定 JSON API，返回全量模型（含 Text / Image / Video / Audio）。
本解析器仅取 `type == "Text"` 的 LLM 模型，价格为「美元 / 百万 tokens」。

价格字段（price.actual）：
  - input_price        : 输入价（USD / 1M tokens）
  - output_price       : 输出价（USD / 1M tokens）
  - cache_price        : 缓存命中（读取）价（USD / 1M tokens）
  - cache_creation_price: 缓存创建价（通常不用，仅记录参考）

AtlasCloud 是 AI 网关（OpenAI 兼容），与 OpenRouter 同类，作为「渠道源」展示，
便于和用户已收录的官网/官方价、其他渠道价横向对比（即「对应完整」）。
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from scrapers.base import BaseScraper


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CACHE = os.path.join(ROOT, "data", "atlascloud_raw.json")


def _to_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return round(f, 6)


def _fmt_ctx(n: Any) -> Optional[str]:
    if n is None:
        return None
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:g}M"
    if n >= 1000:
        return f"{n // 1000}K"
    return str(n)


class AtlascloudScraper(BaseScraper):
    """解析 AtlasCloud Models API（JSON）。"""

    def fetch_url(self, url: str) -> str:
        """拉取 JSON API 并写原始缓存，便于二次核对。"""
        cache_path = self.source.get("cache_path") or DEFAULT_CACHE
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        resp = self.session.get(url, timeout=45)
        resp.raise_for_status()
        text = resp.text
        try:
            payload = {
                "fetched_at": "",
                "url": url,
                "body": json.loads(text),
            }
        except json.JSONDecodeError:
            payload = {"url": url, "body": text}
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return text

    def parse(self, html: str) -> List[Dict[str, Any]]:
        try:
            data = json.loads(html)
        except json.JSONDecodeError:
            return []
        if not isinstance(data, dict):
            return []
        items: List[Dict[str, Any]] = data.get("data") or []
        if not isinstance(items, list):
            return []

        records: List[Dict[str, Any]] = []
        seen: set = set()

        for it in items:
            if (it.get("type") or "").lower() != "text":
                continue
            name = (it.get("displayName") or "").strip()
            if not name:
                continue
            # 去重：同名只保留首条（API 已按 priority 排序）
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)

            price = (it.get("price") or {}).get("actual") or {}
            inp = _to_float(price.get("input_price"))
            out = _to_float(price.get("output_price"))
            cache = _to_float(price.get("cache_price"))
            if inp is None and out is None:
                continue

            records.append(
                self._rec(
                    model_raw=name,
                    input=inp,
                    output=out,
                    cache_hit=cache,
                    context=_fmt_ctx(it.get("contextLength")),
                    condition="AtlasCloud (atlascloud.ai) · USD/1M tokens",
                )
            )
        return records
