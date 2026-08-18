"""智谱 Z.ai 国际站（海外，USD 结算）模型定价解析器。

数据源：https://docs.z.ai/guides/overview/pricing
（Z.AI DEVELOPER DOCUMENT，官方定价页，全站 USD）

页面含多张表：
- table 0：Text Models，表头 `Model | Input | Cached Input | Cached Input Storage | Output`
- 其余：Vision / Tools / Image / Video / Audio / Agents，均非文本 LLM 定价，忽略。

只取文本模型表（表头含 Model + Input + Output 且 Input 列值为美元价格）。
价格为美元（USD）/ 百万 tokens。

收录范围：GLM 系列文本模型（GLM-5.2 / 5.1 / 5 / 5-Turbo / 4.7 / 4.6 / 4.5 / 4.5-Air 等）。
GLM-5.3 目前仅 GLM Coding Plan 订阅提供，标准 API 未开放，定价页无 → 抓不到属正常，
如后续上线会自动收录。

GLM 系列 condition 留空（无来源类型区分，价格即智谱官方国际站原价）。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from scrapers.base import BaseScraper, clean_price


class ZaiScraper(BaseScraper):
    """解析 docs.z.ai 官方定价页的文本模型表（USD）。"""

    def parse(self, html: str) -> List[Dict[str, Any]]:
        from parsel import Selector

        sel = Selector(text=html)
        records: List[Dict[str, Any]] = []

        for table in sel.css("table"):
            header_cells = [
                c.xpath("string(.)").get(default="").strip()
                for c in table.css("tr:first-child td,th")
            ]
            hj = " ".join(header_cells).lower()
            # 只处理文本模型表：含 Model + Input + Output 三个关键列
            if "model" not in hj or "input" not in hj or "output" not in hj:
                continue
            # 定位列索引
            i_model = i_input = i_cache = i_output = -1
            for idx, h in enumerate(header_cells):
                hl = h.strip().lower()
                if hl == "model":
                    i_model = idx
                elif hl == "input":
                    i_input = idx
                elif hl == "cached input":
                    i_cache = idx
                elif hl == "output":
                    i_output = idx
            if i_model < 0 or i_input < 0 or i_output < 0:
                continue

            for row in table.css("tr")[1:]:
                cells = [
                    c.xpath("string(.)").get(default="").strip()
                    for c in row.css("td,th")
                ]
                if len(cells) <= max(i_model, i_input, i_cache, i_output):
                    continue
                raw_model = cells[i_model].strip()
                if not raw_model or raw_model.lower() == "model":
                    continue
                # 仅收录 GLM 文本系列
                if not raw_model.lower().startswith("glm"):
                    continue
                inp = clean_price(cells[i_input])
                out = clean_price(cells[i_output])
                cache = clean_price(cells[i_cache]) if i_cache >= 0 else None
                if inp is None and out is None:
                    continue
                # 跳过视觉模型（GLM-5V / GLM-4.6V 等带 V 后缀的）
                if _is_vision(raw_model):
                    continue
                records.append(
                    self._rec(
                        model_raw=raw_model,
                        input=inp,
                        output=out,
                        cache_hit=cache,
                        context=None,
                        condition=None,
                    )
                )

        return records


def _is_vision(name: str) -> bool:
    """GLM 视觉/OCR 模型（GLM-5V / GLM-4.6V / GLM-4.5V / GLM-4.6V-FlashX / GLM-OCR）应排除。

    识别规则：模型名含 `glm-<数字>v` 模式（如 glm-5v、glm-4.6v、glm-4.5v）或含 `ocr`。
    假设：智谱视觉模型命名遵循 `GLM-<版本号>V` 约定（V 紧跟数字版本号）。
    GLM-4.5-X 等文本模型不受影响（X 不匹配 `\\d+v`）。
    """
    low = (name or "").lower()
    if "ocr" in low:
        return True
    # glm-5v / glm-4.6v / glm-4.5v / glm-4.6v-flashx
    return bool(re.search(r"glm-\d+(?:\.\d+)?v", low))
