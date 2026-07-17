"""MiniMax 开放平台 Token 定价解析器。

语言模型价格以 CSS-grid 卡片行呈现（非 <table>）：每行 5 个子节点依次为
模型名 / 输入价（¥X/ 百万 tokens）/ 输出价 / 缓存命中价 / 额外价。
本解析器抽取输入 / 输出 / 缓存命中价格。价格为人民币（CNY）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from scrapers.base import BaseScraper, clean_price


class MinimaxScraper(BaseScraper):
    """解析 MiniMax 语言模型价格网格。"""

    def parse(self, html: str) -> List[Dict[str, Any]]:
        from parsel import Selector

        sel = Selector(text=html)
        rows = sel.css("div.grid.items-baseline.py-3")
        records: List[Dict[str, Any]] = []
        for row in rows:
            kids = row.xpath("./div")
            texts = [k.xpath("string(.)").get(default="").strip() for k in kids]
            if len(texts) < 5:
                continue
            model = texts[0]
            inp = clean_price(texts[1])
            out = clean_price(texts[2])
            cache = clean_price(texts[3])
            if not model or (inp is None and out is None):
                continue
            records.append(
                self._rec(
                    model_raw=model,
                    input=inp,
                    output=out,
                    cache_hit=cache,
                    context=None,
                    condition=None,
                )
            )
        return records
