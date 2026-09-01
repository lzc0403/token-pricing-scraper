"""Google Gemini 官网（ai.google.dev，USD）模型定价解析器。

数据源：https://ai.google.dev/gemini-api/docs/pricing

页面为静态 HTML，每个模型一个 <h2> 标题，其下按档位分 <h3>（Standard / Batch /
Flex / Priority），每个档位下有若干张表（Input/Output/Context caching 等）。
本解析器只取 **Standard 档**（默认展示档位）：

    h2 "Gemini 3.7 Flash" → h3 "Standard" → table
      行「Input price」     → Paid Tier 列 → input
      行「Output price ...」→ Paid Tier 列 → output
      行「Context caching price」→ Paid Tier 列 → cache_hit

促销价陷阱：Paid Tier 单元格形如

    "$0.75 through December 31, 2026.$1.50 starting January 1, 2027."

即「促销价 through <日期>. 标准价 starting <日期>.」。解析规则：取**当前生效**
的价格——若存在 `through <日期>` 且该日期晚于今天，取促销价；否则取标准价
（最后一个价格）。不能盲目取首个，否则促销过期后抓到过期价。

Gemini 3.5 Pro 官网已无独立条目（被 3.1 Pro Preview 取代），无法收录，
该 canonical 继续由 config/mainstream_models.yml 目录静态价提供。

canonical 由 openrouter.yml 白名单同 id 映射（source=gemini，白名单 id=google/gemini-*）。
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from parsel import Selector

from scrapers.base import BaseScraper

# h2 模型名 → OpenRouter id（白名单通道用）。仅收录站内在册文本模型。
_MODEL_OR_ID: Dict[str, str] = {
    "Gemini 3.7 Flash": "google/gemini-3.7-flash",
    "Gemini 3.5 Flash": "google/gemini-3.5-flash",
    "Gemini 2.5 Pro": "google/gemini-2.5-pro",
    "Gemini 2.5 Flash": "google/gemini-2.5-flash",
}

_PRICE_RE = re.compile(r"\$([\d,.]+)")
# 「$0.75 through December 31, 2026.」促销段
_PROMO_RE = re.compile(
    r"\$([\d,.]+)\s+through\s+([A-Z][a-z]+ \d{1,2}, \d{4})", re.I
)


def _effective_price(cell: str) -> Optional[float]:
    """从 Paid Tier 单元格取当前生效价（处理促销期文本）。

    - 无促销段：取单元格内最后一个价格（有时前面带上下文说明）。
    - 有促销段：促销截止日期未到 → 促销价；已过 → 标准价。
    """
    text = (cell or "").strip()
    if not text:
        return None
    prices = [float(x.replace(",", "")) for x in _PRICE_RE.findall(text)]
    if not prices:
        return None
    promo = _PROMO_RE.search(text)
    if promo:
        promo_price = float(promo.group(1).replace(",", ""))
        try:
            until = datetime.strptime(promo.group(2), "%B %d, %Y").date()
        except ValueError:
            until = None
        today = date.today()
        if until is not None and today <= until:
            return promo_price
    return prices[-1]


class GeminiScraper(BaseScraper):
    """解析 ai.google.dev Gemini API 定价页（USD）。"""

    def parse(self, html: str) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        sel = Selector(text=html)
        body = sel.css("main") or sel.css("body") or sel
        self._cur_model: Optional[str] = None
        self._in_standard = True
        # 以文档顺序遍历 h2/h3/table，跟踪「当前模型」与「是否 Standard 档」
        for node in body.css("h2, h3, table"):
            tag = node.root.tag
            if tag == "h2":
                self._cur_model = node.xpath("string(.)").get(default="").strip()
                self._in_standard = True  # h2 后、h3 前出现的表视为默认档
            elif tag == "h3":
                level = node.xpath("string(.)").get(default="").strip().lower()
                self._in_standard = level == "standard"
            elif tag == "table" and self._cur_model in _MODEL_OR_ID and self._in_standard:
                rec = self._parse_model_table(node)
                if rec is not None:
                    records.append(rec)
                    self._cur_model = None  # 每个模型只取第一张 Standard 表
        return records

    def _parse_model_table(self, table) -> Optional[Dict[str, Any]]:
        """从单模型 Standard 表提取 input/output/cache_hit。"""
        inp = out = cache = None
        for row in table.css("tr"):
            cells = [
                c.xpath("string(.)").get(default="").strip()
                for c in row.css("td,th")
            ]
            if len(cells) < 3:
                continue
            label = cells[0].lower()
            # Paid Tier 列：第 3 列起找第一个含 $ 的单元格
            paid = next((c for c in cells[2:] if "$" in c), None)
            if paid is None:
                continue
            if label.startswith("input"):
                inp = _effective_price(paid)
            elif label.startswith("output"):
                out = _effective_price(paid)
            elif "context caching" in label and "storage" not in label:
                # 缓存价单元格可能含 storage 单价（每小时），_effective_price
                # 取最后一个 $ 数字会误取 storage 价；这里只取第一个 $ 数字。
                m = _PRICE_RE.search(paid)
                if m:
                    cache = float(m.group(1).replace(",", ""))
        if inp is None and out is None:
            return None
        model_name = self._cur_model or ""
        rec = self._rec(
            model_raw=model_name,
            input=inp,
            output=out,
            cache_hit=cache,
            context="1M",
            condition=None,
        )
        rec["openrouter_id"] = _MODEL_OR_ID[model_name]
        return rec
