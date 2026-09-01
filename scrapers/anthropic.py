"""Anthropic 官网（platform.claude.com，USD）模型定价解析器。

数据源：https://platform.claude.com/docs/en/about-claude/pricing
（原 docs.anthropic.com 会 301 到此地址。）

页面为静态 HTML，主定价表为页面第一张 <table>（16 行），6 列：

    Model | Base Input Tokens | 5m Cache Writes | 1h Cache Writes |
    Cache Hits & Refreshes | Output Tokens

价格格式「$5 / MTok」，单位 USD / 百万 tokens。

收录策略：
- 只取 5m 缓存写入档（1h 档价格 2× input，场景少见，不入库；列仍解析但丢弃）。
- cache_write = 5m Cache Writes；cache_hit = Cache Hits & Refreshes。
- 已退役模型（Opus 4.1 / Opus 4 / Sonnet 4 / Haiku 3.5 等页面标注 retired 的行）
  不收录——通过白名单 canonical 过滤，未知模型名自动跳过。
- model_raw 保留页面显示名（如 "Claude Opus 5"），同时附 openrouter_id
  （anthropic/claude-opus-5）供 main.py 白名单通道强制 canonical。

canonical 由 openrouter.yml 白名单同 id 映射（main.py 白名单通道，source=anthropic）。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from parsel import Selector

from scrapers.base import BaseScraper

# 页面显示名 → OpenRouter id（白名单通道用）。仅收录站内在册模型。
_MODEL_OR_ID: Dict[str, str] = {
    "Claude Fable 5": "anthropic/claude-fable-5",
    "Claude Opus 5": "anthropic/claude-opus-5",
    "Claude Opus 4.8": "anthropic/claude-opus-4.8",
    "Claude Opus 4.7": "anthropic/claude-opus-4.7",
    "Claude Opus 4.6": "anthropic/claude-opus-4.6",
    "Claude Opus 4.5": "anthropic/claude-opus-4.5",
    "Claude Sonnet 5": "anthropic/claude-sonnet-5",
    "Claude Sonnet 4.6": "anthropic/claude-sonnet-4.6",
    "Claude Sonnet 4.5": "anthropic/claude-sonnet-4.5",
    "Claude Haiku 4.5": "anthropic/claude-haiku-4.5",
}

# 「$5 / MTok」/「$0.50 / MTok」→ 5.0 / 0.5
_PRICE_RE = re.compile(r"\$([\d,.]+)")

# 主定价表表头特征（6 列齐全才算，避免误抓 batch/工具表）
_HEADER_KEYS = ("base input", "cache writes", "cache hits", "output")


def _price(cell: str) -> Optional[float]:
    """「$5 / MTok」→ 5.0；无价格（'—' 等）→ None。"""
    m = _PRICE_RE.search(cell or "")
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


class AnthropicScraper(BaseScraper):
    """解析 platform.claude.com 官方定价页（USD）。"""

    def parse(self, html: str) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        sel = Selector(text=html)
        table = self._find_main_table(sel)
        if table is None:
            return records

        for row in table.css("tr")[1:]:
            cells = [
                c.xpath("string(.)").get(default="").strip()
                for c in row.css("td,th")
            ]
            # 6 列：Model | Base Input | 5m Writes | 1h Writes | Cache Hits | Output
            if len(cells) < 6:
                continue
            name = cells[0].strip()
            # 去掉标注后缀（如 "(limited availability)"、retired 标记）
            display = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
            or_id = _MODEL_OR_ID.get(display)
            if or_id is None:
                # 未在册（含退役模型、Mythos 等限量供应）一律跳过
                continue
            inp = _price(cells[1])
            cwrite = _price(cells[2])
            chit = _price(cells[4])
            out = _price(cells[5])
            if inp is None and out is None:
                continue
            rec = self._rec(
                model_raw=display,
                input=inp,
                output=out,
                cache_hit=chit,
                cache_write=cwrite,
                context="200K",
                condition=None,
            )
            rec["openrouter_id"] = or_id
            records.append(rec)
        return records

    @staticmethod
    def _find_main_table(sel: Selector):
        """定位主定价表：表头同时含 Base Input / Cache Writes / Cache Hits / Output。"""
        for table in sel.css("table"):
            header = " ".join(
                c.xpath("string(.)").get(default="").strip().lower()
                for c in table.css("tr:first-child th, tr:first-child td")
            )
            if all(k in header for k in _HEADER_KEYS):
                return table
        return None
