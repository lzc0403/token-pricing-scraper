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
            rec = self._to_record(m, force_name=w.get("model"), note=w.get("note"), override=w)
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

    @staticmethod
    def _parse_overrides(m: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """解析 OpenRouter pricing.overrides 峰谷时段。

        OpenRouter 部分模型（如 deepseek/deepseek-v4-pro-0813）在 pricing 里带
        overrides 数组，用 utc_start/utc_end（UTC HHMM，如 1000=10:00）划分时段，
        每个时段有独立 prompt/completion（可能含 input_cache_read）。同 DeepSeek 官网
        峰谷：高峰时段（北京 09:00-12:00/14:00-18:00）全价、空闲时段减半。

        返回 {peak_input_low, peak_input_high, peak_output_low, peak_output_high,
               peak_cache_low, peak_cache_high, peak_window_beijing}，
        无峰谷（单档 / overrides 缺省）返回 None。单位：USD / 1M tokens。
        """
        p = m.get("pricing") or {}
        ovs = p.get("overrides") or []
        if not isinstance(ovs, list) or len(ovs) < 2:
            return None
        # 收集所有时段的 input/output（per-token），找高低两档
        inputs: List[float] = []
        outputs: List[float] = []
        caches: List[float] = []
        for ov in ovs:
            pi = _per_m(ov.get("prompt"))
            po = _per_m(ov.get("completion"))
            pc = _per_m(ov.get("input_cache_read"))
            if pi is not None:
                inputs.append(pi)
            if po is not None:
                outputs.append(po)
            if pc is not None:
                caches.append(pc)
        # 无有效高低区分（全时段同价）→ 无峰谷
        if len(set(inputs)) < 2 and len(set(outputs)) < 2:
            return None
        out = {
            "peak_input_low": min(inputs) if inputs else None,
            "peak_input_high": max(inputs) if inputs else None,
            "peak_output_low": min(outputs) if outputs else None,
            "peak_output_high": max(outputs) if outputs else None,
            "peak_cache_low": min(caches) if caches else None,
            "peak_cache_high": max(caches) if caches else None,
        }
        # 高峰/空闲窗口（UTC HHMM → 北京 HHMM）：记录第一个高峰时段的北京区间
        # 语义与 DeepSeek 官网对齐：高峰 = prompt 更大的时段（全价），空闲 = prompt 更小。
        # 按各时段 prompt 大小判定档位，聚合出北京高峰窗口。
        bj_peak_windows: List[Tuple[int, int]] = []
        for ov in ovs:
            pi = _per_m(ov.get("prompt"))
            s = int(ov.get("utc_start") or 0)
            e = int(ov.get("utc_end") or 0)
            if pi is None or s is None or e is None:
                continue
            if pi < out["peak_input_high"]:  # 低档 = 空闲
                continue
            # 高峰时段：UTC → 北京（+8h）
            bs, be = (s + 800) % 2400, (e + 800) % 2400
            bj_peak_windows.append((bs, be))
        if bj_peak_windows:
            out["peak_window_beijing"] = bj_peak_windows
        # 换算回「是否峰谷计费」标记
        out["is_peak"] = True
        return out

    def _to_record(
        self,
        m: Dict[str, Any],
        force_name: Optional[str] = None,
        note: Optional[str] = None,
        override: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        mid = m.get("id")
        name = force_name or _clean_name(str(m.get("name") or mid or ""))
        if not name:
            return None
        p = m.get("pricing") or {}
        # 优先使用白名单 price_override（官网价可能不同于 API 返回值）
        ov_inp = None
        ov_out = None
        if override:
            ov_inp = override.get("input_price")
            ov_out = override.get("output_price")
            if ov_inp is not None:
                try:
                    ov_inp = float(ov_inp)
                except (TypeError, ValueError):
                    ov_inp = None
            if ov_out is not None:
                try:
                    ov_out = float(ov_out)
                except (TypeError, ValueError):
                    ov_out = None
        inp = ov_inp if ov_inp is not None else _per_m(p.get("prompt"))
        out = ov_out if ov_out is not None else _per_m(p.get("completion"))
        cache = _per_m(p.get("input_cache_read"))
        ctx = _fmt_ctx(m.get("context_length"))
        # 记录原始 per-token 便于二次验证；condition 留空（id/note 是内部备注，不对外展示）
        rec = self._rec(
            model_raw=name,
            input=inp,
            output=out,
            cache_hit=cache,
            context=ctx,
            condition=None,
        )
        rec["openrouter_id"] = mid
        rec["openrouter_prompt_per_token"] = p.get("prompt")
        rec["openrouter_completion_per_token"] = p.get("completion")
        # OpenRouter 峰谷：解析 overrides（如 deepseek-v4-pro-0813），
        # 主字段保留基础价（空闲价）供 verify 复算；peak_* 双档供站点动态时钟展示。
        peak = self._parse_overrides(m)
        if peak:
            for k in ("peak_input_low", "peak_input_high",
                      "peak_output_low", "peak_output_high",
                      "peak_cache_low", "peak_cache_high",
                      "peak_window_beijing", "is_peak"):
                rec[k] = peak.get(k)
            # 来源类型标注（OpenRouter 代表市场成交价）
            rec["condition"] = "OpenRouter 峰谷计费"
        return rec
