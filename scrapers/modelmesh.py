"""ModelMesh 模型中心定价解析器。

页面以卡片网格展示各厂商模型，每张卡片含：模型名（「厂商 / 模型名（限时X折）」）、
上下文长度、输入价（「¥ N / M 输入 tokens」）、输出价（「¥ N / M 输出 tokens」）。
海外模型价格为美元并附带人民币换算，如「$ 2.50 (¥17.50) / M 输入 tokens」，
本解析器通过 prefer_currency="¥" 始终取人民币等价。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from scrapers.base import BaseScraper, clean_price

# 卡片名 div 的选择器（含冒号的 class 需转义）
_NAME_SEL = "div.truncate.text-base.md\\:text-lg.font-bold"
# 上下文长度提取，如 "1000K 上下文" -> "1000K"
_CTX_RE = re.compile(r"(\d+K)\s*上下文")


class ModelmeshScraper(BaseScraper):
    """解析 ModelMesh 模型中心卡片价格。"""

    @staticmethod
    def _extract_model(name_text: str) -> str:
        """从「厂商 / 模型名（限时X折）」中提取并清洗模型名。"""
        if " / " in name_text:
            model = name_text.split(" / ", 1)[1]
        else:
            model = name_text
        # 去掉末尾的「（限时X折）」等括号说明
        model = re.sub(r"[（(][^（）()]*[）)]\s*$", "", model).strip()
        return model

    @staticmethod
    def _find_card(name_div) -> Any:
        """向上回溯，找到同时包含输入 / 输出价格叶子的卡片容器。"""
        node = name_div
        for _ in range(8):
            node = node.xpath("..")
            if not node:
                break
            inner = node.xpath("string(.)").get(default="")
            if "M 输入 tokens" in inner and "M 输出 tokens" in inner:
                return node
        return None

    def parse(self, html: str) -> List[Dict[str, Any]]:
        from parsel import Selector

        sel = Selector(text=html)
        names = sel.css(_NAME_SEL)
        records: List[Dict[str, Any]] = []
        for name_div in names:
            name_text = name_div.xpath("string(.)").get(default="").strip()
            if not name_text:
                continue
            model = self._extract_model(name_text)
            card = self._find_card(name_div)
            if card is None:
                continue

            in_leaf = card.xpath(
                ".//div[contains(., 'M 输入 tokens') and not(contains(., 'M 输出 tokens'))]"
            )
            out_leaf = card.xpath(
                ".//div[contains(., 'M 输出 tokens') and not(contains(., 'M 输入 tokens'))]"
            )
            ctx_leaf = card.xpath(".//div[contains(., '上下文')]")

            inp = (
                clean_price(in_leaf[0].xpath("string(.)").get(default=""), prefer_currency="¥")
                if in_leaf
                else None
            )
            out = (
                clean_price(out_leaf[0].xpath("string(.)").get(default=""), prefer_currency="¥")
                if out_leaf
                else None
            )
            ctx: Optional[str] = None
            for c in ctx_leaf:
                m = _CTX_RE.search(c.xpath("string(.)").get(default=""))
                if m:
                    ctx = m.group(1)
                    break

            if inp is None and out is None:
                continue
            records.append(
                self._rec(
                    model_raw=model,
                    input=inp,
                    output=out,
                    cache_hit=None,
                    context=ctx,
                    condition=None,
                )
            )
        return records
