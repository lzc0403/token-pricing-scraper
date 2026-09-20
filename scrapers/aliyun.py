"""阿里云 Hologres 托管模型 Token 定价解析器。

数据源：Hologres 托管模型计费页（中国站）。

2026-09 页面改版：文本模型主表由「9 列」精简为「6 列」——
  - 旧版（legacy）：地域 / 模型名称 / 模型类别 / 输入 Token 阶梯 / 输入单价 /
    显式缓存创建 / 显式缓存命中 / 隐式缓存命中 / 输出单价（共 5 个价格列）
  - 新版：地域 / 模型名称 / 模型类别 / 输入 Token 阶梯 / 输入单价 / 输出单价
    （仅 2 个价格列，缓存价不再单列）

新版把缓存价改为在同页「缓存计费说明」表中给出**与输入单价的比率**：

    显式缓存创建 | 输入单价 × 1.25
    显式缓存命中 | 输入单价 × 0.10
    隐式缓存命中 | 输入单价 × 0.20

解析规则（两种版式兼容）：
- 文本模型主表判定：表头同时含「模型名称」「输出单价」「千 Token」
  （借此排除 元/张、元/秒 的非 token 表与说明表）。
- legacy 表（表头含「隐式缓存命中」列）：缓存命中价直接取该列。
- 新版表（无缓存列）：缓存命中价 = 输入单价 × 隐式比率，比率从说明表解析；
  说明表缺失时回退默认 0.20（与改版前口径一致）。
- 仅取中国内地区域（地域列含 北京/上海/杭州/深圳）的行；跳过「新加坡」等海外区域。
- 站点统一以「元/百万 Token」展示，故「元/千 Token」值统一 ×1000。
- 仅保留主线模型 Qwen3.7-Max / Qwen3.7-Plus；
  Qwen3.7-Plus 有阶梯价（≤256K / 256K~1M），取基础阶梯 ≤256K。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from scrapers.base import BaseScraper, clean_price

# 中国内地城市（地域列出现其一即视为中国站）
_MAINLAND_CITIES = ("北京", "上海", "杭州", "深圳")
# 仅保留主线模型（与既有 aliyun 源覆盖范围一致）
_TARGET_PREFIXES = ("qwen3.7-max", "qwen3.7-plus")
# 元/千 Token -> 元/百万 Token
_K_PER_M = 1000.0
# 新版说明表中「隐式缓存命中 | 输入单价 × 0.20」的比率提取
_RATIO_RE = re.compile(r"[×xX*]\s*(\d+(?:\.\d+)?)")
# 说明表默认口径（页面未给比率时的兜底，与改版前硬编码一致）
_DEFAULT_IMPLICIT_RATIO = 0.20


class AliyunScraper(BaseScraper):
    """解析阿里云 Hologres 托管模型 Qwen 定价。"""

    def _parse_implicit_ratio(self, tables: List[Any]) -> Optional[float]:
        """从「缓存计费说明」表解析隐式缓存命中比率（输入单价 × 0.20 → 0.20）。"""
        for table in tables:
            rows = table.css("tr")
            if not rows:
                continue
            header = " ".join(
                c.xpath("string(.)").get(default="").strip() for c in rows[0].css("td, th")
            )
            if "与输入单价的关系" not in header:
                continue
            for row in rows[1:]:
                cells = [
                    c.xpath("string(.)").get(default="").strip() for c in row.css("td, th")
                ]
                if not cells:
                    continue
                label = cells[0]
                if "隐式缓存命中" not in label:
                    continue
                m = _RATIO_RE.search(" ".join(cells[1:]))
                if m:
                    return float(m.group(1))
        return None

    def parse(self, html: str) -> List[Dict[str, Any]]:
        from parsel import Selector

        sel = Selector(text=html)
        tables = sel.css("table")
        implicit_ratio = self._parse_implicit_ratio(tables)
        if implicit_ratio is None:
            implicit_ratio = _DEFAULT_IMPLICIT_RATIO

        records: List[Dict[str, Any]] = []
        seen: set = set()
        current_mainland = False

        for table in tables:
            rows = table.css("tr")
            if not rows:
                continue
            # 仅处理文本模型主表：表头须含「模型名称」「输出单价」「千 Token」
            header = [c.xpath("string(.)").get(default="").strip()
                      for c in rows[0].css("td, th")]
            hj = " ".join(header)
            if "模型名称" not in hj or "输出单价" not in hj or "千 Token" not in hj:
                continue
            # legacy 版式：缓存命中价单列（隐式缓存命中）
            legacy = "隐式缓存命中" in hj

            for row in rows[1:]:
                cells = [c.xpath("string(.)").get(default="").strip()
                         for c in row.css("td, th")]
                if not cells:
                    continue
                first = cells[0]
                # 地域行：单单元格含城市名（与首个模型同行，需剥离该单元格）
                is_region = (any(c in first for c in _MAINLAND_CITIES)
                             or "新加坡" in first)
                if is_region:
                    current_mainland = any(c in first for c in _MAINLAND_CITIES)
                    cells = cells[1:]  # 剥离地域单元格，余下为模型数据
                if not current_mainland:
                    continue
                if not cells:
                    continue

                # 模型名位于数据首列；非目标模型（含阶梯续行）直接跳过
                model_name = cells[0]
                low = model_name.lower()
                if not any(low.startswith(p) for p in _TARGET_PREFIXES):
                    continue

                if legacy:
                    # 旧版：价格恒为末 5 列 [输入, 显式创建, 显式命中, 隐式命中, 输出]
                    if len(cells) < 6:
                        continue
                    tier = cells[-6]
                    if "256K~1M" in tier:
                        continue
                    prices = cells[-5:]
                    inp = clean_price(prices[0])
                    implicit = clean_price(prices[3])
                    outp = clean_price(prices[4])
                else:
                    # 新版：价格恒为末 2 列 [输入, 输出]，缓存价按比率换算
                    if len(cells) < 3:
                        continue
                    tier = cells[-3]
                    if "256K~1M" in tier:
                        continue
                    inp = clean_price(cells[-2])
                    outp = clean_price(cells[-1])
                    implicit = (
                        round(inp * implicit_ratio, 6) if inp is not None else None
                    )

                base = "qwen3.7-max" if low.startswith("qwen3.7-max") else "qwen3.7-plus"
                if base in seen:
                    continue
                seen.add(base)

                rec = self._rec(
                    model_raw=model_name,
                    input=round(inp * _K_PER_M, 4) if inp is not None else None,
                    output=round(outp * _K_PER_M, 4) if outp is not None else None,
                    # 缓存命中价：legacy 取「隐式缓存命中」列；新版按比率换算
                    cache_hit=round(implicit * _K_PER_M, 4) if implicit is not None else None,
                    context=None,
                    condition=None,
                )
                records.append(rec)
        return records
