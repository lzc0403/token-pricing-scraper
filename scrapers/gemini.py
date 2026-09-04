"""Google Gemini 官网（ai.google.dev，USD）模型定价解析器。

数据源：https://ai.google.dev/gemini-api/docs/pricing

页面为静态 HTML，每个模型一个 <h2> 标题，其下按档位分 <h3>（Standard / Batch /
Flex / Priority），每个档位下有若干张表（Input/Output/Context caching 等）。
本解析器只取 **Standard 档**（默认展示档位），且只收录站内白名单模型
（_MODEL_OR_ID；当前仅 3.8/3.7/3.6 Flash）：

    h2 "Gemini 3.8 Flash" → h3 "Standard" → table
      行「Input price」     → Paid Tier 列 → input
      行「Output price ...」→ Paid Tier 列 → output
      行「Context caching price」→ Paid Tier 列 → cache_hit

促销价陷阱：Paid Tier 单元格形如

    "$0.75 through December 31, 2026.$1.50 starting January 1, 2027."

即「促销价 through <日期>. 标准价 starting <日期>.」。解析规则：取**当前生效**
的价格——若存在 `through <日期>` 且该日期晚于今天，取促销价；否则取标准价
（最后一个价格）。不能盲目取首个，否则促销过期后抓到过期价。

收录口径（2026-09 起）：Gemini 只保留 3.8 Flash / 3.7 Flash / 3.6 Flash
三个在售主力，其余（3.5 Pro / 3.5 Flash / 2.5 Pro / 2.5 Flash）已下架不收录。
其中 3.5 Pro 官网本就无独立条目（被 3.1 Pro Preview 取代）。

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
    "Gemini 3.8 Flash": "google/gemini-3.8-flash",
    "Gemini 3.7 Flash": "google/gemini-3.7-flash",
    "Gemini 3.6 Flash": "google/gemini-3.6-flash",
}

_PRICE_RE = re.compile(r"\$([\d,.]+)")
# 「$0.75 through December 31, 2026.」促销段
_PROMO_RE = re.compile(
    r"\$([\d,.]+)\s+through\s+([A-Z][a-z]+ \d{1,2}, \d{4})", re.I
)
# 缓存存储价：「$0.50 / 1,000,000 tokens per hour (storage price) ...」
# 单位按小时计费，与按 token 计价的输入/输出/缓存读取不是同一维度。
_STORAGE_PRICE_RE = re.compile(r"\$([\d,.]+)\s*/\s*1,000,000\s*tokens per hour", re.I)
_STORAGE_THROUGH_RE = re.compile(r"through\s+([A-Z][a-z]+ \d{1,2}, \d{4})", re.I)


def _effective_price(cell: str) -> Optional[float]:
    """从 Paid Tier 单元格取当前生效价（处理促销期文本）。

    - 无促销段：取单元格内**第一个**价格，即「基准档」。官网把更高档位
      写在后面，例如
        * Gemini 2.5 Pro：$1.25（≤200k）在前、$2.50（>200k）在后
        * Gemini 2.5 Flash：$0.30（文本/图像/视频）在前、$1.00（音频）在后
      若误取最后一个会抓成「长上下文档」或「音频档」，导致同一行
      输入/输出/缓存来自不同档位（历史 bug：2.5 Pro 曾出现
      input=2.5(>200k) 与 cache=0.125(≤200k) 的混搭；2.5 Flash 曾把
      输入价抓成音频档 $1.00）。
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
    return prices[0]


def _storage_price(cell: str) -> Optional[float]:
    """从 Context caching 单元格提取**缓存存储价**（USD / 1M tokens / 小时）。

    官网把「缓存读取价」与「缓存存储价」写在同一格，例如：

        $0.075 through December 31, 2026.$0.15 starting January 1, 2027.
        $0.50 / 1,000,000 tokens per hour (storage price) through December 31, 2026.
        $1.00 / 1,000,000 tokens per hour (storage price) starting January 1, 2027.

    存储价同样带促销期，按日期取当前生效值（未过期取促销价，已过期取末值）。
    单位与 token 单价不同（按小时计费），因此不与 cache_hit/cache_write 混用。
    """
    text = cell or ""
    hits: List[tuple] = []
    for m in _STORAGE_PRICE_RE.finditer(text):
        try:
            price = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        tail = text[m.end() : m.end() + 120]
        dm = _STORAGE_THROUGH_RE.search(tail)
        until = None
        if dm:
            try:
                until = datetime.strptime(dm.group(1), "%B %d, %Y").date()
            except ValueError:
                until = None
        hits.append((price, until))
    if not hits:
        return None
    today = date.today()
    for price, until in hits:
        if until is not None and today <= until:
            return price
    return hits[-1][0]


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
        inp = out = cache = storage = None
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
                # 缓存读取价：取单元格首个 $ 数字（基准档），storage 单价单独提取。
                m = _PRICE_RE.search(paid)
                if m:
                    cache = float(m.group(1).replace(",", ""))
                # 缓存存储价（Google 语境下的「缓存创建」成本，按小时计费）
                storage = _storage_price(paid)
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
        # Google 无「按 token 的缓存写入价」，只有缓存存储费（$/1M tokens/小时），
        # 单独落 cache_storage 字段，单位与 token 单价不同，不混入 cache_write。
        rec["cache_storage"] = storage
        rec["openrouter_id"] = _MODEL_OR_ID[model_name]
        return rec
