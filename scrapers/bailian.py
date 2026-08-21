"""阿里云百炼（国内站 cn-beijing）模型调用计费解析器（CNY）。

数据源：https://help.aliyun.com/help/json/document_detail.json?alias=%2Fmodel-studio%2Fmodel-pricing
  &pageNum=1&pageSize=20&website=cn&language=zh

对应控制台入口：
  https://bailian.console.aliyun.com/cn-beijing?tab=doc#/doc/?type=model&url=2987148
  （doc id 2987148 = /model-studio/model-pricing）

该 JSON 接口返回文档全文 HTML（data.content），内含 274 张定价表，单位为「元/百万 tokens」。
控制台 SPA 自身不服务端渲染价格表，故直连此 JSON 接口抓取。

DeepSeek 来源类型区分：
- 页面上 DeepSeek 模型行无「原厂直供」标记 → 阿里云自部署。
- 非 DeepSeek 模型（GLM / Kimi / MiniMax）condition=None。

解析规则：
- 仅取模型 ID 命中目标家族（deepseek / glm / kimi / minimax）的行；
  Qwen 系列由 aliyun（Hologres）源负责，此处排除。
- 跳过「国际 / 美国 / 日本」区域行，仅保留国内（全球 / 大陆，无区域标记或「全球」）价。
- 模型 ID 去噪：剥离 kimi/ 与 MiniMax/ 命名空间前缀、日期快照（-2026-xx-xx）、
  -us / -preview / -exp / -fast / -highspeed 后缀，取基准名
  （如 deepseek-v4-flash、MiniMax-M3、kimi-k3）。
- 价格列：取行内形如「数字元」的两个单元格（输入 / 输出）。
- 缓存命中价按用户给定规则 = 输入单价 × 0.2 计算
  （页面仅标注「上下文缓存享有折扣」，未给具体数值；此比率是估算值，非页面返回的明确数据）。
  站点渲染时该值仅作参考，跨源比价时以其他明确标注缓存价的厂商源为准。
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from scrapers.base import BaseScraper, clean_price

# 后缀清洗：日期快照 / 短快照号 / 区域或预览标记
_SUFFIX = re.compile(r"-(?:\d{4}-\d{2}-\d{2}|\d{4}|us|preview|exp|fast|highspeed)$", re.IGNORECASE)
_OVERSEAS_MARK = ("国际", "美国", "日本")
_TARGET_PREFIX = ("deepseek", "glm", "kimi", "minimax")
# 严格匹配「数字元」价格单元格（排除「原价2元 限时8折」「100万Token」等）
_PRICE_CELL = re.compile(r"^\s*\d+(?:\.\d+)?\s*元\s*$")
# 用户给定：缓存命中 = 输入单价 × 20%
CACHE_HIT_RATIO = 0.2


def _norm_id(raw: str) -> Optional[str]:
    """模型 ID 去噪，返回基准名；非目标家族返回 None。"""
    if not raw:
        return None
    # 去掉命名空间前缀（kimi/ 、MiniMax/ 等）
    mid = raw.split("/")[-1].strip()
    # 取首个空白前基础名（去掉「上下文缓存享有折扣」等注释）
    mid = mid.split()[0].strip() if mid.split() else mid
    # 去日期 / 后缀
    while True:
        m = _SUFFIX.search(mid)
        if not m:
            break
        mid = _SUFFIX.sub("", mid)
    mid = mid.rstrip("-").lower()
    if not mid:
        return None
    if not any(mid.startswith(p) for p in _TARGET_PREFIX):
        return None
    return mid


class BailianScraper(BaseScraper):
    """解析阿里云百炼国内站模型调用计费（CNY）。"""

    def parse(self, html: str) -> List[Dict[str, Any]]:
        # 该源直连 JSON 接口，content 为 JSON 文本；兜底当普通 HTML 解析
        try:
            payload = json.loads(html)
            content = (payload.get("data") or {}).get("content") or ""
        except Exception:
            content = html

        from parsel import Selector

        sel = Selector(text=content)
        records: List[Dict[str, Any]] = []
        seen = set()

        for table in sel.css("table"):
            rows = table.css("tr")
            if len(rows) < 2:
                continue
            for row in rows[1:]:
                cells = [
                    c.xpath("string(.)").get(default="").strip().replace("​", "")
                    for c in row.css("td, th")
                ]
                if len(cells) < 3:
                    continue
                norm = _norm_id(cells[0])
                if not norm:
                    continue
                # 跳过海外区域行
                if any(mk in " ".join(cells) for mk in _OVERSEAS_MARK):
                    continue
                # 取形如「数字元」的价格单元格
                price_cells = [c for c in cells[1:] if _PRICE_CELL.match(c)]
                if len(price_cells) < 2:
                    continue
                inp = clean_price(price_cells[-2])
                out = clean_price(price_cells[-1])
                if inp is None and out is None:
                    continue
                if norm in seen:
                    continue
                seen.add(norm)
                cache = round(inp * CACHE_HIT_RATIO, 6) if inp is not None else None
                # DeepSeek 来源类型：页面无「原厂直供」标记 → 阿里云自部署
                if norm.startswith("deepseek"):
                    condition = "阿里云自部署"
                else:
                    condition = None
                records.append(
                    self._rec(
                        model_raw=norm,
                        input=round(inp, 6) if inp is not None else None,
                        output=round(out, 6) if out is not None else None,
                        cache_hit=cache,
                        context=None,
                        condition=condition,
                    )
                )
        return records
