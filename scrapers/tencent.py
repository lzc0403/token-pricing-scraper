"""腾讯云 TokenHub 定价解析器（国际站，仅取广州/中国大陆区域）。

数据源：https://cloud.tencent.com/document/product/1729/97731
（腾讯云大模型服务平台 TokenHub 模型价格，国际站，USD/百万 tokens）

文档用 tab 切换「新加坡」与「广州」两个区域表。本解析器只取「广州」面板下的
语言模型定价表，忽略新加坡。价格为美元（USD）/ 百万 tokens。

DeepSeek 来源类型区分（与国内站 tencent_cn.py 同规则）：
- 页面上 DeepSeek 模型名带「原厂直供」后缀的行 → DeepSeek 官方部署（原厂直供）
- 同名、无后缀的行 → 腾讯云自建部署
  「腾讯云自建」这四个字本身不出现在单元格中，通过同名匹配判定。
- 非 DeepSeek 模型（如 hunyuan）无此区分，condition 保留 token 长度条件或 None。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from scrapers.base import BaseScraper, clean_price

# 区域标签：命中其一即视为「中国大陆 / 广州」区域
_MAINLAND_MARKS = ("广州", "中国大陆", "mainland")

# 「原厂直供」后缀剥离
_FACTORY_SUFFIX = "原厂直供"


def _strip_factory(raw: str) -> str:
    """剥离模型名末尾的「原厂直供」后缀，返回基础名。"""
    base = raw.replace(_FACTORY_SUFFIX, "").strip()
    base = re.sub(r"\s+", " ", base).strip()
    return base


# 正式版标记：DeepSeek-V4-Flash 0731 正式版（新价格） → 剥离「0731 正式版」「（新价格）」
# 「0731/0813 正式版」仅用于归一化基础名，不进入来源 condition 展示
_OFFICIAL_RE = re.compile(r"(\d{4})?\s*正式版")
_NEWPRICE_RE = re.compile(r"[（(]\s*新价格\s*[)）]")


def _clean_model(raw: str) -> str:
    """清洗模型名，剥离「原厂直供」「（新价格）」「0731/0813 正式版」等后缀，只留基础名。"""
    base = _strip_factory(raw)
    base = _NEWPRICE_RE.sub("", base).strip()
    base = _OFFICIAL_RE.sub("", base).strip()
    return base


class TencentScraper(BaseScraper):
    """解析 tencentcloud.com 国际站的模型价格页（语言模型 / 广州区域，USD）。"""

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

        # 表头动态列定位（页面列结构可能变化：新增「峰谷计费」列等）
        header_cells = [c.xpath("string(.)").get(default="").strip() for c in rows[0].css("td,th")]
        col = {"model": 0, "cond": 1, "peak": None, "input": None, "output": None, "cache": None}
        for idx, h in enumerate(header_cells):
            if "峰谷" in h:
                col["peak"] = idx
            elif "输入" in h and "输出" not in h and "缓存" not in h:
                col["input"] = idx
            elif "输出" in h and "输入" not in h and "缓存" not in h:
                col["output"] = idx
            elif "缓存" in h:
                col["cache"] = idx
        if col["input"] is None or col["output"] is None:
            return []  # 表头未识别，跳过

        # 第一遍扫描：收集所有带「原厂直供」后缀的基础名
        factory_bases: set = set()
        current_model: Optional[str] = None
        for row in rows[1:]:
            cells = [c.xpath("string(.)").get(default="").strip() for c in row.css("td,th")]
            if len(cells) <= max(i for i in col.values() if i is not None):
                continue
            model = cells[col["model"] or 0].strip()
            if model and model != "\ufeff":
                current_model = model
            if not current_model:
                continue
            if _FACTORY_SUFFIX in current_model:
                base = _clean_model(current_model)
                factory_bases.add(base.lower())

        # 第二遍：生成记录，判定来源类型
        records: List[Dict[str, Any]] = []
        seen: Dict[tuple, Dict[str, Any]] = {}
        current_model = None
        for row in rows[1:]:
            cells = [c.xpath("string(.)").get(default="").strip().replace("\ufeff", "") for c in row.css("td,th")]
            if len(cells) <= max(i for i in col.values() if i is not None):
                continue
            model = cells[col["model"] or 0].strip()
            # 空模型名（零宽空格等）表示同一模型的阶梯条件续行
            if model:
                current_model = model
            if not current_model:
                continue

            token_cond = cells[col["cond"]].strip() if col["cond"] is not None else None
            token_cond = token_cond if token_cond and token_cond != "-" else None
            peak_cond = (cells[col["peak"]].strip() if col["peak"] is not None else "") if col["peak"] is not None else ""
            peak_cond = peak_cond if peak_cond and peak_cond != "-" else None
            # 来源类型判定 + 模型名归一（0731/0813 正式版不进入 condition）
            base = _clean_model(current_model)
            if _FACTORY_SUFFIX in current_model:
                source_type = "原厂直供"
            elif base.lower() in factory_bases:
                source_type = "腾讯云自建"
            else:
                source_type = None

            # 合并 峰谷 / token 条件 / 来源类型 到 condition
            parts = []
            if peak_cond:
                parts.append(peak_cond)
            if source_type:
                parts.append(source_type)
            if token_cond:
                parts.append(token_cond)
            condition = " | ".join(parts) if parts else None

            key = (base.lower(), condition)
            rec = self._rec(
                model_raw=base,
                input=clean_price(cells[col["input"]]),
                output=clean_price(cells[col["output"]]),
                cache_hit=clean_price(cells[col["cache"]]) if col["cache"] is not None else None,
                context=None,
                condition=condition,
            )
            seen[key] = rec  # last-wins 去重

        records.extend(seen.values())
        return records
