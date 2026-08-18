"""BytePlus ModelArk 海外站（火山云海外）Token 定价解析器。

数据源：https://docs.byteplus.com/en/docs/ModelArk/1544106
SPA 文档，需 Playwright 渲染（config 中 js: true）。

页面含多张定价表，本解析器只处理「Large language models — Online inference (standard)」表
（表头含 Model ID / Input (non-audio) / Cache-hit input (non-audio) / Output）。
价格为「美元 / 百万 tokens」，与国内火山引擎（CNY）区分展示。

收录范围：DeepSeek + GLM 系列。
- DeepSeek：deepseek-v4-pro / deepseek-v4-flash / deepseek-v3-2
- GLM：glm-5-2 / glm-4-7

模型名归一化：剥离日期快照后缀（-260425 / -251201 / -260617 / -251222），
复用 aliyun_intl.py 的 _SUFFIX_RE 模式，返回无后缀基准名。

DeepSeek 来源类型标注（与 aliyun_intl / bailian 同规则）：
- BytePlus 页面无「原厂直供」标记 → 火山引擎自部署。
  「火山引擎自部署」字样不在页面上出现，是依据「未标原厂直供即自部署」规则判定。
- GLM 等 non-DeepSeek 模型 condition 留空（区域信息已由 SOURCE_LABELS「火山云海外」表达）。

分层定价处理：
- 同一模型可能有多行（如 deepseek-v3-2 的 [0,32] / (32,128]），只保留首行（基准档）。
- 无 tier 标记（Pricing tiers 列为 "-"）的模型直接取该行价格。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from scrapers.base import BaseScraper, clean_price

# 后缀清洗：日期快照（6 位 YYMMDD / 8 位 YYYY-MM-DD / 4 位 YYMM）/ preview / GA 日期快照
# BytePlus 用 6 位日期（-260425/-251201/-260617/-251222）与 GA 版本（deepseek-v4-flash-ga-260731）
# aliyun_intl 用 8 位（-2026-05-26）。GA 版剥离 -ga-日期 后归一到无后缀基准名
_DATE = r"(?:\d{4}-\d{2}-\d{2}|\d{6}|\d{4})"
# 日期快照：-260425 / -251201；GA 版：-ga-260731（剥离后归一无后缀基准名）
_SUFFIX_RE = re.compile(r"-" + _DATE + r"$", re.IGNORECASE)
_GA_SUFFIX_RE = re.compile(r"-ga-" + _DATE + r"$", re.IGNORECASE)

# 版本号「-」转「.」：BytePlus 用 glm-5-2 / deepseek-v3-2（- 替代 .），
# 归一到 models.yml 的标准 alias 形式 glm-5.2 / deepseek-v3.2
_VERSION_DASH_RE = re.compile(r"^(deepseek-v\d+|glm-\d+)-(\d+)$")


def _normalize(name: str) -> str:
    """模型名去噪，返回基准名（用于去重与 matcher 匹配）。"""
    n = (name or "").strip().lower()
    n = n.split("(")[0].strip()
    while True:
        # 先剥 GA 日期后缀（-ga-260731 → 空），再剥普通日期后缀，循环到无残留
        m_ga = _GA_SUFFIX_RE.search(n)
        if m_ga:
            n = _GA_SUFFIX_RE.sub("", n)
            continue
        m = _SUFFIX_RE.search(n)
        if not m:
            break
        n = _SUFFIX_RE.sub("", n)
    # 版本号「-」转「.」：glm-5-2 → glm-5.2，deepseek-v3-2 → deepseek-v3.2
    n = _VERSION_DASH_RE.sub(r"\1.\2", n)
    return n


def _is_base(raw: str) -> bool:
    low = (raw or "").lower()
    return not bool(_SUFFIX_RE.search(low) or _GA_SUFFIX_RE.search(low))


class VolcengineIntlScraper(BaseScraper):
    """解析 BytePlus ModelArk 海外站定价表（USD）。"""

    def parse(self, html: str) -> List[Dict[str, Any]]:
        from parsel import Selector

        sel = Selector(text=html)
        records: List[Dict[str, Any]] = []

        for table in sel.css("table"):
            header_cells = [
                c.xpath("string(.)").get(default="").strip()
                .replace("\n", " ")  # 真实页面表头跨行（Input\n(non-audio)\n(USD/M tokens)），归一为空格
                .replace("\u200b", "")
                for c in table.css("tr:first-child td,th")
            ]
            hj = " ".join(header_cells)
            # 真实页面表头是无空格拼接（Input(non-audio)(USD/M tokens)），
            # 归一为「去所有空格」的紧凑串再匹配，避免空格差异导致误跳过
            hjc = hj.replace(" ", "").lower()
            # 只处理「在线推理标准」表：含 Model ID + Input (non-audio) + Cache-hit + Output
            if "modelid" not in hjc:
                continue
            if "input(non-audio)" not in hjc and "input(non-audio)(usd/mtokens)" not in hjc:
                continue
            if "output" not in hjc:
                continue
            # 跳过「批量推理」表（其 Input 列名是「Input (USD / M tokens)」无 non-audio 后缀）
            # 跳过视频生成表（无 Input/Output 命名列）
            if "cache-hitinput(non-audio)" not in hjc and "cache-hitinput(non-audio)(usd/mtokens)" not in hjc:
                continue

            # 列定位：注意「Cache-hit input (non-audio)」也含「input (non-audio)」，
            # 必须先排除 cache-hit 开头的列，否则 i_input 会被 cache 列覆盖
            i_model = -1
            i_input = -1
            i_cache = -1
            i_output = -1
            for idx, h in enumerate(header_cells):
                hl = h.lower().replace(" ", "").replace("\u200b", "")
                if hl.startswith("modelid"):
                    i_model = idx
                elif hl.startswith("cache-hit"):
                    # 任何 cache-hit 开头的列都归 cache
                    if "non-audio" in hl or "audio" not in hl:
                        i_cache = idx
                elif "input(non-audio)" in hl:
                    i_input = idx
                elif hl.startswith("output"):
                    i_output = idx
            if i_model < 0 or i_input < 0 or i_output < 0:
                continue

            for row in table.css("tr")[1:]:
                cells = [
                    c.xpath("string(.)").get(default="").strip().replace("​", "")
                    for c in row.css("td,th")
                ]
                if len(cells) <= max(i_model, i_input, i_cache, i_output):
                    continue
                raw_model = cells[i_model].strip()
                if not raw_model or raw_model in ("--",):
                    continue
                low = raw_model.lower()
                # 跳过预览模型
                if "preview" in low:
                    continue
                norm = _normalize(raw_model)
                if not norm:
                    continue
                # 仅保留 DeepSeek + GLM 系列
                if not (norm.startswith("deepseek") or norm.startswith("glm")):
                    continue
                inp = clean_price(cells[i_input]) if i_input >= 0 else None
                out = clean_price(cells[i_output]) if i_output >= 0 else None
                cache = clean_price(cells[i_cache]) if i_cache >= 0 else None
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

        # 去重：同一 norm 只保留首行（基准档，Input 最低档）。
        # BytePlus 页面分层续行按出现顺序排列（[0,32] 在前，(32,128] 在后），
        # 首行即为基准档；保留首行即可。无后缀基准名优先仅用于 raw 不同 norm 相同的极端情况。
        best: Dict[str, Dict[str, Any]] = {}
        for rec in records:
            norm = rec["norm"]
            if norm not in best:
                best[norm] = rec
                continue
            # 仅当现有记录是带后缀 raw 而新记录是无后缀 raw 时覆盖（极罕见）
            existing = best[norm]
            if _is_base(rec["raw"]) and not _is_base(existing["raw"]):
                best[norm] = rec

        out: List[Dict[str, Any]] = []
        for rec in best.values():
            norm = rec["norm"]
            # DeepSeek 来源类型：页面无「原厂直供」标记 → 火山引擎自部署；
            # GLM 等 non-DeepSeek 模型 condition 留空
            condition = "火山引擎自部署" if norm.startswith("deepseek") else None
            out.append(
                self._rec(
                    model_raw=rec["norm"],
                    input=rec["input"],
                    output=rec["output"],
                    cache_hit=rec["cache_hit"],
                    context=None,
                    condition=condition,
                )
            )
        return out
