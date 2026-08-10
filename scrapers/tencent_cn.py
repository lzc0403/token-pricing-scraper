"""腾讯云国内站 TokenHub 模型价格解析器（CNY）。

数据源：https://cloud.tencent.com/document/product/1823/130055
（腾讯云大模型服务平台 TokenHub 模型价格，国内站，CNY）

该页为 SPA，config 中 js: true 由 Playwright 渲染。语言模型定价表表头含
「推理输入（元/百万 tokens）」「推理输出（元/百万 tokens）」「缓存命中（元/百万 tokens）」。
同一模型分「原厂直供」与「腾讯云自建」两档，用 condition 字段区分：

- 「原厂直供」是模型名带后缀的行（如 ``DeepSeek-V4-Flash 正式版 原厂直供``）。
- 「腾讯云自建」是同名、无后缀的行（如 ``DeepSeek-V4-Flash``）；
  「腾讯云自建」这四个字本身并不出现在任何单元格里，因此不能用作文本过滤。

解析规则：
- 仅处理表头同时含「推理输入」「推理输出」「缓存命中」的语言模型定价表。
- 仅取**含「原厂直供」行**的表（即完整定价表；概览表不含原厂直供两档，价格也与
  完整表不一致，例如 GLM 概览 8/28 vs 完整表 10.254/32.2282，故跳过以免歧义）。
- 模型名：去掉「正式版 / 原厂直供 / 腾讯云自建 / HighSpeed / Preview /（…下线…）」等
  注释，**保留多词名**（如 ``Kimi K3``、``Kimi K2.7 Code``，不可截断为单词）。
- 档位（condition）判定：先扫描本表带「原厂直供」的模型基础名集合 `factory`；
  某行若含「原厂直供」→ ``"原厂直供"``；若其基础名在 `factory` 中（同名无后缀行）
  → ``"腾讯云自建"``；否则 ``None``（单档模型，如 GLM-5.2 / Kimi K3）。
- 按 (基础模型名, condition) 去重，后到覆盖（完整表位于文档较后，其官方最新价
  覆盖前面的概览表，避免概览表的偏低价胜出）。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from scrapers.base import BaseScraper, clean_price

# 模型名注释清洗：去掉中文/英文档位与下线标记，但保留真实多词模型名
_ANNOT_RE = re.compile(
    r"(正式版|原厂直供|腾讯云自建|HighSpeed|Highspeed|Preview|preview|（[^）]*）)",
    re.IGNORECASE,
)


def _base_name(raw: str) -> str:
    """剥离注释得到基础模型名，保留多词名（如 'Kimi K3'）。"""
    base = _ANNOT_RE.sub(" ", raw)
    base = re.sub(r"\s+", " ", base).strip().rstrip("-").strip()
    return base


class TencentCnScraper(BaseScraper):
    """解析腾讯云国内站 TokenHub 语言模型价格表（CNY）。"""

    def parse(self, html: str) -> List[Dict[str, Any]]:
        from parsel import Selector

        sel = Selector(text=html)
        records: List[Dict[str, Any]] = []
        seen: Dict[tuple, Dict[str, Any]] = {}

        for table in sel.css("table"):
            header_cells = [
                c.xpath("string(.)").get(default="").strip()
                for c in table.css("tr:first-child td,th")
            ]
            hj = " ".join(header_cells)
            if "推理输入" not in hj or "推理输出" not in hj or "缓存命中" not in hj:
                continue

            # 仅取含「原厂直供」行的完整定价表（跳过概览表/单档表）
            table_text = " ".join(
                c.xpath("string(.)").get(default="").strip()
                for c in table.css("tr td, tr th")
            )
            if "原厂直供" not in table_text:
                continue

            # 按列头动态定位价格列下标（不写死列序，抗表头变动）
            idx_in = next((i for i, h in enumerate(header_cells) if "推理输入" in h), None)
            idx_out = next((i for i, h in enumerate(header_cells) if "推理输出" in h), None)
            idx_cache = next((i for i, h in enumerate(header_cells) if "缓存命中" in h), None)
            if idx_in is None or idx_out is None or idx_cache is None:
                continue

            # 先扫描：本表中哪些基础名存在「原厂直供」变体
            factory: set = set()
            for row in table.css("tr")[1:]:
                rc = [
                    c.xpath("string(.)").get(default="").strip().replace("​", "")
                    for c in row.css("td,th")
                ]
                if not rc:
                    continue
                name = rc[0].strip()
                if "原厂直供" in name:
                    factory.add(_base_name(name).lower())

            for row in table.css("tr")[1:]:
                cells = [
                    c.xpath("string(.)").get(default="").strip().replace("​", "")
                    for c in row.css("td, th")
                ]
                if len(cells) <= max(idx_in, idx_out, idx_cache):
                    continue
                raw = cells[0].strip()
                if not raw or raw == "﻿":
                    continue

                base = _base_name(raw)
                if not base:
                    continue

                # 档位判定
                if "原厂直供" in raw:
                    cond = "原厂直供"
                elif base.lower() in factory:
                    cond = "腾讯云自建"
                else:
                    cond = None

                inp = clean_price(cells[idx_in])
                out = clean_price(cells[idx_out])
                cache = clean_price(cells[idx_cache])
                if inp is None and out is None:
                    continue

                key = (base.lower(), cond)
                # last-wins：完整定价表（含原厂直供两档、官方最新价）通常位于文档
                # 较后位置，会覆盖前面的概览表（如 GLM-5.2 概览 8/28 vs 完整表
                # 10.254/32.2282），避免概览表的偏低价覆盖完整价。
                seen[key] = self._rec(
                    model_raw=base,
                    input=round(inp, 6) if inp is not None else None,
                    output=round(out, 6) if out is not None else None,
                    cache_hit=round(cache, 6) if cache is not None else None,
                    context=None,
                    condition=cond,
                )

        records.extend(seen.values())
        return records
