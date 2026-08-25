"""持久化：写出全量 / watchlist 的 JSON 与 CSV，并对比历史价格变动。"""

from __future__ import annotations

import csv
import json
import os
import shutil
from typing import Any, Dict, List, Optional

# 输出字段顺序（全量）
PRICE_FIELDS = [
    "source",
    "model_raw",
    "input",
    "output",
    "cache_hit",
    "context",
    "condition",
    "unit",
    "currency",
    "input_rmb",
    "output_rmb",
    "canonical",
]

WATCH_FIELDS = PRICE_FIELDS + ["is_lowest_input"]


def _ensure_dir(out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)


def _write_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _write_csv(path: str, rows: List[Dict[str, Any]], fields: List[str]) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in fields})


def _mark_lowest(watchlist: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """为 watchlist 每条记录标注 `is_lowest_input`（跨源同一 canonical 的最低输入价）。"""
    by_canon: Dict[str, List[Dict[str, Any]]] = {}
    for r in watchlist:
        c = r.get("canonical")
        if c:
            by_canon.setdefault(c, []).append(r)

    for recs in by_canon.values():
        inputs: List[float] = []
        for r in recs:
            v = r.get("input_rmb")
            if v is not None:
                inputs.append(v)
        min_in = min(inputs) if inputs else None
        for r in recs:
            is_low = (
                r.get("input_rmb") is not None
                and min_in is not None
                and r.get("input_rmb") == min_in
            )
            r["is_lowest_input"] = "yes" if is_low else "no"
    return watchlist


def write_outputs(records: List[Dict[str, Any]], out_dir: str) -> Dict[str, str]:
    """写出 prices.* 与 watchlist.* 到 out_dir。

    Returns:
        各产物文件路径 dict。
    """
    _ensure_dir(out_dir)

    watchlist = [r for r in records if r.get("canonical") is not None]
    watchlist_sorted = sorted(watchlist, key=lambda r: (r.get("source", ""), r.get("canonical", "")))
    _mark_lowest(watchlist_sorted)

    prices_path = os.path.join(out_dir, "prices.json")
    prices_csv = os.path.join(out_dir, "prices.csv")
    watch_path = os.path.join(out_dir, "watchlist.json")
    watch_csv = os.path.join(out_dir, "watchlist.csv")

    _write_json(prices_path, records)
    _write_csv(prices_csv, records, PRICE_FIELDS)
    _write_json(watch_path, watchlist_sorted)
    _write_csv(watch_csv, watchlist_sorted, WATCH_FIELDS)

    return {
        "prices.json": prices_path,
        "prices.csv": prices_csv,
        "watchlist.json": watch_path,
        "watchlist.csv": watch_csv,
    }


def archive_snapshot(out_dir: str, date_str: Optional[str] = None) -> Optional[str]:
    """每日抓取时归档当前 prices.json 快照到 data/history/YYYY-MM-DD.json。

    用于历史价格趋势图的时间维度数据源。同一天多次抓取只保留最新一次
    （覆盖写），避免 CI 重跑产生重复点。

    Args:
        out_dir: data/ 目录
        date_str: 日期字符串（默认今天，格式 YYYY-MM-DD）
    Returns:
        归档文件路径，或 None（无 prices.json 时）
    """
    from datetime import datetime
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    src = os.path.join(out_dir, "prices.json")
    if not os.path.exists(src):
        return None

    hist_dir = os.path.join(out_dir, "history")
    _ensure_dir(hist_dir)
    dst = os.path.join(hist_dir, f"{date_str}.json")
    shutil.copyfile(src, dst)
    return dst


def compare_previous(current_path: str, previous_path: str) -> List[Dict[str, Any]]:
    """对比本次与历史（已提交）prices.json，返回 watchlist 模型的价格变动。

    按 (canonical, source) 比较 input / output，仅返回有变动的项。

    Returns:
        变动项列表，每项含 canonical/source/model_raw/field/old/new/currency。
        若历史文件不存在或无可比项，返回空列表。
    """
    if not os.path.exists(previous_path):
        return []

    with open(current_path, encoding="utf-8") as f:
        current = json.load(f)
    with open(previous_path, encoding="utf-8") as f:
        previous = json.load(f)

    # 同一 (canonical, source) 下可能有多行不同计费口径（原厂直供闲时/高峰、
    # 云商自建等，见 condition 字段），对比必须带上 condition 否则互相覆盖错位。
    # 用 pop 消费，防止重复行被匹配两次。
    prev_idx: Dict[tuple, Dict[str, Any]] = {}
    for r in previous:
        if r.get("canonical"):
            prev_idx[(r["canonical"], r["source"], r.get("condition") or "")] = r

    deltas: List[Dict[str, Any]] = []
    for r in current:
        canon = r.get("canonical")
        if not canon:
            continue
        prev = prev_idx.pop((canon, r["source"], r.get("condition") or ""), None)
        if not prev:
            continue
        # 该模型在该来源下共有几条不同计费口径（含未变动的），
        # 供 notifier 区分「单档调价」与「刊例整体调整」。
        tier_count = sum(
            1
            for x in current
            if x.get("canonical") == canon and x.get("source") == r["source"]
        )
        for field in ("input", "output"):
            old_val = prev.get(field)
            new_val = r.get(field)
            if old_val != new_val:
                deltas.append(
                    {
                        "canonical": canon,
                        "source": r["source"],
                        "model_raw": r.get("model_raw"),
                        "field": field,
                        "old": old_val,
                        "new": new_val,
                        "currency": r.get("currency"),
                        "condition": r.get("condition"),
                        "tier_count": tier_count,
                    }
                )
    return deltas
