"""智谱 BigModel（开放平台）Token 定价解析器。

价格页为多张表格（语言模型 / embedding / 图像 …）。本解析器取语言模型主表
（TABLE[1]），其结构为：模型名 | 计费单位/条件 | 输入价格 | 输出价格 |
缓存命中 | （缓存写入）。首行即数据行（无独立表头），空模型名单元格表示
同一模型的阶梯条件续行。价格为人民币（CNY）/ 百万 tokens，缓存命中为
「限时免费」时记为 None。

**限时促销处理**：促销行（如 GLM-5.3-Flash）单元格结构不同于普通行：
- 模型名列 `name-box` 内含两个节点 —— 首个 `<p>` 是纯模型名，其后 `<div>` 是
  促销标签（如「5折限时两周」）。直接 `string(.)` 会把标签粘进模型名，
  导致 matcher 归一化后匹配不上而被丢弃。
- 价格列 `price-box` 内含两个 `.price-line` —— 首个是折后价，其后是划线原价。
  直接 `string(.)` 会得到「1.4元 2.8元」，`clean_price` 去符号后拼成「1.42.8」
  并误读为 1.42（真实 1.4）。

因此取值一律「取首个目标节点」，促销结束后节点数回落为 1，逻辑自动兼容。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from scrapers.base import BaseScraper, clean_price

# 剥离官网价格表里的营销/状态装饰后缀，避免 matcher 精确匹配失败
# 例：「GLM-5.2 新品」「GLM-5-Turbo 新」→「GLM-5.2」「GLM-5-Turbo」
_SUFFIX_RE = re.compile(r"\s*(新品|新上市|新|New|NEW|限时|预览|Preview|Beta|beta|尝鲜)\s*$", re.I)


def _model_name(cell) -> str:
    """取模型名：`name-box` 内首个 `<p>`，忽略其后的促销标签 div。

    促销行形如 `<div class="name-box"><p>GLM-5.3-Flash</p><div>5折限时两周</div></div>`。
    """
    texts = cell.css(".name-box p::text").getall()
    if not texts:
        texts = cell.css("p::text").getall()
    if texts:
        return texts[0].strip()
    return cell.xpath("string(.)").get(default="").strip()


def _price_text(cell) -> str:
    """取价格：`price-box` 内首个 `.price-line`（折后价），忽略划线原价。

    促销行形如 `<div class="price-box"><p class="price-line">1.4元</p>
    <p class="price-line">2.8元</p></div>`：首个是折后价，其后是划线原价。
    """
    texts = cell.css(".price-line::text").getall()
    if texts:
        return texts[0].strip()
    return cell.xpath("string(.)").get(default="").strip()


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
            cells = row.css("td,th")
            if len(cells) < 5:
                continue
            model = _SUFFIX_RE.sub("", _model_name(cells[0])).strip()
            if model:
                current_model = model
            if not current_model:
                continue
            inp = clean_price(_price_text(cells[2]))
            out = clean_price(_price_text(cells[3]))
            cache = clean_price(_price_text(cells[4]))
            if inp is None and out is None:
                continue
            cond = cells[1].xpath("string(.)").get(default="").strip()
            records.append(
                self._rec(
                    model_raw=current_model,
                    input=inp,
                    output=out,
                    cache_hit=cache,
                    context=None,
                    condition=cond or None,
                )
            )
        return records
