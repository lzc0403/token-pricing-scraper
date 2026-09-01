"""xAI Grok 官网（docs.x.ai，USD）模型定价解析器。

数据源：https://docs.x.ai/docs/models

页面为 Next.js SSR，模型数据内嵌在脚本变量中：

    globalThis.__XAI_PUBLIC_MODELS__ = {"clusterConfigs":[{"languageModels":[...]}]}

每个语言模型对象的价格字段（字符串数字，单位换算：value / 10_000 = USD / 百万 tokens）：

    promptTextTokenPrice               标准输入价
    promptTextTokenPriceLongContext    长上下文输入价（prompt ≥ longContextThreshold 时全量按此计）
    cachedPromptTokenPrice             缓存命中价
    cachedPromptTokenPriceLongContext  长上下文缓存命中价
    completionTextTokenPrice           标准输出价
    completionTokenPriceLongContext    长上下文输出价

grok-4.6 示例：input "20000" → $2.0/M；cached "5000" → $0.5/M；output "60000" → $6.0/M。

收录策略：
- 只收站内在册模型（Grok 4.6）；长上下文档用 condition 区分
  （「长上下文 · ≥200K」），与 OpenAI 官网分档口径一致。
- 官网无缓存写入价字段 → cache_write 恒为 None。
- canonical 由 openrouter.yml 白名单同 id 映射（source=grok，白名单 id=x-ai/grok-4.6）。
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from scrapers.base import BaseScraper

_JSON_RE = re.compile(r"globalThis\.__XAI_PUBLIC_MODELS__\s*=\s*(\{.*?\})\s*;?\s*</script>", re.S)

# value（字符串）→ USD/百万 tokens 的除数
_SCALE = 10_000

# 模型名 → OpenRouter id（白名单通道用）。仅收录站内在册模型。
_MODEL_OR_ID: Dict[str, str] = {
    "grok-4.6": "x-ai/grok-4.6",
}

# 长上下文档 condition 标注（与官网 longContextThreshold 一致）
_LONG_COND = "长上下文 · ≥200K"
_STD_COND = "default"


def _usd(v: Any) -> Optional[float]:
    """字符串价格 → USD/百万 tokens。"""
    if v is None:
        return None
    try:
        return float(v) / _SCALE
    except (TypeError, ValueError):
        return None


class GrokScraper(BaseScraper):
    """解析 docs.x.ai 官方模型页（USD）。"""

    def parse(self, html: str) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        seen: set = set()
        m = _JSON_RE.search(html)
        if not m:
            return records
        try:
            data = json.loads(m.group(1))
        except (json.JSONDecodeError, TypeError):
            return records

        for cluster in data.get("clusterConfigs") or []:
            for model in cluster.get("languageModels") or []:
                name = str(model.get("name") or "").strip()
                or_id = _MODEL_OR_ID.get(name)
                if or_id is None:
                    continue
                threshold = str(model.get("longContextThreshold") or "").strip()

                std = {
                    "input": _usd(model.get("promptTextTokenPrice")),
                    "output": _usd(model.get("completionTextTokenPrice")),
                    "cache_hit": _usd(model.get("cachedPromptTokenPrice")),
                }
                longp = {
                    "input": _usd(model.get("promptTextTokenPriceLongContext")),
                    "output": _usd(model.get("completionTokenPriceLongContext")),
                    "cache_hit": _usd(model.get("cachedPromptTokenPriceLongContext")),
                }
                ctx = model.get("maxPromptLength")
                ctx_label = f"{int(ctx) // 1000}K" if isinstance(ctx, (int, float)) and ctx else None

                if any(v is not None for v in std.values()):
                    if ("std", name) in seen:
                        continue
                    seen.add(("std", name))
                    rec = self._rec(
                        model_raw=name,
                        input=std["input"],
                        output=std["output"],
                        cache_hit=std["cache_hit"],
                        context=ctx_label,
                        condition=_STD_COND,
                    )
                    rec["openrouter_id"] = or_id
                    records.append(rec)
                # 长上下文档：与标准档不同才单列（避免重复行）
                has_long = any(
                    v is not None for v in longp.values()
                )
                differs = has_long and (
                    longp["input"] != std["input"] or longp["output"] != std["output"]
                )
                if differs and threshold:
                    if ("long", name) in seen:
                        continue
                    seen.add(("long", name))
                    rec_long = self._rec(
                        model_raw=name,
                        input=longp["input"],
                        output=longp["output"],
                        cache_hit=longp["cache_hit"],
                        context=ctx_label,
                        condition=_LONG_COND,
                    )
                    rec_long["openrouter_id"] = or_id
                    records.append(rec_long)
        return records
