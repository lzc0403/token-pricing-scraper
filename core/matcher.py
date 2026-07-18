"""模型名归一化与 watchlist 匹配。

匹配策略（见 README / config/models.yml）：
  1. `normalize`：转小写、去空格、去 `-` 与 `_`。
  2. canonical 与普通 alias 执行精确匹配。
  3. 仅显式声明 `match: prefix` 的 alias 执行前缀匹配。
  4. 命中即返回 canonical；未命中返回 None。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

_STRIP_RE = re.compile(r"[\s\-_]")


def normalize(name: Optional[str]) -> str:
    """归一化模型名：小写、去空格、去 `-` 与 `_`。"""
    if name is None:
        return ""
    return _STRIP_RE.sub("", str(name).lower())


def _alias_specs(model: Dict[str, Any]) -> List[Tuple[str, str]]:
    aliases = [model["canonical"]] + list(model.get("aliases", []))
    specs: List[Tuple[str, str]] = []
    for alias in aliases:
        if isinstance(alias, dict):
            name = alias.get("name")
            mode = alias.get("match", "exact")
        else:
            name = alias
            mode = "exact"
        norm = normalize(name)
        if norm and mode in {"exact", "prefix"}:
            specs.append((norm, mode))
    return specs


def match(model_raw: Optional[str], models_cfg: Dict[str, Any]) -> Optional[str]:
    raw_n = normalize(model_raw)
    if not raw_n:
        return None
    for model in models_cfg.get("models", []):
        for alias_n, mode in _alias_specs(model):
            if mode == "exact" and raw_n == alias_n:
                return model["canonical"]
            if mode == "prefix" and raw_n.startswith(alias_n):
                return model["canonical"]
    return None


def build_watchlist(
    records: List[Dict[str, Any]], models_cfg: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """为每条记录打 `canonical` 标签，并返回 (全量带标签, 仅命中记录)。

    Returns:
        annotated : 全量记录，每条新增 `canonical` 字段（未命中为 None）。
        watchlist: 仅 canonical 非 None 的记录（models.yml 配置目标模型的筛选视图）。
    """
    annotated: List[Dict[str, Any]] = []
    watchlist: List[Dict[str, Any]] = []
    for rec in records:
        canon = match(rec.get("model_raw"), models_cfg)
        rec = dict(rec)
        rec["canonical"] = canon
        annotated.append(rec)
        if canon is not None:
            watchlist.append(rec)
    return annotated, watchlist
