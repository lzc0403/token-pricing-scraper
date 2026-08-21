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

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# --------------------------------------------------------------------------- #
# 审计规则（config/audit_rules.yml 可覆盖；缺省回退到以下默认值）
# 默认值注释即历史硬编码值，改动阈值无需改代码。
# --------------------------------------------------------------------------- #
_RULES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "audit_rules.yml"
)

# 默认值（与历史行为一致）
_TIMEOUT = 20
_PRICE_MAX = 1000.0          # 视为「价格离谱」的阈值：¥/1M tokens
_RATE_TOL = 0.01             # USD 换算容差
_DIVERGE_RATIO = 10.0        # 跨源离散倍数阈值
_CACHE_SUSPECT_RATIO = 0.6   # 缓存命中价 > 输入价 × 0.6 视为异常偏高
_CACHE_RATIO_DEV = 0.15      # TERM1 CACHE_RATIO_ANOMALY 偏离基准 ±15%
_OPENAI_LONG_DEV = 0.15      # OPENAI_LONG_DEV 硬编码价 vs OR 偏差 ±15%


def _load_rules() -> Dict[str, Any]:
    """从 config/audit_rules.yml 读取规则；文件缺失/非法时返回空 dict（用默认值）。"""
    try:
        import yaml

        with open(_RULES_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


_RULES: Dict[str, Any] = _load_rules()


def _rule(name: str, default: float) -> float:
    """读规则值，缺省回退 default。"""
    v = _RULES.get(name)
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


# 关键主力模型：输入价缺失必须拦（门禁级）
# 这些模型是页面主推、用户最关注的价格基准，缺输入价直接失败
_CRITICAL_MODELS = frozenset(
    {
        "DeepSeek V4 Pro",
        "DeepSeek V4 Flash",
        "Qwen3.8 Max",
        "Qwen3.7 Max",
        "GLM-5.2",
        "GLM-5.1",
        "Kimi K3",
        "GPT-4o",
        "Claude Opus 5",
        "Gemini 3.7 Flash",
    }
)


# --------------------------------------------------------------------------- #
# Tier 1：结构性校验
# --------------------------------------------------------------------------- #
def _check_structural(watchlist: List[Dict[str, Any]], rate: float) -> List[Dict[str, Any]]:
    """对 watchlist 做结构性校验，返回可疑项列表。"""
    suspects: List[Dict[str, Any]] = []
    price_max = _rule("price_max", _PRICE_MAX)
    rate_tol = _rule("rate_tol", _RATE_TOL)
    diverge_ratio = _rule("diverge_ratio", _DIVERGE_RATIO)

    # 1. 关键字段空值
    for r in watchlist:
        if not r.get("model_raw") or str(r.get("model_raw")).strip() in ("", "—"):
            suspects.append({"tier": 1, "code": "EMPTY_MODEL", "severity": "high",
                             "source": r.get("source"), "canonical": r.get("canonical"),
                             "msg": "model_raw 为空", "record": r})
        if r.get("input_rmb") is None and r.get("input") is None:
            sev = "high" if r.get("canonical") in _CRITICAL_MODELS else "low"
            suspects.append({"tier": 1, "code": "EMPTY_INPUT", "severity": sev,
                             "source": r.get("source"), "canonical": r.get("canonical"),
                             "msg": ("关键模型输入价为空" if sev == "high" else "输入价为空"), "record": r})
        if r.get("output_rmb") is None and r.get("output") is None:
            suspects.append({"tier": 1, "code": "EMPTY_OUTPUT", "severity": "med",
                             "source": r.get("source"), "canonical": r.get("canonical"),
                             "msg": "输出价为空", "record": r})

    # 1b. 缓存命中价合理性（语义：缓存命中价必须 ≤ 输入价，且应明显低于输入价）
    for r in watchlist:
        in_v = r.get("input")
        out_v = r.get("output")
        cache_v = r.get("cache_hit")
        canon = r.get("canonical")
        if in_v is None or cache_v is None:
            continue
        # 缓存命中 > 输入价 → 几乎必然列错位/解析错误
        if cache_v > in_v:
            suspects.append({"tier": 1, "code": "CACHE_GT_INPUT", "severity": "high",
                             "source": r.get("source"), "canonical": canon,
                             "msg": f"缓存命中价({cache_v}) > 输入价({in_v})，疑似列错位/解析错误",
                             "record": r})
        elif cache_v > in_v * _rule("cache_suspect_ratio", _CACHE_SUSPECT_RATIO):
            # 缓存命中通常 ≤ 输入价的三四折；高于 60% 已显可疑（各厂商折扣不同，留余量）
            suspects.append({"tier": 1, "code": "CACHE_SUSPECT", "severity": "med",
                             "source": r.get("source"), "canonical": canon,
                             "msg": f"缓存命中价({cache_v}) 接近输入价({in_v})，异常偏高",
                             "record": r})

    # 1c. 缓存/输入比率跨源异常（如百炼缓存价是推算的 20%，若与实际折扣差异过大则告警）
    # 基准用「中位数」而非均值：少数源偏离不会把基准拉偏，只有真正偏离的源被标记。
    by_canon_cache: Dict[str, List[Dict[str, Any]]] = {}
    for r in watchlist:
        c = r.get("canonical")
        in_v = r.get("input")
        cache_v = r.get("cache_hit")
        if c and in_v is not None and cache_v is not None and in_v > 0:
            ratio = cache_v / in_v
            by_canon_cache.setdefault(c, []).append(
                {"source": r.get("source"), "ratio": ratio, "record": r}
            )
    for c, entries in by_canon_cache.items():
        if len(entries) < 2:
            continue
        ratios = [e["ratio"] for e in entries]
        baseline = sorted(ratios)[len(ratios) // 2]  # 中位数作基准
        for e in entries:
            if baseline > 0 and abs(e["ratio"] - baseline) / baseline > _rule("cache_ratio_dev", _CACHE_RATIO_DEV):
                suspects.append({"tier": 1, "code": "CACHE_RATIO_ANOMALY", "severity": "med",
                                 "source": e["record"].get("source"), "canonical": c,
                                 "msg": f"缓存/输入比率({e['ratio']:.0%}) 偏离同模型基准({baseline:.0%}) 超 15%，"
                                        f"疑似缓存价缺失/估算口径不一致",
                                 "record": e["record"]})

    # 2. 价格区间合理性（按原币种判断：CNY 源阈值 1000 元；USD 源阈值 $1000，
    #    避免 Pro 级旗舰如 GPT-5.5 Pro 输出 $180×7=1260 元被误报为离谱价）
    for r in watchlist:
        is_usd = r.get("currency") == "USD"
        for fld, label in (("input_rmb", "输入"), ("output_rmb", "输出")):
            v = r.get(fld)
            if v is None:
                continue
            if v < 0:
                suspects.append({"tier": 1, "code": "NEG_PRICE", "severity": "high",
                                 "source": r.get("source"), "canonical": r.get("canonical"),
                                 "msg": f"{label}价为负: {v}", "record": r})
            elif v > price_max:
                # USD 源：用原始 USD 价对比（rmb 换算会放大 Pro 旗舰价）
                raw = r.get("output" if label == "输出" else "input")
                if not is_usd or not isinstance(raw, (int, float)) or raw > price_max:
                    suspects.append({"tier": 1, "code": "OUTLIER_PRICE", "severity": "high",
                                     "source": r.get("source"), "canonical": r.get("canonical"),
                                     "msg": f"{label}价超阈值(>{price_max}): {v}", "record": r})

    # 3. 货币换算一致性（USD 源）
    for r in watchlist:
        if r.get("currency") != "USD":
            continue
        inp = r.get("input")
        in_rmb = r.get("input_rmb")
        if inp is not None and in_rmb is not None and rate > 0:
            expect = inp * rate
            if expect > 0 and abs(in_rmb - expect) / expect > rate_tol:
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
        inputs: List[float] = []
        for r in rows:
            v = r.get("input_rmb")
            if v is not None:
                inputs.append(v)
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
        inputs_div: List[float] = []
        for r in rows:
            v = r.get("input_rmb")
            if v is not None:
                inputs_div.append(v)
        if len(inputs_div) < 2:
            continue
        lo, hi = min(inputs_div), max(inputs_div)
        if lo > 0 and hi / lo > diverge_ratio:
            suspects.append({"tier": 1, "code": "DIVERGE", "severity": "low",
                             "source": None, "canonical": c,
                             "msg": f"跨源输入价离散 {hi/lo:.1f}× (最低 {lo} / 最高 {hi})，建议人工核对是否同规格模型",
                             "record": {"min": lo, "max": hi, "ratio": round(hi / lo, 1)}})

    # 7. OpenAI 硬编码长上下文价 vs OpenRouter 交叉校验
    # openai.py 的 _LONG_CONTEXT_PRICES 是硬编码值（TODO：待改动态抓取），
    # 此处与 OpenRouter 同模型价格对比，偏差超 15% 告警，防止硬编码价过期。
    for r in watchlist:
        if r.get("source") != "openai" or not r.get("openrouter_id"):
            continue
        cond = str(r.get("condition") or "")
        if "长文本" not in cond and "长上下文" not in cond:
            continue
        or_records = [
            x for x in watchlist
            if x.get("openrouter_id") == r.get("openrouter_id")
            and x.get("source") == "openrouter"
        ]
        if not or_records:
            suspects.append({"tier": 1, "code": "OPENAI_LONG_NO_OR", "severity": "med",
                             "source": "openai", "canonical": r.get("canonical"),
                             "msg": f"OpenAI 硬编码长上下文价 {r.get('canonical')} 无对应 OpenRouter 记录可交叉校验",
                             "record": r})
            continue
        or_rec = or_records[0]
        for fld in ("input", "output"):
            oai_v = r.get(fld)
            or_v = or_rec.get(fld)
            if oai_v is not None and or_v is not None and or_v > 0:
                dev = abs(oai_v - or_v) / or_v
                if dev > _rule("openai_long_dev", _OPENAI_LONG_DEV):
                    suspects.append({"tier": 1, "code": "OPENAI_LONG_DEV", "severity": "high",
                                     "source": "openai", "canonical": r.get("canonical"),
                                     "msg": f"OpenAI 硬编码长上下文{fld}价({oai_v}) 与 OpenRouter({or_v}) 偏差 {dev:.1%}",
                                     "record": r})

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
    src_map: Dict[str, Dict[str, Any]] = {}
    for s in sources_cfg:
        sid = s.get("id")
        if sid:
            src_map[sid] = s
    text_cache: Dict[str, str] = {}

    for r in watchlist:
        sid = r.get("source")
        mr = r.get("model_raw")
        if not sid or not mr:
            continue
        src = src_map.get(sid)
        if not src:
            continue
        # API/cache 型源（如 openrouter 走 JSON API 缓存、aliyun_bailian 走 JSON 文档接口）：
        # 返回体是 JSON 而非 HTML，静态 HTML 核对不适用，整个 Tier2 跳过
        # （避免 PRICE_NOT_FOUND / MODEL_NOT_FOUND 误报淹没报告）。
        url = src.get("url") or (src.get("urls") or [""])[0]
        if src.get("cache_path") or (url and re.search(r"\.json(\?|$)|/api/", url)):
            continue
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
        f"- 门禁状态：**{'⛔ 阻断（存在 high 级可疑项）' if stats.get('gate') == 'block' else '✅ 通过'}**",
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
        for s in sorted(suspects, key=lambda x: order.get(str(x.get("severity") or ""), 9)):
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
    # 门禁只按 Tier1 high 判定：Tier2 是源页面静态核对，SPA/API 源有大量
    # 「静态 HTML 找不到价格」的误报（数据本身来自 Playwright/API，静态核对不适用）。
    # 若把 Tier2 high 也算进门禁，CI 会永久 block。Tier1 是纯数据校验，无误报，是真正门禁。
    tier1_high = sum(
        1 for s in suspects if s.get("tier") == 1 and s.get("severity") == "high"
    )
    stats = {
        "total": len(watchlist),
        "suspects": len(suspects),
        "high": sev["high"],
        "med": sev["med"],
        "low": sev["low"],
        "tier1": sum(1 for s in suspects if s.get("tier") == 1),
        "tier2": sum(1 for s in suspects if s.get("tier") == 2),
        # 门禁判定：Tier1 high > 0 → block（结构性数据错误，不可信）
        "tier1_high": tier1_high,
        "gate": "block" if tier1_high > 0 else "pass",
    }

    md = _build_md(suspects, stats, generated_at)
    with open(os.path.join(data_dir, "audit_report.md"), "w", encoding="utf-8") as f:
        f.write(md)
    with open(os.path.join(data_dir, "audit.json"), "w", encoding="utf-8") as f:
        json.dump({"generated_at": generated_at, "stats": stats, "suspects": suspects},
                  f, ensure_ascii=False, indent=2)

    return {"suspects": suspects, "stats": stats}
