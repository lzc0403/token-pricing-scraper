"""阿里云 Model Studio 国际站（新加坡 ap-southeast-1）Token 定价解析器。

数据源：https://modelstudio.console.alibabacloud.com/ap-southeast-1?tab=doc#/doc/?type=model&url=prices
SPA 控制台，需 Playwright 渲染（config 中 js: true）。

页面含多张定价表，表头同时含「Input Price」「Output Price」「Implicit Cache Hit」，
单位为「美元 / 百万 tokens」。模型含 Qwen（阿里云自有）与 DeepSeek / Kimi / GLM（转售）。

DeepSeek 来源类型区分（与 tencent.py 同规则）：
- 页面上 DeepSeek 模型行无「原厂直供」标记 → 阿里云自部署。
  「阿里云自部署」字样不在页面上出现，是依据「未标原厂直供即自部署」规则判定。
- 非 DeepSeek 模型（如 Qwen、Kimi、GLM）condition 保留原区域标签。

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
            # 表结构：含 Time Period 列为峰谷表，列序整体右移一位
            has_peak = "Time Period" in hj
            if has_peak:
                col_in, col_out, col_cache, col_peak = 4, 5, 6, 3
            else:
                col_in, col_out, col_cache, col_peak = 3, 4, 5, None

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
                inp = clean_price(cells[col_in])
                out = clean_price(cells[col_out])
                cache = clean_price(cells[col_cache])
                if inp is None and out is None:
                    continue
                peak = cells[col_peak].strip() if col_peak is not None and col_peak < len(cells) else None
                records.append(
                    {
                        "norm": norm,
                        "raw": raw_model,
                        "input": round(inp, 6) if inp is not None else None,
                        "output": round(out, 6) if out is not None else None,
                        "cache_hit": round(cache, 6) if cache is not None else None,
                        "peak": peak,
                        "has_peak": has_peak,
                    }
                )

        # 按 norm 分组：同一 norm 下，若同时存在「空闲/高峰」双行，合并为单行峰谷记录；
        # 若只有单行，直接保留。峰谷版优先于无输入价的普通版。
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for rec in records:
            groups.setdefault(rec["norm"], []).append(rec)

        merged: List[Dict[str, Any]] = []
        for items in groups.values():
            peak_rows = [r for r in items if r.get("peak") in ("Off-peak", "Peak")]
            other_rows = [r for r in items if r not in peak_rows]
            if len(peak_rows) >= 2:
                by_peak = {r["peak"]: r for r in peak_rows}
                if "Off-peak" in by_peak and "Peak" in by_peak:
                    low, high = by_peak["Off-peak"], by_peak["Peak"]
                    merged.append(
                        {
                            "norm": low["norm"],
                            "raw": low["raw"],
                            "input": high["input"],
                            "output": high["output"],
                            "cache_hit": high["cache_hit"],
                            "peak_input_low": low["input"],
                            "peak_input_high": high["input"],
                            "peak_output_low": low["output"],
                            "peak_output_high": high["output"],
                            "peak_cache_low": low["cache_hit"],
                            "peak_cache_high": high["cache_hit"],
                            "condition_extra": "峰谷计费",
                        }
                    )
                    continue
            # 无峰谷或峰谷不完整：优先保留有输入价、来自峰谷表、无后缀基准名的记录
            def _score(rec: Dict[str, Any]) -> tuple:
                has_in = rec["input"] is not None
                is_peak = rec.get("has_peak")
                is_base = _is_base(rec["raw"])
                return (has_in, is_peak, is_base)

            candidates = peak_rows if peak_rows else other_rows
            best = sorted(candidates, key=_score, reverse=True)[0]
            merged.append({"condition_extra": None, **best})

        out: List[Dict[str, Any]] = []
        for rec in merged:
            norm = rec["norm"]
            parts = []
            if norm.startswith("deepseek"):
                parts.append("阿里云自部署")
            if rec.get("condition_extra"):
                parts.append(rec["condition_extra"])
            condition = " | ".join(parts) if parts else None
            rec_out = self._rec(
                model_raw=rec["norm"],
                input=rec["input"],
                output=rec["output"],
                cache_hit=rec["cache_hit"],
                context=None,
                condition=condition,
            )
            # 透传峰谷字段
            for k in ["peak_input_low", "peak_input_high", "peak_output_low", "peak_output_high", "peak_cache_low", "peak_cache_high"]:
                if k in rec:
                    rec_out[k] = rec[k]
            out.append(rec_out)
        return out


def _is_base(raw: str) -> bool:
    return not bool(_SUFFIX_RE.search((raw or "").lower()))
