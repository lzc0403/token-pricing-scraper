"""小米 MiMo 开放平台 API 定价解析器。

数据源：https://platform.xiaomimimo.com/docs/zh-CN/pricing（国内 CNY）
        https://platform.xiaomimimo.com/docs/en-US/pricing（海外 USD）

页面为 SPA（`<div id="root">`），静态 HTML 无价格 → sources.yml 配 `js: true`。

结构特点：**同一张页面内同时含「模型国内定价」(¥) 与「模型海外定价」($) 两张
文本模型表**，另有 ASR（按音频时长）与联网插件（按次）表。因此国内源与海外源
共用同一页面，靠**价格单元格的货币符号**分流：

  - `mimo`（currency: CNY）只取 ¥ 表
  - `mimo_intl`（currency: USD）只取 $ 表

表结构（4 列，首行既是分组名也是列名）：

    MiMo-V2.5 系列 | 输入（命中缓存） | 输入（未命中缓存） | 输出
    mimo-v2.5-pro  | ¥0.025          | ¥3.00             | ¥6.00
    mimo-v2.5      | ¥0.02           | ¥1.00             | ¥2.00

  英文站表头为 MiMo-V2.5 Series / Input (Cache Hit) / Input (Cache Miss) / Output。

取数口径：
- 原页面即为「元（美元）/ 百万 tokens」，与站点统一口径一致，**不做换算**。
- `cache_hit` 取「输入（命中缓存）」列；`input` 取「输入（未命中缓存）」列。
- 缓存写入官网标注「限时免费」，`cache_write` 恒为 None。
- 仅收 `mimo-v2.5` / `mimo-v2.5-pro` 两个文本模型（ASR 按小时、TTS 限时免费，
  均非 token 计价，跳过）。
"""

from __future__ import annotations

from typing import Any, Dict, List

from scrapers.base import BaseScraper, clean_price

# 目标文本模型前缀（ASR / TTS 系列不按 token 计价，排除）
_TARGET_PREFIX = "mimo-v2.5"
# 表头特征：必须同时出现「输出」列与「命中缓存」列的文本定价表
_HEADER_OUTPUT = ("输出", "output")
_HEADER_CACHE_HIT = ("命中缓存", "cache hit")


def _is_text_table(header: List[str]) -> bool:
    """判断是否为 MiMo-V2.5 文本定价表（4 列且含缓存命中 / 输出列）。"""
    if len(header) != 4:
        return False
    joined = " ".join(header).lower()
    has_output = any(token.lower() in joined for token in _HEADER_OUTPUT)
    has_cache = any(token.lower() in joined for token in _HEADER_CACHE_HIT)
    return has_output and has_cache


class MimoScraper(BaseScraper):
    """解析小米 MiMo 开放平台 API 定价（国内 ¥ / 海外 $ 同页分流）。"""

    def parse(self, html: str) -> List[Dict[str, Any]]:
        from parsel import Selector

        sel = Selector(text=html)
        want_usd = str(self.currency).upper() == "USD"
        records: List[Dict[str, Any]] = []
        seen: set = set()

        for table in sel.css("table"):
            rows = table.css("tr")
            if len(rows) < 2:
                continue
            header = [
                c.xpath("string(.)").get(default="").strip().replace("\u200b", "")
                for c in rows[0].css("td, th")
            ]
            if not _is_text_table(header):
                continue

            for row in rows[1:]:
                cells = [
                    c.xpath("string(.)").get(default="").strip().replace("\u200b", "")
                    for c in row.css("td, th")
                ]
                if len(cells) < 4:
                    continue
                model = cells[0].strip()
                if not model.lower().startswith(_TARGET_PREFIX):
                    continue

                cache_raw, input_raw, output_raw = cells[1], cells[2], cells[3]
                # 同页两表靠货币符号分流：¥ 表归国内源，$ 表归海外源
                is_usd = "$" in "".join((cache_raw, input_raw, output_raw))
                if is_usd != want_usd:
                    continue

                # 同一模型可能在多张表重复出现（如「全球」「国际」分片），按源内去重
                key = model.lower()
                if key in seen:
                    continue
                seen.add(key)

                records.append(
                    self._rec(
                        model_raw=model,
                        input=clean_price(input_raw),
                        output=clean_price(output_raw),
                        cache_hit=clean_price(cache_raw),
                        context=None,
                        condition=None,
                    )
                )
        return records
