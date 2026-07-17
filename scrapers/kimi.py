"""Kimi 开放平台 Token 定价解析器。

每个定价页（chat-k26 / chat-k25 / chat-k27-code）为一张定义式表格：
首行表头（模型 / 计费单位 / 输入价格（缓存命中）/ 输入价格（缓存未命中）/
输出价格 / 上下文窗口），其后每行一个模型。本解析器按表头关键词定位列，
抽取缓存命中 / 输入 / 输出价格与上下文窗口。价格为人民币（CNY）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from scrapers.base import BaseScraper, clean_price


class KimiScraper(BaseScraper):
    """解析 Kimi 平台模型价格表。"""

    def parse(self, html: str) -> List[Dict[str, Any]]:
        from parsel import Selector

        sel = Selector(text=html)
        tables = sel.css("table")
        if not tables:
            return []
        rows = tables[0].css("tr")
        if len(rows) < 2:
            return []

        header = [c.xpath("string(.)").get(default="").strip() for c in rows[0].css("td,th")]

        def idx_of(*keywords: str) -> int:
            for i, h in enumerate(header):
                if any(kw in h for kw in keywords):
                    return i
            return -1

        i_model = idx_of("模型")
        i_cache = idx_of("缓存命中")
        i_input = idx_of("缓存未命中", "输入价格")
        i_output = idx_of("输出价格")
        i_ctx = idx_of("上下文")
        if i_model < 0 or i_input < 0 or i_output < 0:
            return []

        records: List[Dict[str, Any]] = []
        for row in rows[1:]:
            cells = [c.xpath("string(.)").get(default="").strip() for c in row.css("td,th")]
            if len(cells) <= max(i_model, i_input, i_output):
                continue
            model = cells[i_model].strip()
            if not model:
                continue
            rec = self._rec(
                model_raw=model,
                input=clean_price(cells[i_input]),
                output=clean_price(cells[i_output]),
                cache_hit=clean_price(cells[i_cache]) if i_cache >= 0 else None,
                context=cells[i_ctx].strip() if (i_ctx >= 0 and i_ctx < len(cells)) else None,
                condition=None,
            )
            records.append(rec)
        return records
