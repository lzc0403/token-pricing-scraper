"""智谱 BigModel（开放平台）Token 定价解析器。

价格页为多张表格（语言模型 / embedding / 图像 …）。本解析器取语言模型主表
（TABLE[1]），其结构为：模型名 | 计费单位/条件 | 输入价格 | 输出价格 |
缓存命中 | （缓存写入）。首行即数据行（无独立表头），空模型名单元格表示
同一模型的阶梯条件续行。价格为人民币（CNY）/ 百万 tokens，缓存命中为
「限时免费」时记为 None。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from scrapers.base import BaseScraper, clean_price


class BigmodelScraper(BaseScraper):
    """解析智谱 BigModel 语言模型定价表。"""

    def parse(self, html: str) -> List[Dict[str, Any]]:
        from parsel import Selector

        sel = Selector(text=html)
        tables = sel.css("table")
        if len(tables) < 2:
            return []
        table = tables[1]
        rows = table.css("tr")
        if not rows:
            return []

        records: List[Dict[str, Any]] = []
        current_model: Optional[str] = None
        for row in rows:
            cells = [c.xpath("string(.)").get(default="").strip() for c in row.css("td,th")]
            if len(cells) < 5:
                continue
            model = cells[0].strip()
            if model:
                current_model = model
            if not current_model:
                continue
            inp = clean_price(cells[2]) if len(cells) > 2 else None
            out = clean_price(cells[3]) if len(cells) > 3 else None
            cache = clean_price(cells[4]) if len(cells) > 4 else None
            if inp is None and out is None:
                continue
            records.append(
                self._rec(
                    model_raw=current_model,
                    input=inp,
                    output=out,
                    cache_hit=cache,
                    context=None,
                    condition=cells[1].strip() or None,
                )
            )
        return records
