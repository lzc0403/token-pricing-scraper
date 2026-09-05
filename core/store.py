"""持久化：写出全量 / watchlist 的 JSON 与 CSV，并对比历史价格变动。"""

from __future__ import annotations

import csv
import json
import os
import glob
import shutil
from typing import Any, Dict, List, Optional

# 输出字段顺序（全量）
PRICE_FIELDS = [
    "source",
    "model_raw",
    "input",
    "output",
    "cache_hit",
    "cache_write",
    "cache_storage",
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


# 厂商官网（官方原价）来源 ID 集合——与 site_data._OFFICIAL_SOURCES_ANY + _OFFICIAL_SINGLE
# 口径一致（含双币种双站：deepseek/deepseek_us、kimi/kimi_ai 等）。
_OFFICIAL_SOURCE_IDS = {
    "deepseek", "deepseek_us",        # DeepSeek 国内外官方站
    "bigmodel", "zai",                 # 智谱 国内外官方站
    "kimi", "kimi_ai",                 # Moonshot 国内外官方站
    "minimax",                          # MiniMax 官方
    "aliyun", "volcengine",             # 通义 / 豆包 厂商官网（云厂商主页价，非百炼/智能体代理）
    "openai", "anthropic", "gemini", "grok",  # 海外四大
}


def _is_official_row(src: Any) -> bool:
    return str(src or "") in _OFFICIAL_SOURCE_IDS


def build_official_changes(
    data_dir: str,
    lookback_days: int = 7,
    today_iso: Optional[str] = None,
) -> Dict[str, Any]:
    """基于历史快照与当前 prices.json，产出官方源价格调价 + 新模型清单。

    写入 data/official_changes.json，供前端调价横幅与新品角标使用。

    逻辑：
      1. 当前 prices.json 与 N 天前的归档快照（取历史中第 N 天之前最近一份快照）对比
         字段 input/output/cache_hit/cache_write/cache_storage
      2. 仅保留 is_official 行（厂商官网原价）
      3. 变化幅度 < 1% 的视为抓取抖动，过滤
      4. 新增模型：当前 (canonical, source, condition) 出现在快照中「源不在白名单内
         但当前已收录官方价」的情况

    Args:
        data_dir: data 目录（含 prices.json + history/）
        lookback_days: 回溯天数（默认 7）
        today_iso: 今日 YYYY-MM-DD；默认今日

    Returns:
        {
          "generated_at": today_iso,
          "lookback_days": N,
          "changes": [ {canonical, source, source_label, field, field_cn, old, new, pct, date} ],
          "new_models": [ {canonical, source, source_label, date} ]
        }
    """
    from datetime import datetime
    if today_iso is None:
        today_iso = datetime.now().strftime("%Y-%m-%d")

    sub = {
        "generated_at": today_iso,
        "lookback_days": lookback_days,
        "changes": [],
        "new_models": [],
    }

    prices_path = os.path.join(data_dir, "prices.json")
    if not os.path.exists(prices_path):
        return sub
    try:
        with open(prices_path, encoding="utf-8") as f:
            cur_rows = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return sub

    cur_idx: Dict[tuple, Dict[str, Any]] = {}
    for r in cur_rows:
        if not r.get("canonical") or not _is_official_row(r.get("source")):
            continue
        k = (r["canonical"], r["source"], str(r.get("condition") or ""))
        cur_idx[k] = r

    # 取 N 天前最近一份快照作为对比基线
    hist_dir = os.path.join(data_dir, "history")
    if not os.path.isdir(hist_dir):
        return sub
    files = sorted(glob.glob(os.path.join(hist_dir, "*.json")))
    # 排除今日自身（archive_snapshot 在 main.py 里先生成）
    past = [f for f in files if os.path.basename(f) != f"{today_iso}.json"]
    if not past:
        return sub
    baseline_path = past[max(0, len(past) - lookback_days)]
    try:
        with open(baseline_path, encoding="utf-8") as f:
            prev_rows = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return sub

    prev_idx: Dict[tuple, Dict[str, Any]] = {}
    for r in prev_rows:
        if not r.get("canonical") or not _is_official_row(r.get("source")):
            continue
        k = (r["canonical"], r["source"], str(r.get("condition") or ""))
        prev_idx[k] = r

    # 持久化"首次出现日"映射（避免首次铺底时大量历史行被误标新品）。
    # known_official.json: {canonical: {source: {condition: "YYYY-MM-DD"}}}，
    # 嵌套结构避免 condition 中的 "|" 冲突。
    known_path = os.path.join(data_dir, "known_official.json")
    known_raw: Dict[str, Dict[str, Dict[str, str]]] = {}
    if os.path.exists(known_path):
        try:
            with open(known_path, encoding="utf-8") as f:
                known_raw = json.load(f)
        except (OSError, json.JSONDecodeError, ValueError):
            known_raw = {}

    def _kkey(canon: str, src: str, cond: str) -> tuple:
        return (canon, src, cond)

    # 写回 known（持续累积），并标记本次新收录的行
    today = today_iso
    for k in cur_idx:
        canon, src, cond = k
        bucket = known_raw.setdefault(canon, {}).setdefault(src, {})
        if cond not in bucket:
            bucket[cond] = today
    try:
        with open(known_path, "w", encoding="utf-8") as f:
            json.dump(known_raw, f, ensure_ascii=False, indent=2)
    except OSError:
        pass

    # new_models：当前快照相对基线新增的 (canonical, source, condition)。
    cur_keys = set(cur_idx)
    prev_keys = set(prev_idx)
    new_keys = cur_keys - prev_keys

    # 前端按 (canonical, source) 二元键即可判定 is_new，无需 condition
    # （同 canonical 同 source 多 condition 都视为同一品牌新上架）。
    sub["known"] = {f"{canon}\u0001{src}": fs
                    for canon, sm in known_raw.items()
                    for src, cm in sm.items()
                    for fs in cm.values()}

    _FIELD_CN = {"input": "输入", "output": "输出", "cache_write": "缓存创建",
                 "cache_hit": "缓存读取", "cache_storage": "缓存存储"}
    SOURCE_LBL = {
        "deepseek": "DeepSeek官网", "deepseek_us": "DeepSeek海外官网",
        "bigmodel": "智谱", "zai": "智谱Z.ai",
        "kimi": "Kimi官网", "kimi_ai": "Kimi国际站",
        "minimax": "MiniMax官网",
        "aliyun": "阿里云通义", "volcengine": "火山引擎豆包",
        "openai": "OpenAI官网", "anthropic": "Anthropic官网",
        "gemini": "Gemini官网", "grok": "Grok官网",
    }

    def _pct(o, n):
        try:
            if o is None or n is None or o == 0:
                return None
            return round((float(n) - float(o)) / float(o) * 100, 2)
        except (TypeError, ValueError):
            return None

    for k, cur in cur_idx.items():
        prev = prev_idx.get(k)
        if k in new_keys:
            sub["new_models"].append({
                "canonical": cur["canonical"],
                "source": cur["source"],
                "source_label": SOURCE_LBL.get(cur["source"], cur["source"]),
                "first_seen": known_raw.get(k[0], {}).get(k[1], {}).get(k[2], today_iso),
                "date": today_iso,
            })
            if prev is None:
                # 快照中无此行：跳过字段对比（已在 new_models 中声明）
                continue
        # 字段对比（仅在 prev 存在时进行）
        for field in ("input", "output", "cache_write", "cache_hit", "cache_storage"):
            old_v = prev.get(field)
            new_v = cur.get(field)
            if old_v == new_v:
                continue
            if old_v is None or new_v is None:
                continue
            pct = _pct(old_v, new_v)
            if abs(pct or 0) < 1:
                continue
            sub["changes"].append({
                "canonical": cur["canonical"],
                "source": cur["source"],
                "source_label": SOURCE_LBL.get(cur["source"], cur["source"]),
                "field": field,
                "field_cn": _FIELD_CN.get(field, field),
                "old": old_v,
                "new": new_v,
                "pct": pct,
                "currency": cur.get("currency"),
                "date": today_iso,
            })

    # 调价按幅度降序，取前 30
    sub["changes"].sort(key=lambda x: -abs(x.get("pct") or 0))
    sub["changes"] = sub["changes"][:30]
    return sub


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
