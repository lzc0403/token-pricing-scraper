"""火山引擎方舟 Token 定价解析器。

文档为在线推理主定价表（含「模型名称 / 条件 / 输入(非音频) / 输入(音频) /
缓存存储 / 缓存命中(非音频) / 缓存命中(音频) / 输出」）。本解析器定位含
「模型名称」表头的那张表，抽取输入 / 缓存命中 / 输出价格，并仅保留
doubao / seedance 系列（目标关注模型 Seedance 2.0 的等价来源）。
价格为人民币（CNY）/ 百万 tokens。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from scrapers.base import BaseScraper, clean_price


class VolcengineScraper(BaseScraper):
    """解析火山引擎方舟模型价格表。"""

    def parse(self, html: str) -> List[Dict[str, Any]]:
        from parsel import Selector

        sel = Selector(text=html)
        # 定位「在线推理」主定价表（表头含「模型名称」）
        target = None
        for table in sel.css("table"):
            header = [c.xpath("string(.)").get(default="").strip() for c in table.css("tr:first-child td,th")]
            if any("模型名称" in h for h in header):
                target = table
                break
        if target is None:
            return []

        rows = target.css("tr")
        if len(rows) < 2:
            return []

        # 按表头关键词定位列
        header = [c.xpath("string(.)").get(default="").strip() for c in rows[0].css("td,th")]

        def col_index(*keywords: str) -> int:
            for i, h in enumerate(header):
                if any(kw in h for kw in keywords):
                    return i
            return -1

        i_in = col_index("输入(非音频)") if col_index("输入(非音频)") >= 0 else col_index("输入")
        i_out = col_index("输出")
        i_cache = col_index("缓存命中(非音频)") if col_index("缓存命中(非音频)") >= 0 else col_index("缓存命中")

        records: List[Dict[str, Any]] = []
        for row in rows[1:]:
            cells = [c.xpath("string(.)").get(default="").strip().replace("​", "") for c in row.css("td,th")]
            if len(cells) < 8:
                continue
            model = cells[0].strip()
            if not model:
                continue
            low = model.lower()
            # 仅保留 doubao / seedance 系列（与目标模型相关）
            if not (low.startswith("doubao") or "seedance" in low):
                continue
            inp = clean_price(cells[i_in]) if i_in >= 0 else None
            out = clean_price(cells[i_out]) if i_out >= 0 else None
            cache = clean_price(cells[i_cache]) if i_cache >= 0 else None
            if inp is None and out is None:
                continue
            records.append(
                self._rec(
                    model_raw=model,
                    input=inp,
                    output=out,
                    cache_hit=cache,
                    context=None,
                    condition=cells[1].strip() or None,
                )
            )
        return records
