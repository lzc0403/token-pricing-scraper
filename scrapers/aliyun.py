"""阿里云百炼 Token 定价解析器。

主 URL（billing-for-text-generation）当前已失效（404），因此自动回退到
`fallback_url`（model-pricing 总览页，含 Qwen3.7 系列）。该总览页把同一模型按
「服务部署范围」拆分为多张表（中国内地 / 全球 / 国际 / 美国 / 日本 …），本解析器
只取「中国内地」区域、且模型 ID 为 qwen3.7-max / qwen3.7-plus 的行。
价格为人民币（CNY），含「原价 N 元 限时 M 折」时由 clean_price 折算为折后价。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from scrapers.base import BaseScraper, clean_price

# 仅保留「中国内地」部署范围的行
_MAINLAND = "中国内地"


class AliyunScraper(BaseScraper):
    """解析阿里云百炼 Qwen3.7 系列定价。"""

    def run(self) -> List[Dict[str, Any]]:
        """抓取主 URL；若解析不到定价记录则回退到 fallback_url。

        主 URL（billing-for-text-generation）当前已失效，返回的 404 页面中
        仍可能包含 "qwen3.7" 字样（推荐 / 站点索引），因此这里以「实际能否解析出
        定价记录」作为回退判据，而非简单文本包含。
        `base.run()` 直接调用 `fetch_url`，不会触发 fallback，故整体覆盖 `run()`。
        """
        url = self.source.get("url")
        recs: List[Dict[str, Any]] = []
        if url:
            try:
                recs = [r for r in (self.parse(self.fetch_url(url)) or []) if r and r.get("model_raw")]
            except Exception:
                recs = []
        if not recs:
            fallback = self.source.get("fallback_url")
            if fallback:
                try:
                    recs = [r for r in (self.parse(self.fetch_url(fallback)) or [])
                            if r and r.get("model_raw")]
                except Exception:
                    recs = []
        return recs

    def parse(self, html: str) -> List[Dict[str, Any]]:
        from parsel import Selector

        sel = Selector(text=html)
        records: List[Dict[str, Any]] = []
        # 每个目标模型仅保留一条（优先 canonical 行，无日期 / preview 后缀）
        seen: set = set()

        for table in sel.css("table"):
            rows = table.css("tr")
            if len(rows) < 2:
                continue
            for row in rows[1:]:
                cells = [c.xpath("string(.)").get(default="").strip() for c in row.css("td,th")]
                if len(cells) < 6:
                    continue
                region = cells[1].strip() if len(cells) > 1 else ""
                if region != _MAINLAND:
                    continue
                model_id = cells[0].split("\n")[0].strip()
                low = model_id.lower()
                if not (low.startswith("qwen3.7-max") or low.startswith("qwen3.7-plus")):
                    continue
                base = "qwen3.7-max" if low.startswith("qwen3.7-max") else "qwen3.7-plus"
                if base in seen:
                    continue
                seen.add(base)
                rec = self._rec(
                    model_raw=model_id,
                    input=clean_price(cells[4]),
                    output=clean_price(cells[5]),
                    cache_hit=None,
                    context=None,
                    condition=None,
                )
                records.append(rec)
        return records
