"""DeepSeek 官网定价解析器。

2026-08 改版后页面为峰谷定价表：
- 首行表头为模型名（含 footnote 如 deepseek-v4-flash(1)）
- 价格区每类（缓存命中/缓存未命中/输出）拆成两行：
    「标签 子标签 值1 值2」   （子标签=空闲时段/OFF-PEAK）
    「高峰时段 值1 值2」       （子标签=高峰时段/PEAK）
- 单位从「元/百万tokens」改为「元」/「$」，但仍按每百万 tokens 计费。

输出字段：
- input/output/cache_hit：取**高峰时段**价（官网基准价，用作主价展示与排序对照）
- peak_input_low/peak_input_high 等 6 字段：峰谷双档全量
- condition="峰谷计费"
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from scrapers.base import BaseScraper, clean_price

# 去掉模型名后的 footnote 标记，如 deepseek-v4-flash(1) -> deepseek-v4-flash
_FOOTNOTE_RE = re.compile(r"[（(][^（）()]*[)）]\s*$")


class DeepseekScraper(BaseScraper):
    """解析 api-docs.deepseek.com 的模型与价格页（2026 峰谷版）。"""

    def _clean_model(self, name: str) -> str:
        name = (name or "").strip()
        return _FOOTNOTE_RE.sub("", name).strip()

    def _is_peak(self, label: str) -> bool:
        """判断行标签是否为「高峰时段」/「PEAK」。"""
        lab = (label or "").strip().lower()
        return "高峰时段" in label or lab == "peak"

    def _field_of(self, label: str) -> str:
        """把中文/英文价格类别标签映射到字段名。"""
        lab = (label or "").lower()
        # 缓存命中：中英文（必须先判断）
        if "缓存命中" in label or "cache hit" in lab:
            return "cache_hit"
        # 缓存未命中 -> input
        if "缓存未命中" in label or "cache miss" in lab:
            return "input"
        if "input" in lab or "输入" in label:
            return "input"
        if "output" in lab or "输出" in label:
            return "output"
        return ""

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

        # 峰谷存储：{字段: {模型索引: {'low': v, 'high': v}}}
        peak: Dict[str, List[Dict[str, Any]]] = {
            "input": [{"low": None, "high": None} for _ in range(n)],
            "output": [{"low": None, "high": None} for _ in range(n)],
            "cache_hit": [{"low": None, "high": None} for _ in range(n)],
        }
        context: List[Any] = [None] * n
        last_field: str = ""  # 承接上一个价格类别（形态 B 高峰行需要）

        for row in rows[1:]:
            cells = [c.xpath("string(.)").get(default="").strip() for c in row.css("td,th")]
            if not cells:
                continue

            label = cells[0]
            # 上下文长度行：单列值或两列值
            if "上下文" in label or "context" in label.lower():
                raw_vals = cells[1:]
                for i in range(n):
                    v = raw_vals[i] if i < len(raw_vals) else (raw_vals[0] if raw_vals else None)
                    context[i] = v if v else None
                continue

            # 价格行：两种形态
            #   A) [总标签?, 类别标签, 子标签(空闲/OFF-PEAK), 值1, 值2]   len > n+1
            #      （总标签如「价格(1)」可能占首格，也可能省略；cells[1] 才是类别）
            #   B) [子标签(高峰/PEAK), 值1, 值2]              len == n+1 且子标签是高峰
            #   C) [类别标签, 值1, 值2]                        旧版单档（兜底）
            if len(cells) > n + 1:
                # 形态 A：尝试 cells[0]，失败则尝试 cells[1] 作为类别
                fld = self._field_of(cells[0])
                if fld:
                    raw_vals = cells[2:]
                else:
                    fld = self._field_of(cells[1]) if len(cells) > 1 else ""
                    if not fld:
                        continue
                    raw_vals = cells[3:] if len(cells) > 3 else cells[2:]
                last_field = fld
                for i in range(n):
                    v = raw_vals[i] if i < len(raw_vals) else (raw_vals[0] if raw_vals else None)
                    peak[fld][i]["low"] = clean_price(v)
            elif self._is_peak(cells[0]):
                # 形态 B：高峰子标签 + 值（承接上一个类别）
                if not last_field:
                    continue
                raw_vals = cells[1:]
                for i in range(n):
                    v = raw_vals[i] if i < len(raw_vals) else (raw_vals[0] if raw_vals else None)
                    peak[last_field][i]["high"] = clean_price(v)
            else:
                # 形态 C：旧版单档兜底
                fld = self._field_of(cells[0])
                if not fld:
                    continue
                last_field = fld
                raw_vals = cells[1:]
                for i in range(n):
                    v = raw_vals[i] if i < len(raw_vals) else (raw_vals[0] if raw_vals else None)
                    pv = clean_price(v)
                    peak[fld][i]["low"] = pv
                    peak[fld][i]["high"] = pv  # 无峰谷区分时双档同值

        records: List[Dict[str, Any]] = []
        for i, model in enumerate(models):
            rec = self._rec(
                model_raw=model,
                input=peak["input"][i]["high"],
                output=peak["output"][i]["high"],
                cache_hit=peak["cache_hit"][i]["high"],
                context=context[i],
                condition="峰谷计费",
            )
            # 峰谷双档全量字段（_rec 不原生支持，手动扩展）
            rec["peak_input_low"] = peak["input"][i]["low"]
            rec["peak_input_high"] = peak["input"][i]["high"]
            rec["peak_output_low"] = peak["output"][i]["low"]
            rec["peak_output_high"] = peak["output"][i]["high"]
            rec["peak_cache_low"] = peak["cache_hit"][i]["low"]
            rec["peak_cache_high"] = peak["cache_hit"][i]["high"]
            records.append(rec)
        return records
