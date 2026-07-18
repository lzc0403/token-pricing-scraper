"""OpenRouter 数据二次验证：原始缓存 JSON vs 解析记录交叉核对。

防止解析错误 / 单位换算错误 / 缓存损坏。
产出：
  - data/openrouter_verify.json
  - data/openrouter_verify.md
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CACHE = os.path.join(ROOT, "data", "openrouter_raw.json")
DEFAULT_RULES = os.path.join(ROOT, "config", "openrouter.yml")


def _load_json(path: str) -> Any:
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (ValueError, OSError):
        return None


def _load_rules() -> Dict[str, Any]:
    if not os.path.exists(DEFAULT_RULES):
        return {}
    try:
        import yaml  # type: ignore

        with open(DEFAULT_RULES, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _per_m(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v) * 1_000_000
    except (TypeError, ValueError):
        return None


def verify(data_dir: str = "data", records: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """核对 OpenRouter 缓存与解析结果。

    Args:
        data_dir: data 目录
        records: 可选，已解析的 openrouter 记录；缺省则从 prices.json 过滤 source=openrouter
    """
    cache_path = os.path.join(data_dir, "openrouter_raw.json")
    # 兼容 scraper 新格式 {fetched_at, body} 与旧直接 body
    raw_wrap = _load_json(cache_path)
    if not raw_wrap:
        return _write(data_dir, {
            "ok": False,
            "error": "missing_cache",
            "msg": "data/openrouter_raw.json 不存在，请先抓取 OpenRouter",
            "suspects": [],
            "stats": {},
        })

    if isinstance(raw_wrap, dict) and "body" in raw_wrap:
        body = raw_wrap.get("body") or {}
        fetched_at = raw_wrap.get("fetched_at")
    else:
        body = raw_wrap
        fetched_at = None

    items = body.get("data") if isinstance(body, dict) else None
    if not isinstance(items, list):
        return _write(data_dir, {
            "ok": False,
            "error": "bad_cache",
            "msg": "缓存 JSON 结构无效",
            "suspects": [],
            "stats": {},
        })

    by_id = {str(m.get("id")): m for m in items if m.get("id")}
    rules = _load_rules()
    whitelist = [w.get("id") for w in (rules.get("whitelist") or []) if w.get("id")]
    tol = float(((rules.get("verify") or {}).get("price_tol")) or 0.001)
    max_missing = int(((rules.get("verify") or {}).get("max_missing_whitelist")) or 3)

    if records is None:
        prices = _load_json(os.path.join(data_dir, "prices.json")) or []
        records = [r for r in prices if r.get("source") == "openrouter"]

    or_recs = [r for r in (records or []) if r.get("source") == "openrouter"]
    suspects: List[Dict[str, Any]] = []

    # 1) 每条记录必须回指 openrouter_id 且价格可复算
    for r in or_recs:
        mid = r.get("openrouter_id")
        if not mid:
            # 尝试从 condition 解析 id=
            cond = str(r.get("condition") or "")
            if cond.startswith("id="):
                mid = cond.split("|")[0].replace("id=", "").strip()
        if not mid or mid not in by_id:
            suspects.append({
                "code": "OR_ID_MISSING",
                "severity": "high",
                "model": r.get("model_raw"),
                "msg": f"记录无法在原始缓存中定位 id={mid}",
            })
            continue
        m = by_id[mid]
        p = m.get("pricing") or {}
        exp_in = _per_m(p.get("prompt"))
        exp_out = _per_m(p.get("completion"))
        got_in = r.get("input")
        got_out = r.get("output")
        for label, exp, got in (("input", exp_in, got_in), ("output", exp_out, got_out)):
            if exp is None and got is None:
                continue
            if exp is None or got is None:
                suspects.append({
                    "code": "OR_PRICE_NULL",
                    "severity": "med",
                    "model": r.get("model_raw"),
                    "id": mid,
                    "msg": f"{label} 一侧为空 exp={exp} got={got}",
                })
                continue
            if exp == 0 and got == 0:
                continue
            base = exp if exp != 0 else 1.0
            if abs(got - exp) / base > tol:
                suspects.append({
                    "code": "OR_PRICE_MISMATCH",
                    "severity": "high",
                    "model": r.get("model_raw"),
                    "id": mid,
                    "msg": f"{label} 换算不一致 exp={exp} got={got}",
                })

    # 2) 白名单覆盖
    present_ids = set()
    for r in or_recs:
        mid = r.get("openrouter_id")
        if not mid:
            cond = str(r.get("condition") or "")
            if "id=" in cond:
                mid = cond.split("id=", 1)[1].split("|")[0].strip()
        if mid:
            present_ids.add(mid)
    missing = [wid for wid in whitelist if wid not in present_ids and wid in by_id]
    for mid in missing:
        suspects.append({
            "code": "OR_WHITELIST_MISS",
            "severity": "med",
            "id": mid,
            "msg": f"白名单模型在 API 中存在但未进入解析结果: {mid}",
        })
    # 在 API 也不存在的白名单
    absent_api = [wid for wid in whitelist if wid not in by_id]
    for mid in absent_api:
        suspects.append({
            "code": "OR_WHITELIST_ABSENT",
            "severity": "low",
            "id": mid,
            "msg": f"白名单模型当前 OpenRouter API 无此 id: {mid}",
        })

    high = sum(1 for s in suspects if s.get("severity") == "high")
    med = sum(1 for s in suspects if s.get("severity") == "med")
    low = sum(1 for s in suspects if s.get("severity") == "low")
    ok = high == 0 and len(missing) <= max_missing

    result = {
        "ok": ok,
        "fetched_at": fetched_at,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stats": {
            "raw_models": len(items),
            "parsed": len(or_recs),
            "whitelist": len(whitelist),
            "missing_whitelist": len(missing),
            "absent_api": len(absent_api),
            "suspects": len(suspects),
            "high": high,
            "med": med,
            "low": low,
        },
        "missing_whitelist": missing,
        "absent_api": absent_api,
        "suspects": suspects,
        "sample": [
            {
                "id": r.get("openrouter_id") or r.get("condition"),
                "model": r.get("model_raw"),
                "input": r.get("input"),
                "output": r.get("output"),
            }
            for r in or_recs[:15]
        ],
    }
    return _write(data_dir, result)


def _write(data_dir: str, result: Dict[str, Any]) -> Dict[str, Any]:
    os.makedirs(data_dir, exist_ok=True)
    jpath = os.path.join(data_dir, "openrouter_verify.json")
    mpath = os.path.join(data_dir, "openrouter_verify.md")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    s = result.get("stats") or {}
    lines = [
        "# OpenRouter 二次验证报告",
        "",
        f"- 时间：{result.get('generated_at', '—')}",
        f"- 抓取时间：{result.get('fetched_at') or '—'}",
        f"- 结果：{'✅ 通过' if result.get('ok') else '❌ 未通过'}",
        f"- 原始模型数：{s.get('raw_models', 0)}",
        f"- 解析条数：{s.get('parsed', 0)}",
        f"- 白名单：{s.get('whitelist', 0)}（缺失 {s.get('missing_whitelist', 0)} / API 无 {s.get('absent_api', 0)}）",
        f"- 可疑：{s.get('suspects', 0)}（high {s.get('high', 0)} / med {s.get('med', 0)} / low {s.get('low', 0)}）",
        "",
    ]
    if result.get("error"):
        lines += [f"**错误**：{result.get('msg')}", ""]
    if result.get("suspects"):
        lines.append("## 可疑项")
        for item in result["suspects"][:50]:
            lines.append(
                f"- [{item.get('severity')}] `{item.get('code')}` "
                f"{item.get('id') or item.get('model') or ''} — {item.get('msg')}"
            )
        lines.append("")
    if result.get("sample"):
        lines.append("## 解析样本")
        for x in result["sample"]:
            lines.append(
                f"- {x.get('model')} (`{x.get('id')}`) "
                f"in={x.get('input')} out={x.get('output')}"
            )
        lines.append("")
    with open(mpath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return result
