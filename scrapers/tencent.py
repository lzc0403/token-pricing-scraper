"""腾讯云 TokenHub 定价解析器（仅取广州/中国大陆区域）。

文档用 tab 切换「新加坡」与「广州」两个区域表。本解析器只取「广州」面板下的
语言模型定价表，忽略新加坡。价格为美元（USD）/ 百万 tokens。
"""

from __future__ import annotations

from typing import Any, Dict, List

from scrapers.base import BaseScraper, clean_price

# 区域标签：命中其一即视为「中国大陆 / 广州」区域
_MAINLAND_MARKS = ("广州", "中国大陆", "mainland")


class TencentScraper(BaseScraper):
    """解析 tencentcloud.com 的模型价格页（语言模型 / 广州区域）。"""

    def _select_mainland_panel(self, sel) -> Any:
        """在 语言模型 区域下找到「广州/中国大陆」对应的内容面板。"""
        items = sel.css(".tse-tabs__item")
        labels = [" ".join(it.xpath(".//text()").getall()).strip() for it in items]
        panels = sel.css(".tse-tabs__cont")

        idx = None
        for i, lab in enumerate(labels):
            if any(mark in lab for mark in _MAINLAND_MARKS):
                idx = i
                break
        if idx is None:
            # 兜底：跳过第一个（通常是新加坡），取第二个
            idx = 1 if len(panels) > 1 else 0
        if idx >= len(panels):
            idx = 0
        return panels[idx]

    def parse(self, html: str) -> List[Dict[str, Any]]:
        from parsel import Selector

        sel = Selector(text=html)
        panel = self._select_mainland_panel(sel)
        tables = panel.css("table")
        if not tables:
            return []

        rows = tables[0].css("tr")
        if len(rows) < 2:
            return []

        records: List[Dict[str, Any]] = []
        current_model: Optional[str] = None
        for row in rows[1:]:
            cells = [c.xpath("string(.)").get(default="").strip() for c in row.css("td,th")]
            if len(cells) < 5:
                continue
            model = cells[0].strip()
            # 空模型名（零宽空格等）表示同一模型的阶梯条件续行
            if model and model != "﻿":
                current_model = model
            if not current_model:
                continue
            condition = cells[1].strip() or None
            rec = self._rec(
                model_raw=current_model,
                input=clean_price(cells[2]),
                output=clean_price(cells[3]),
                cache_hit=clean_price(cells[4]),
                context=None,
                condition=condition,
            )
            records.append(rec)
        return records
