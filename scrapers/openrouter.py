"""OpenRouter 热门模型定价抓取器。

数据源：https://openrouter.ai/api/v1/models?sort=top-weekly
价格字段 pricing.prompt / pricing.completion 为「每 token 美元」；
本解析器换算为「每 1M tokens 美元」后写入标准记录。

规则：
  1. 自动下载并缓存原始 JSON → data/openrouter_raw.json
  2. 优先按 openrouter.yml 白名单匹配（热门主力）
  3. 额外取 top-weekly 前 N 个非免费文本模型作补充
  4. 二次验证：原始缓存 vs 解析结果价格一致性（core/openrouter_verify）
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from scrapers.base import BaseScraper

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CACHE = os.path.join(ROOT, "data", "openrouter_raw.json")
DEFAULT_RULES = os.path.join(ROOT, "config", "openrouter.yml")


def _per_m(price_per_token: Any) -> Optional[float]:
    """USD/token → USD/1M tokens。"""
    if price_per_token is None or price_per_token == "":
        return None
    try:
        v = float(price_per_token)
    except (TypeError, ValueError):
        return None
    if v < 0:
        return None
    return round(v * 1_000_000, 6)


def _fmt_ctx(n: Any) -> Optional[str]:
    if n is None:
        return None
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:g}M"
    if n >= 1000:
        return f"{n // 1000}K"
    return str(n)


def _clean_name(name: str) -> str:
    s = (name or "").strip()
    # 去掉 "OpenAI: " / "Anthropic: " 前缀
    s = re.sub(r"^[A-Za-z0-9 .+-]+:\s*", "", s)
    return s.strip() or name


class OpenrouterScraper(BaseScraper):
    """解析 OpenRouter Models API（JSON）。"""

    def fetch_url(self, url: str) -> str:
        """拉取 JSON API，并写缓存文件。"""
        cache_path = self.source.get("cache_path") or DEFAULT_CACHE
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        resp = self.session.get(url, timeout=40)
        resp.raise_for_status()
        text = resp.text
        # 落盘原始 JSON，供二次验证
        payload = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "url": url,
            "body": json.loads(text),
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        # 兼容 parse：直接喂 body JSON 字符串
        return json.dumps(payload["body"], ensure_ascii=False)

    def _load_rules(self) -> Dict[str, Any]:
        path = self.source.get("rules_path") or DEFAULT_RULES
        if not os.path.exists(path):
            return {}
        try:
            import yaml  # type: ignore

            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def parse(self, html: str) -> List[Dict[str, Any]]:
        try:
            data = json.loads(html)
        except json.JSONDecodeError:
            return []

        items: List[Dict[str, Any]] = data.get("data") or []
        if not isinstance(items, list):
            return []

        rules = self._load_rules()
        whitelist: List[Dict[str, Any]] = rules.get("whitelist") or []
        top_n = int(rules.get("top_weekly_extra") or 0)
        exclude_free = bool(rules.get("exclude_free", True))
        allow_modalities = set(rules.get("output_modalities") or ["text"])

        by_id: Dict[str, Dict[str, Any]] = {}
        for m in items:
            mid = m.get("id")
            if mid:
                by_id[str(mid)] = m

        selected: List[Dict[str, Any]] = []
        seen: Set[str] = set()

        # 1) 白名单（热门主力，按配置顺序）
        for w in whitelist:
            mid = w.get("id")
            if not mid or mid in seen:
                continue
            m = by_id.get(mid)
            if not m:
                continue
            rec = self._to_record(m, force_name=w.get("model"), note=w.get("note"))
            if rec and (not exclude_free or not self._is_free(m)):
                selected.append(rec)
                seen.add(mid)

        # 2) top-weekly 补充（API 已按 top-weekly 排序）
        extra = 0
        if top_n > 0:
            for m in items:
                if extra >= top_n:
                    break
                mid = str(m.get("id") or "")
                if not mid or mid in seen:
                    continue
                if exclude_free and self._is_free(m):
                    continue
                arch = m.get("architecture") or {}
                outs = set(arch.get("output_modalities") or ["text"])
                if allow_modalities and not (outs & allow_modalities):
                    continue
                rec = self._to_record(m, note="top-weekly")
                if not rec:
                    continue
                selected.append(rec)
                seen.add(mid)
                extra += 1

        return selected

    def _is_free(self, m: Dict[str, Any]) -> bool:
        p = m.get("pricing") or {}
        try:
            return float(p.get("prompt") or 0) == 0 and float(p.get("completion") or 0) == 0
        except (TypeError, ValueError):
            return False

    def _to_record(
        self,
        m: Dict[str, Any],
        force_name: Optional[str] = None,
        note: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        mid = m.get("id")
        name = force_name or _clean_name(str(m.get("name") or mid or ""))
        if not name:
            return None
        p = m.get("pricing") or {}
        inp = _per_m(p.get("prompt"))
        out = _per_m(p.get("completion"))
        cache = _per_m(p.get("input_cache_read"))
        ctx = _fmt_ctx(m.get("context_length"))
        cond_bits = [f"id={mid}"]
        if note:
            cond_bits.append(note)
        # 记录原始 per-token 便于二次验证
        rec = self._rec(
            model_raw=name,
            input=inp,
            output=out,
            cache_hit=cache,
            context=ctx,
            condition=" | ".join(cond_bits),
        )
        rec["openrouter_id"] = mid
        rec["openrouter_prompt_per_token"] = p.get("prompt")
        rec["openrouter_completion_per_token"] = p.get("completion")
        return rec
