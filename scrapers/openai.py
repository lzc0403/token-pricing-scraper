"""OpenAI 官网（developers.openai.com，USD）模型定价解析器。

数据源：https://developers.openai.com/api/docs/pricing

页面为 Astro 预渲染，价格数据以 JSON 内嵌在
`TextTokenPricingTables` 组件的 `props` 属性中（HTML 实体 `&quot;` 转义）。

页面含多个 tier 档位（standard / batch / flex / fast），默认展示 standard。
每档 rows 形如：

    [1, [[1, [[0, "gpt-5.6-sol"], [0,5],[0,0.5],[0,6.25],[0,30]], ...]]]

列：模型名 | 输入 | 缓存输入 | 缓存写入 | 输出（美元/百万 tokens）。

旗舰区（gpt-5.6-sol/terra/luna）另带长文本档（>272K tokens）：
- 短文本 ≤272K：sol 5/30、terra 2/12、luna 0.2/1.2
- 长文本 >272K：sol 10/45、terra 4/18、luna 0.4/1.8

收录范围：gpt-5.5 及以上（gpt-5.5 / gpt-5.5-pro / gpt-5.6-sol / gpt-5.6-terra / gpt-5.6-luna），
长短文本分档用 condition 区分（"短文本 · ≤272K" / "长文本 · >272K"）。
"""

from __future__ import annotations

import html as _html
import json
import re
from typing import Any, Dict, List, Optional

from scrapers.base import BaseScraper

# 旗舰区长文本价格（页面渲染区短+长 8 列确认）
_LONG_CONTEXT_PRICES: Dict[str, Dict[str, float]] = {
    "gpt-5.6-sol": {"input": 10.0, "output": 45.0, "cache_hit": 1.0},
    "gpt-5.6-terra": {"input": 4.0, "output": 18.0, "cache_hit": 0.4},
    "gpt-5.6-luna": {"input": 0.4, "output": 1.8, "cache_hit": 0.04},
}

# 只收录 GPT-5.5 及以上（name 可能带 "(<272K context length)" 后缀，剥离后匹配）
_MIN_CANON = {
    "gpt-5.5": "GPT-5.5",
    "gpt-5.5-pro": "GPT-5.5 Pro",
    "gpt-5.6-sol": "GPT-5.6 Sol",
    "gpt-5.6-terra": "GPT-5.6 Terra",
    "gpt-5.6-luna": "GPT-5.6 Luna",
}

# model_raw（清后缀小写）→ OpenRouter 精确 id（main.py 复用白名单 canonical 映射）。
# 注意 gpt-5.6-sol 在 OpenRouter 的 id 是 openai/gpt-5.6（官网叫 sol，OpenRouter 无 -sol 后缀）。
_OR_ID = {
    "gpt-5.5": "openai/gpt-5.5",
    "gpt-5.5-pro": "openai/gpt-5.5-pro",
    "gpt-5.6-sol": "openai/gpt-5.6",
    "gpt-5.6-terra": "openai/gpt-5.6-terra",
    "gpt-5.6-luna": "openai/gpt-5.6-luna",
}

_CTX_SUFFIX_RE = re.compile(r"\s*\(<[^)]*context[^)]*\)\s*$", re.I)

_ROWS_JSON_RE = re.compile(
    r'TextTokenPricingTables" renderer-url="[^"]+" props="(.+?)" ssr client=',
    re.S,
)


class OpenaiScraper(BaseScraper):
    """解析 developers.openai.com 官方定价页（USD）。"""

    def parse(self, html: str) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []

        # 1) 提取标准档（standard）rows
        rows_json = self._extract_tier_rows(html, "standard")
        if not rows_json:
            return records

        for item in rows_json:
            model_raw, prices = item
            clean_raw = _CTX_SUFFIX_RE.sub("", model_raw).strip().lower()
            if clean_raw not in _MIN_CANON:
                continue
            canon = _MIN_CANON[clean_raw]
            or_id = _OR_ID.get(clean_raw)
            inp = self._to_float(prices[0])
            out = self._to_float(prices[3])
            cache = self._to_float(prices[1])
            if inp is None and out is None:
                continue
            cond = "短文本 · ≤272K" if "5.6" in model_raw else "default"
            rec = self._rec(
                model_raw=model_raw,
                input=inp,
                output=out,
                cache_hit=cache,
                context="1M",
                condition=cond,
            )
            if or_id:
                rec["openrouter_id"] = or_id
            records.append(rec)
            # 2) 旗舰区补长文本档
            long_p = _LONG_CONTEXT_PRICES.get(model_raw)
            if long_p:
                rec_long = self._rec(
                    model_raw=model_raw,
                    input=long_p["input"],
                    output=long_p["output"],
                    cache_hit=long_p["cache_hit"],
                    context="1M",
                    condition="长文本 · >272K",
                )
                if or_id:
                    rec_long["openrouter_id"] = or_id
                records.append(rec_long)
        return records

    # ------------------------------------------------------------------ #
    def _extract_tier_rows(self, html: str, tier: str) -> List[tuple]:
        """从页面提取指定 tier 的 (模型名, 价格数组) 列表。"""
        m = _ROWS_JSON_RE.search(html)
        if not m:
            return []
        raw_props = _html.unescape(m.group(1))
        try:
            props = json.loads(raw_props)
        except (json.JSONDecodeError, TypeError):
            return []
        # props 是 [1, {...}] 或 {...} 结构，需容错
        if isinstance(props, list):
            props = props[1] if len(props) > 1 and isinstance(props[1], dict) else props[0]
        if not isinstance(props, dict):
            return []
        tier_val = props.get("tier")
        if isinstance(tier_val, list) and len(tier_val) > 1:
            tier_val = tier_val[1]
        if str(tier_val or "").lower() != tier:
            return []
        rows = props.get("rows")
        items = self._parse_rows_value(rows)
        return items

    @staticmethod
    def _parse_rows_value(rows: Any) -> List[tuple]:
        """把 rows 值解析为 [(模型名, [价格, ...]), ...]。

        rows 形态（经过 json.loads 后）：
            [1, [[1, [[0, "gpt-5.6-sol"], [0,5],[0,0.5],[0,6.25],[0,30]], ...]]]
        简化理解：
            rows = [1, ROWS]；ROWS = [[1, ROW1], [1, ROW2], ...]
            ROWn  = [[0, "gpt-5.6-sol"], [0,5], [0,0.5], ...]
        """
        out: List[tuple] = []
        if not isinstance(rows, list) or len(rows) < 2:
            return out
        row_list = rows[1]
        if not isinstance(row_list, list):
            return out
        for row in row_list:
            if not isinstance(row, list) or len(row) < 2 or row[0] != 1:
                continue
            cells = row[1]
            if not isinstance(cells, list) or len(cells) < 2:
                continue
            model_cell, *price_cells = cells
            model_raw = None
            if isinstance(model_cell, list) and len(model_cell) > 1:
                model_raw = model_cell[1]
            elif isinstance(model_cell, str):
                model_raw = model_cell
            prices: List[Any] = []
            for pc in price_cells:
                if isinstance(pc, list) and len(pc) > 1:
                    prices.append(pc[1])
                else:
                    prices.append(pc)
            if model_raw:
                out.append((model_raw, prices))
        return out

    @staticmethod
    def _to_float(v: Any) -> Optional[float]:
        if isinstance(v, bool):
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            s = v.strip().strip("$").replace(",", "")
            try:
                return float(s)
            except ValueError:
                return None
        return None


# 暴露类名。BaseScraper 子类名推断方式：
# main.py 从模块所有类中找 BaseScraper 子类，任意类名均可。
# 为保持与其他 scraper 命名一致性（如 ZaiScraper），此处类名用 OpenaiScraper。