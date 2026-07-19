"""阿里云 Hologres 托管模型 Token 定价解析器。

数据源：Hologres 托管模型计费页（中国站），以单表五列直接列出：
输入单价 / 显式缓存创建 / 显式缓存命中 / 隐式缓存命中 / 输出单价，
单位为「元/千 Token」。

解析规则：
- 仅取「中国内地」区域（地域列含 北京/上海/杭州/深圳）的行；跳过「新加坡」等海外区域。
- 地域列与首个模型同行（rowspan），解析时剥离地域单元格后取模型数据。
- 缓存命中只取「隐式缓存命中」列（用户指定），不取显式缓存命中 / 显式缓存创建。
- 站点统一以「元/百万 Token」展示，故提取的「元/千 Token」值统一 ×1000。
- 仅保留与原 aliyun 源一致的主线模型 Qwen3.7-Max / Qwen3.7-Plus；
  Qwen3.7-Plus 有阶梯价（≤256K / 256K~1M），取基础阶梯 ≤256K。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from scrapers.base import BaseScraper, clean_price

# 中国内地城市（地域列出现其一即视为中国站）
_MAINLAND_CITIES = ("北京", "上海", "杭州", "深圳")
# 仅保留与原 aliyun 源一致的主线模型
_TARGET_PREFIXES = ("qwen3.7-max", "qwen3.7-plus")
# 元/千 Token -> 元/百万 Token
_K_PER_M = 1000.0


class AliyunScraper(BaseScraper):
    """解析阿里云 Hologres 托管模型 Qwen 定价。"""

    def parse(self, html: str) -> List[Dict[str, Any]]:
        from parsel import Selector

        sel = Selector(text=html)
        records: List[Dict[str, Any]] = []
        seen: set = set()
        current_mainland = False

        for table in sel.css("table"):
            rows = table.css("tr")
            if not rows:
                continue
            # 仅处理含五列定价的 Token 表：表头同时含「输入单价」与「隐式缓存命中」
            header = [c.xpath("string(.)").get(default="").strip()
                      for c in rows[0].css("td, th")]
            hj = " ".join(header)
            if "隐式缓存命中" not in hj or "输入单价" not in hj:
                continue

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
                # 五列价格恒为末 5 列；阶梯列为价格前的单元格
                if len(cells) < 6:
                    continue
                tier = cells[-6]
                # Qwen3.7-Plus 仅取基础阶梯 ≤256K，跳过 256K~1M 续行
                if "256K~1M" in tier:
                    continue
                base = "qwen3.7-max" if low.startswith("qwen3.7-max") else "qwen3.7-plus"
                if base in seen:
                    continue
                seen.add(base)

                prices = cells[-5:]
                inp = clean_price(prices[0])
                imp_hit = clean_price(prices[3])  # 隐式缓存命中（仅取此项）
                outp = clean_price(prices[4])
                rec = self._rec(
                    model_raw=model_name,
                    input=round(inp * _K_PER_M, 4) if inp is not None else None,
                    output=round(outp * _K_PER_M, 4) if outp is not None else None,
                    # 仅用隐式缓存命中价
                    cache_hit=round(imp_hit * _K_PER_M, 4) if imp_hit is not None else None,
                    context=None,
                    condition=None,
                )
                records.append(rec)
        return records
