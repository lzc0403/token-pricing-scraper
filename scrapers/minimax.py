"""MiniMax 开放平台 Token 定价解析器。

语言模型价格以 CSS-grid 卡片行呈现（非 <table>）：
- M2.7 系列：每行 5 个子节点 = 模型名 / 输入价 / 输出价 / 缓存读取价 / 缓存写入价
- M3 系列：每行 4 个子节点 = 模型名 / 输入价 / 输出价 / 缓存读取价
  （无「缓存写入」列；且每个价格格内含「原价划掉 + 实价加粗」双价，永久折扣）

本解析器：
  * 列数阈值放宽到 4，确保 M3（4 列）不被漏抓；
  * 模型名取首个空白分隔 token（剥离「上下文 ≤ 512K」「永久五折」等徽标文字）；
  * 价格取每个价格格中的**最后一个**数字（即实价/折后价，而非划掉的原价）。
价格为人民币（CNY）/ 百万 tokens。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from scrapers.base import BaseScraper, clean_price


class MinimaxScraper(BaseScraper):
    """解析 MiniMax 语言模型价格网格。"""

    def parse(self, html: str) -> List[Dict[str, Any]]:
        from parsel import Selector

        sel = Selector(text=html)
        # M2.7 系列行：grid + items-baseline + py-3；M3 系列行：grid + items-center + py-4
        rows = sel.css("div.grid.items-baseline.py-3, div.grid.items-center.py-4")
        records: List[Dict[str, Any]] = []
        for row in rows:
            kids = row.xpath("./div")
            if len(kids) < 4:
                continue
            # 模型名：优先取首个 <span> 文本（M3 行模型名在嵌套 span，避免带出「上下文/折扣」徽标文字）；
            # 否则回退到整节点首 token。
            name_span = kids[0].xpath(".//span[1]/text()").get(default="").strip()
            if name_span:
                model = name_span.split()[0]
            else:
                raw_name = kids[0].xpath("string(.)").get(default="").strip()
                model = raw_name.split()[0] if raw_name else ""
            if not model:
                continue
            # 上下文徽标（M3 行的「上下文 ≤ 512K」等）：取含「上下文」的 span 文本并精简
            ctx_badge = kids[0].xpath(".//span[contains(., '上下文')]/text()").get(default="").strip()
            context = None
            if ctx_badge:
                m = re.search(r"上下文\s*([\d.K~≤\s]+)", ctx_badge)
                if m:
                    context = m.group(1).replace(" ", "")
            # 价格格：首个子节点之后的每一个；每个价格格取最后一个数字（实价/折后价）
            prices: List[Optional[float]] = []
            for cell in kids[1:]:
                txt = cell.xpath("string(.)").get(default="")
                nums = re.findall(r"[\d.]+", txt)
                prices.append(float(nums[-1]) if nums else None)
            inp = prices[0] if len(prices) > 0 else None
            out = prices[1] if len(prices) > 1 else None
            cache = prices[2] if len(prices) > 2 else None
            if inp is None and out is None:
                continue
            records.append(
                self._rec(
                    model_raw=model,
                    input=inp,
                    output=out,
                    cache_hit=cache,
                    context=context,
                    condition=None,
                )
            )
        return records
