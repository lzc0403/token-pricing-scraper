"""模型名归一化与 watchlist 匹配。

匹配策略（见 README / config/models.yml）：
  1. `normalize`：转小写、去空格、去 `-` 与 `_`。
  2. 先「精确相等」匹配（归一化后的 model_raw 等于某个别名的归一化形式）。
  3. 再「包含」匹配（model_raw 归一化包含别名归一化，或反之）。
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


def _alias_norms(model: Dict[str, Any]) -> List[str]:
    """返回某模型 canonical + 所有别名的归一化集合。"""
    aliases = [model["canonical"]] + list(model.get("aliases", []))
    return [normalize(a) for a in aliases if normalize(a)]


def match(model_raw: Optional[str], models_cfg: Dict[str, Any]) -> Optional[str]:
    """将原始模型名匹配到目标 canonical；未命中返回 None。"""
    raw_n = normalize(model_raw)
    if not raw_n:
        return None

    models = models_cfg.get("models", [])
    # 第一遍：精确相等
    for m in models:
        if raw_n in _alias_norms(m):
            return m["canonical"]
    # 第二遍：包含匹配
    for m in models:
        for alias_n in _alias_norms(m):
            if not alias_n:
                continue
            if alias_n in raw_n:
                return m["canonical"]
    return None


def build_watchlist(
    records: List[Dict[str, Any]], models_cfg: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """为每条记录打 `canonical` 标签，并返回 (全量带标签, 仅命中记录)。

    Returns:
        annotated : 全量记录，每条新增 `canonical` 字段（未命中为 None）。
        watchlist: 仅 canonical 非 None 的记录（9 个目标模型的筛选视图）。
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
