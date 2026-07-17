"""DeepSeek 官网定价解析器。

页面为定义式表格：首行是模型名表头（含 footnote 如 deepseek-v4-flash(1)），
后续每行第一格为标签，其余格为各模型取值。价格单位为「元 / 百万 tokens」。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from scrapers.base import BaseScraper, clean_price

# 去掉模型名后的 footnote 标记，如 deepseek-v4-flash(1) -> deepseek-v4-flash
_FOOTNOTE_RE = re.compile(r"[（(][^（）()]*[)）]\s*$")


class DeepseekScraper(BaseScraper):
    """解析 api-docs.deepseek.com 的模型与价格页。"""

    def _clean_model(self, name: str) -> str:
        name = (name or "").strip()
        return _FOOTNOTE_RE.sub("", name).strip()

    def parse(self, html: str) -> List[Dict[str, Any]]:
        from parsel import Selector

        sel = Selector(text=html)
        tables = sel.css("table")
        if not tables:
            return []

        rows = tables[0].css("tr")
        if len(rows) < 2:
            return []

        # 首行：模型名表头
        header_cells = [c.xpath("string(.)").get(default="").strip() for c in rows[0].css("td,th")]
        models = [self._clean_model(m) for m in header_cells[1:]]
        n = len(models)
        if n == 0:
            return []

        # 关键词 -> 字段，按每行第一格匹配
        def field_of(label: str) -> str:
            if "缓存命中" in label:
                return "cache_hit"
            if "缓存未命中" in label or ("输入" in label and "输出" not in label and "缓存" not in label):
                return "input"
            if "输出" in label:
                return "output"
            if "上下文" in label:
                return "context"
            return ""

        values: Dict[str, List[Any]] = {k: [None] * n for k in ("input", "output", "cache_hit", "context")}
        for row in rows[1:]:
            cells = [c.xpath("string(.)").get(default="").strip() for c in row.css("td,th")]
            if not cells:
                continue
            label = cells[0]
            fld = field_of(label)
            if not fld:
                continue
            raw_vals = cells[1:]
            for i in range(n):
                v = raw_vals[i] if i < len(raw_vals) else (raw_vals[0] if raw_vals else None)
                if fld == "context":
                    values[fld][i] = v if v else None
                else:
                    values[fld][i] = clean_price(v)

        records: List[Dict[str, Any]] = []
        for i, model in enumerate(models):
            rec = self._rec(
                model_raw=model,
                input=values["input"][i],
                output=values["output"][i],
                cache_hit=values["cache_hit"][i],
                context=values["context"][i],
                condition=None,
            )
            records.append(rec)
        return records
