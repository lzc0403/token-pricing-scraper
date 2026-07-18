"""数据自我检查核对机制：抓取后对结构化数据做多维度校验，防止模型幻觉 / 解析错误。

设计两层校验：
  Tier 1 · 结构性校验（始终运行，纯数据，零网络依赖）
    - 关键字段空值（input / output / model_raw）
    - 价格区间合理性（负值、>1000 ¥/1M 视为可疑）
    - 货币换算一致性（USD 源 input_rmb ≈ input × rate，容差 1%）
    - 重复记录（同 source + model_raw + input + output）
    - 最低价标注一致性（is_lowest_input 与实际最小值是否吻合）
    - 跨源离散度（同 canonical 模型，最高/最低输入价 >10 倍标记待核）

  Tier 2 · 源页面抽样核对（best-effort，对静态源权威，对 SPA 源提示人工）
    - 对每条 watchlist 记录，抓取其源 URL 的静态 HTML，
      核对 model_raw 子串是否真实出现在页面文本中（防编造模型名）。
    - 对 js:false 静态源（如 deepseek），额外核对价格数值串是否出现。
    - js:true 的 SPA 源，静态 HTML 可能不含价格 → 标记「需 Playwright 核对」。

输出：
  - data/audit_report.md  人类可读核对报告
  - data/audit.json       机读结构化结果（suspect 记录 + 统计）

调用：
  from core import audit
  audit.run(DATA_DIR, sources_cfg)   # main.py 抓取后调用
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from core import currency

_TIMEOUT = 20
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
# 视为「价格离谱」的阈值：¥/1M tokens（GLM-5.2 输出 28、Kimi 输出 27 为已知合理高值，留余量）
_PRICE_MAX = 1000.0
# USD 换算容差
_RATE_TOL = 0.01
# 跨源离散倍数阈值
_DIVERGE_RATIO = 10.0


# --------------------------------------------------------------------------- #
# Tier 1：结构性校验
# --------------------------------------------------------------------------- #
def _check_structural(watchlist: List[Dict[str, Any]], rate: float) -> List[Dict[str, Any]]:
    """对 watchlist 做结构性校验，返回可疑项列表。"""
    suspects: List[Dict[str, Any]] = []

    # 1. 关键字段空值
    for r in watchlist:
        if not r.get("model_raw") or str(r.get("model_raw")).strip() in ("", "—"):
            suspects.append({"tier": 1, "code": "EMPTY_MODEL", "severity": "high",
                             "source": r.get("source"), "canonical": r.get("canonical"),
                             "msg": "model_raw 为空", "record": r})
        if r.get("input_rmb") is None and r.get("input") is None:
            suspects.append({"tier": 1, "code": "EMPTY_INPUT", "severity": "high",
                             "source": r.get("source"), "canonical": r.get("canonical"),
                             "msg": "输入价为空", "record": r})
        if r.get("output_rmb") is None and r.get("output") is None:
            suspects.append({"tier": 1, "code": "EMPTY_OUTPUT", "severity": "med",
                             "source": r.get("source"), "canonical": r.get("canonical"),
                             "msg": "输出价为空", "record": r})

    # 2. 价格区间合理性
    for r in watchlist:
        for fld, label in (("input_rmb", "输入"), ("output_rmb", "输出")):
            v = r.get(fld)
            if v is None:
                continue
            if v < 0:
                suspects.append({"tier": 1, "code": "NEG_PRICE", "severity": "high",
                                 "source": r.get("source"), "canonical": r.get("canonical"),
                                 "msg": f"{label}价为负: {v}", "record": r})
            elif v > _PRICE_MAX:
                suspects.append({"tier": 1, "code": "OUTLIER_PRICE", "severity": "high",
                                 "source": r.get("source"), "canonical": r.get("canonical"),
                                 "msg": f"{label}价超阈值(>{_PRICE_MAX}): {v}", "record": r})

    # 3. 货币换算一致性（USD 源）
    for r in watchlist:
        if r.get("currency") != "USD":
            continue
        inp = r.get("input")
        in_rmb = r.get("input_rmb")
        if inp is not None and in_rmb is not None and rate > 0:
            expect = inp * rate
            if expect > 0 and abs(in_rmb - expect) / expect > _RATE_TOL:
                suspects.append({"tier": 1, "code": "RATE_MISMATCH", "severity": "med",
                                 "source": r.get("source"), "canonical": r.get("canonical"),
                                 "msg": f"USD 换算不一致: input={inp} × {rate}={expect:.3f} 但 input_rmb={in_rmb}",
                                 "record": r})

    # 4. 重复记录
    seen: Dict[str, int] = {}
    for r in watchlist:
        key = f"{r.get('source')}|{r.get('model_raw')}|{r.get('input')}|{r.get('output')}"
        seen[key] = seen.get(key, 0) + 1
    for key, cnt in seen.items():
        if cnt > 1:
            src, mr = key.split("|")[:2]
            suspects.append({"tier": 1, "code": "DUPLICATE", "severity": "med",
                             "source": src, "canonical": None,
                             "msg": f"重复记录 ×{cnt}: {mr}", "record": {"key": key}})

    # 5. 最低价标注一致性
    by_canon: Dict[str, List[Dict[str, Any]]] = {}
    for r in watchlist:
        c = r.get("canonical")
        if c:
            by_canon.setdefault(c, []).append(r)
    for c, rows in by_canon.items():
        inputs = [r.get("input_rmb") for r in rows if r.get("input_rmb") is not None]
        if not inputs:
            continue
        true_min = min(inputs)
        for r in rows:
            marked = str(r.get("is_lowest_input", "")).lower() in ("yes", "true", "1")
            in_rmb = r.get("input_rmb")
            if in_rmb is None:
                continue
            actual_low = in_rmb == true_min
            if marked != actual_low:
                suspects.append({"tier": 1, "code": "LOWEST_MISMATCH", "severity": "med",
                                 "source": r.get("source"), "canonical": c,
                                 "msg": f"is_lowest_input={marked} 但实际最低={true_min}（本值={in_rmb}）",
                                 "record": r})

    # 6. 跨源离散度
    for c, rows in by_canon.items():
        inputs = [r.get("input_rmb") for r in rows if r.get("input_rmb") is not None]
        if len(inputs) < 2:
            continue
        lo, hi = min(inputs), max(inputs)
        if lo > 0 and hi / lo > _DIVERGE_RATIO:
            suspects.append({"tier": 1, "code": "DIVERGE", "severity": "low",
                             "source": None, "canonical": c,
                             "msg": f"跨源输入价离散 {hi/lo:.1f}× (最低 {lo} / 最高 {hi})，建议人工核对是否同规格模型",
                             "record": {"min": lo, "max": hi, "ratio": round(hi / lo, 1)}})

    return suspects


# --------------------------------------------------------------------------- #
# Tier 2：源页面抽样核对
# --------------------------------------------------------------------------- #
def _fetch_text(url: str) -> Optional[str]:
    """抓取静态 HTML 文本（不渲染 JS）。失败返回 None。"""
    try:
        resp = requests.get(url, timeout=_TIMEOUT, headers={"User-Agent": _UA})
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or resp.encoding
        return resp.text
    except Exception:
        return None


def _strip_html(html: str) -> str:
    """粗略去标签，保留可见文本。"""
    txt = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    txt = re.sub(r"<style[\s\S]*?</style>", " ", txt, flags=re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"\s+", " ", txt)
    return txt


def _check_sources(
    watchlist: List[Dict[str, Any]], sources_cfg: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """对每条记录核对 model_raw 是否出现在源页面文本中。"""
    suspects: List[Dict[str, Any]] = []
    # 源 id -> (url, js, text_cache)
    src_map: Dict[str, Dict[str, Any]] = {s.get("id"): s for s in sources_cfg}
    text_cache: Dict[str, str] = {}

    for r in watchlist:
        sid = r.get("source")
        mr = r.get("model_raw")
        if not sid or not mr:
            continue
        src = src_map.get(sid)
        if not src:
            continue
        url = src.get("url") or (src.get("urls") or [""])[0]
        if not url:
            continue
        if url not in text_cache:
            text_cache[url] = _fetch_text(url) or ""
        text = text_cache[url]
        if not text:
            suspects.append({"tier": 2, "code": "SRC_UNREACHABLE", "severity": "med",
                             "source": sid, "canonical": r.get("canonical"),
                             "msg": f"源页面抓取失败: {url}", "record": r})
            continue
        visible = _strip_html(text)
        js = bool(src.get("js", False))
        mr_clean = str(mr).strip()
        # 模型名子串核对（取前 12 字符，避免长 notes 串干扰）
        probe = mr_clean[:12]
        if probe and probe not in visible:
            if js:
                # SPA：静态 HTML 无数据属正常，标记待 Playwright 核对
                suspects.append({"tier": 2, "code": "SPA_NEED_RENDER", "severity": "low",
                                 "source": sid, "canonical": r.get("canonical"),
                                 "msg": f"SPA 源静态 HTML 未含模型名「{probe}」，需 Playwright 渲染核对",
                                 "record": {"model_raw": mr_clean, "url": url}})
            else:
                suspects.append({"tier": 2, "code": "MODEL_NOT_FOUND", "severity": "high",
                                 "source": sid, "canonical": r.get("canonical"),
                                 "msg": f"静态源页面未找到模型名「{probe}」，疑似幻觉/编造",
                                 "record": {"model_raw": mr_clean, "url": url}})
        # 静态源额外核对价格数值串
        if not js:
            for fld in ("input", "output"):
                v = r.get(fld)
                if v is None:
                    continue
                vs = ("%g" % v) if isinstance(v, float) else str(v)
                if vs not in visible:
                    suspects.append({"tier": 2, "code": "PRICE_NOT_FOUND", "severity": "high",
                                     "source": sid, "canonical": r.get("canonical"),
                                     "msg": f"静态源页面未找到{fld}价数值「{vs}」，疑似解析/幻觉错误",
                                     "record": {"model_raw": mr_clean, "field": fld, "value": vs, "url": url}})

    return suspects


# --------------------------------------------------------------------------- #
# 报告生成
# --------------------------------------------------------------------------- #
def _build_md(
    suspects: List[Dict[str, Any]], stats: Dict[str, Any], generated_at: str
) -> str:
    lines = [
        "# 数据核对报告（自我检查机制）",
        "",
        f"> 生成时间：{generated_at}",
        "",
        "## 一、核对统计",
        "",
        f"- 校验记录总数：**{stats['total']}**",
        f"- 可疑项总数：**{stats['suspects']}**（high {stats['high']} / med {stats['med']} / low {stats['low']}）",
        f"- Tier1 结构性校验可疑：**{stats['tier1']}**",
        f"- Tier2 源页面核对可疑：**{stats['tier2']}**",
        "",
        "## 二、核对维度",
        "",
        "| 层级 | 维度 | 说明 |",
        "| --- | --- | --- |",
        "| Tier1 | EMPTY_MODEL/INPUT/OUTPUT | 关键字段空值 |",
        "| Tier1 | NEG_PRICE / OUTLIER_PRICE | 负值或超 1000 ¥/1M 的离谱价 |",
        "| Tier1 | RATE_MISMATCH | USD 换算 input_rmb ≠ input×rate（容差 1%） |",
        "| Tier1 | DUPLICATE | 同源同模型同价重复 |",
        "| Tier1 | LOWEST_MISMATCH | is_lowest_input 标注与实际不符 |",
        "| Tier1 | DIVERGE | 同模型跨源输入价 >10× 离散 |",
        "| Tier2 | MODEL_NOT_FOUND | 静态源页面未找到模型名（疑似幻觉） |",
        "| Tier2 | PRICE_NOT_FOUND | 静态源页面未找到价格数值（疑似解析错） |",
        "| Tier2 | SPA_NEED_RENDER | SPA 源需 Playwright 渲染才能核对 |",
        "| Tier2 | SRC_UNREACHABLE | 源页面抓取失败 |",
        "",
    ]
    if not suspects:
        lines += ["## 三、可疑项明细", "", "✅ 未发现可疑项，数据一致性校验通过。", ""]
    else:
        lines += [
            "## 三、可疑项明细（按严重度排序）",
            "",
            "| 严重度 | 层级 | 代码 | 源 | 模型 | 说明 |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        order = {"high": 0, "med": 1, "low": 2}
        for s in sorted(suspects, key=lambda x: order.get(x.get("severity"), 9)):
            lines.append(
                f"| {s.get('severity')} | T{s.get('tier')} | {s.get('code')} | "
                f"{s.get('source') or '-'} | {s.get('canonical') or '-'} | {_esc_md(s.get('msg',''))} |"
            )
        lines.append("")
        lines.append("> ⚠️ high 级别需立即人工核对并修正；med 级别建议复核；low 级别多为 SPA 渲染提示。")
    return "\n".join(lines) + "\n"


def _esc_md(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


# --------------------------------------------------------------------------- #
# 主入口
# --------------------------------------------------------------------------- #
def run(data_dir: str, sources_cfg: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """执行数据核对，写出 data/audit_report.md 与 data/audit.json。

    Args:
        data_dir: data/ 目录。
        sources_cfg: config/sources.yml 解析结果；为 None 时跳过 Tier2。

    Returns:
        {"suspects": [...], "stats": {...}}
    """
    watchlist: List[Dict[str, Any]] = []
    wp = os.path.join(data_dir, "watchlist.json")
    if os.path.exists(wp):
        try:
            with open(wp, encoding="utf-8") as f:
                watchlist = json.load(f) or []
        except (ValueError, OSError):
            watchlist = []

    rate = currency.get_rate()
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    suspects: List[Dict[str, Any]] = []
    suspects += _check_structural(watchlist, rate)
    if sources_cfg:
        suspects += _check_sources(watchlist, sources_cfg)

    sev = {"high": 0, "med": 0, "low": 0}
    for s in suspects:
        sev[s.get("severity", "low")] = sev.get(s.get("severity", "low"), 0) + 1
    stats = {
        "total": len(watchlist),
        "suspects": len(suspects),
        "high": sev["high"],
        "med": sev["med"],
        "low": sev["low"],
        "tier1": sum(1 for s in suspects if s.get("tier") == 1),
        "tier2": sum(1 for s in suspects if s.get("tier") == 2),
    }

    md = _build_md(suspects, stats, generated_at)
    with open(os.path.join(data_dir, "audit_report.md"), "w", encoding="utf-8") as f:
        f.write(md)
    with open(os.path.join(data_dir, "audit.json"), "w", encoding="utf-8") as f:
        json.dump({"generated_at": generated_at, "stats": stats, "suspects": suspects},
                  f, ensure_ascii=False, indent=2)

    return {"suspects": suspects, "stats": stats}
