"""阿里云 Model Studio 国际站（新加坡 ap-southeast-1）Token 定价解析器。

数据源：https://modelstudio.console.alibabacloud.com/ap-southeast-1?tab=doc#/doc/?type=model&url=prices
SPA 控制台，需 Playwright 渲染（config 中 js: true）。

页面含多张定价表，表头同时含「Input Price」「Output Price」「Implicit Cache Hit」，
单位为「美元 / 百万 tokens」。模型含 Qwen（阿里云自有）与 DeepSeek / Kimi / GLM（转售）。

解析规则：
- 仅抓取表头含「Input Price」+「Output Price」+「Implicit Cache Hit」的定价表。
- 列序固定：Model(0) | Input Token Range(1) | Mode(2) | Input Price(3) |
  Output Price(4) | Input Price (Implicit Cache Hit)(5) | Explicit Creation(6) | Explicit Hit(7)。
- 模型名去噪：剥离日期快照后缀（-2026-05-26）、-preview、-0731 等；
  优先保留无后缀的基准名（如 deepseek-v4-flash 而非 deepseek-v4-flash-0731）。
- 同一模型的分档续行（如 qwen3.7-plus 的 256k~1M）只保留首行（基准档 Input<=256k）。
- 跳过 -preview 预览模型。
- 全部为 USD / 百万 tokens（与国内站 CNY 区分）。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from scrapers.base import BaseScraper, clean_price

# 后缀清洗：日期快照 / preview / 短快照号
_SUFFIX_RE = re.compile(r"-(?:preview|\d{4}-\d{2}-\d{2}|\d{4})$", re.IGNORECASE)


def _normalize(name: str) -> str:
    """模型名去噪，返回基准名（用于去重）。"""
    n = (name or "").strip().lower()
    # 去掉可能的链接尾噪
    n = n.split("(")[0].strip()
    while True:
        m = _SUFFIX_RE.search(n)
        if not m:
            break
        n = _SUFFIX_RE.sub("", n)
    return n


class AliyunIntlScraper(BaseScraper):
    """解析阿里云国际站 Model Studio 定价表（USD）。"""

    def parse(self, html: str) -> List[Dict[str, Any]]:
        from parsel import Selector

        sel = Selector(text=html)
        records: List[Dict[str, Any]] = []

        for table in sel.css("table"):
            header_cells = [
                c.xpath("string(.)").get(default="").strip()
                for c in table.css("tr:first-child td,th")
            ]
            hj = " ".join(header_cells)
            # 只处理含输入/输出/隐式缓存命中的定价表
            if "Input Price" not in hj or "Output Price" not in hj or "Implicit Cache Hit" not in hj:
                continue

            for row in table.css("tr")[1:]:
                cells = [
                    c.xpath("string(.)").get(default="").strip().replace("​", "")
                    for c in row.css("td,th")
                ]
                if len(cells) < 8:
                    continue
                raw_model = cells[0].strip()
                if not raw_model or raw_model in ("--",):
                    continue
                low = raw_model.lower()
                # 跳过预览模型
                if "preview" in low:
                    continue
                norm = _normalize(raw_model)
                if not norm:
                    continue
                inp = clean_price(cells[3])
                out = clean_price(cells[4])
                cache = clean_price(cells[5])
                if inp is None and out is None:
                    continue
                records.append(
                    {
                        "norm": norm,
                        "raw": raw_model,
                        "input": round(inp, 6) if inp is not None else None,
                        "output": round(out, 6) if out is not None else None,
                        "cache_hit": round(cache, 6) if cache is not None else None,
                    }
                )

        # 去重：同一 norm 只保留「无后缀基准名」的那条；其余（快照/分档续行）丢弃
        best: Dict[str, Dict[str, Any]] = {}
        for rec in records:
            norm = rec["norm"]
            existing = best.get(norm)
            if existing is None:
                best[norm] = rec
                continue
            # 优先无后缀（raw 不含 -日期/-preview/-数字快照）
            if _is_base(rec["raw"]) and not _is_base(existing["raw"]):
                best[norm] = rec

        out: List[Dict[str, Any]] = []
        for rec in best.values():
            out.append(
                self._rec(
                    model_raw=rec["norm"],
                    input=rec["input"],
                    output=rec["output"],
                    cache_hit=rec["cache_hit"],
                    context=None,
                    condition="阿里云国际站 Model Studio (ap-southeast-1)",
                )
            )
        return out


def _is_base(raw: str) -> bool:
    return not bool(_SUFFIX_RE.search((raw or "").lower()))
