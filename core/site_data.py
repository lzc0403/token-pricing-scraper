"""site 数据层：数据组装（watchlist → 站点数据结构）。

由 site.py 拆出，职责单一：从 data/watchlist.json 构建
_official_rows / _mainstream_sections / _channel_rows 等站点数据。
"""
from __future__ import annotations
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from core import currency  # noqa: F401
from core import mainstream_catalog
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CATALOG_PATH = os.path.join(_ROOT_DIR, "config", "mainstream_models.yml")


SOURCE_LABELS: Dict[str, str] = {
    "aliyun": "阿里云",
    "volcengine": "火山引擎",
    "tencent": "腾讯云国际",
    "bigmodel": "智谱",
    "deepseek": "DeepSeek",
    "minimax": "MiniMax",
    "kimi": "Kimi",
    "modelmesh": "胜算云",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google": "Google",
    "openrouter": "OpenRouter",
    "aliyun_intl": "阿里云国际",
    "aliyun_bailian": "阿里云百炼",
    "tencent_cn": "腾讯云CN",
    "atlascloud": "AtlasCloud",
    "volcengine_intl": "火山云海外",
    "zai": "智谱Z.ai",
}

# 厂商官网（官方原价）来源
OFFICIAL_SOURCE: Dict[str, str] = {
    # DeepSeek 官方
    "DeepSeek V4 Pro": "deepseek",
    "DeepSeek V4 Flash": "deepseek",
    "DeepSeek V3.2": "deepseek",
    # 智谱官方
    "GLM-5.1": "bigmodel",
    "GLM-5.2": "bigmodel",
    # Kimi 官方
    "Kimi K3": "kimi",
    "Kimi K2.6": "kimi",
    "Kimi K2.7 Code": "kimi",
    # MiniMax 官方
    "MiniMax M2.7": "minimax",
    "MiniMax M3": "minimax",
    # 通义千问官方（阿里云）
    "Qwen3.7 Max": "aliyun",
    "Qwen3.7 Plus": "aliyun",
    # 豆包官方（火山引擎）— volcengine 同时是渠道源，但对 Doubao 系列它是厂商官网价
    "Doubao Seed 2.1 Pro": "volcengine",
    "Doubao Seed 2.1 Turbo": "volcengine",
    # OpenAI 官方（developers.openai.com，USD）
    "GPT-5.6 Sol": "openai",
    "GPT-5.6 Terra": "openai",
    "GPT-5.6 Luna": "openai",
    "GPT-5.5": "openai",
    "GPT-5.5 Pro": "openai",
}

# 渠道源：非官网聚合/转售渠道
CHANNEL_SOURCES = {"modelmesh", "tencent", "tencent_cn", "openrouter", "volcengine", "aliyun", "aliyun_intl", "aliyun_bailian", "atlascloud", "volcengine_intl"}

# 渠道按「结算币种」分区：USD 结算 = 海外渠道面板；CNY/无标价 = 国内渠道面板。
# 腾讯云/火山引擎等国内云厂商也可能以 USD 对外报价（如跨境实例），一律归入海外。

# 厂内型号排序：同一厂商内「最强 / 最新」优先（下标越小越靠前）
# 展示时还会再套一层「厂商聚合」：同厂模型挨在一起，不跨厂穿插。
MAINSTREAM_SORT_ORDER: List[str] = [
    # DeepSeek
    "DeepSeek V4 Pro",
    "DeepSeek V4 Flash",
    "DeepSeek V3.2",
    # 通义千问
    "Qwen3.7 Max",
    "Qwen3.7 Plus",
    # 智谱
    "GLM-5.2",
    "GLM-5.1",
    # Kimi
    "Kimi K3",
    "Kimi K2.7 Code",
    "Kimi K2.6",
    # MiniMax
    "MiniMax M3",
    "MiniMax M2.7",
    # 豆包
    "Doubao Seed 2.1 Pro",
    "Doubao Seed 2.1 Turbo",
    # 海外 — 各厂旗舰优先，同厂相邻
    "GPT-5.6 Sol",
    "GPT-5.6 Terra",
    "GPT-5.6 Luna",
    "GPT-4o",
    "Claude Fable 5",
    "Claude Opus 5",
    "Claude Opus 4.8",
    "Claude Opus 4.7",
    "Claude Opus 4.6",
    "Claude Opus 4.5",
    "Claude Sonnet 5",
    "Claude Sonnet 4.6",
    "Claude Sonnet 4.5",
    "Claude Haiku 4.5",
    "Gemini 3.5 Pro",
    "Gemini 3.5 Flash",
]

# 国内厂商顺序（与 config/mainstream_models.yml 目录一致）
DOMESTIC_VENDOR_ORDER: List[str] = [
    "deepseek",
    "qwen",
    "glm",
    "kimi",
    "minimax",
    "doubao",
]

# 海外厂商顺序
OVERSEAS_VENDOR_ORDER: List[str] = [
    "openai",
    "anthropic",
    "google",
    "aliyun_intl",
    "atlascloud",
]

# source_id → 厂商分组 id（官方表/渠道表聚合用）
SOURCE_VENDOR: Dict[str, str] = {
    "deepseek": "deepseek",
    "aliyun": "qwen",
    "bigmodel": "glm",
    "kimi": "kimi",
    "minimax": "minimax",
    "volcengine": "doubao",
    "openai": "openai",
    "anthropic": "anthropic",
    "google": "google",
    "aliyun_intl": "aliyun_intl",
    "atlascloud": "atlascloud",
}

MODEL_ORDER: List[str] = [
    # 国内：同厂连续，厂内旗舰优先（与 MAINSTREAM_SORT_ORDER 对齐）
    "DeepSeek V4 Pro",
    "DeepSeek V4 Flash",
    "DeepSeek V3.2",
    "Qwen3.7 Max",
    "Qwen3.7 Plus",
    "GLM-5.2",
    "GLM-5.1",
    "Kimi K3",
    "Kimi K2.7 Code",
    "Kimi K2.6",
    "MiniMax M3",
    "MiniMax M2.7",
    "Doubao Seed 2.1 Pro",
    "Doubao Seed 2.1 Turbo",
    "Seedance 2.0",
    # 海外最主流（只保留热门旗舰/主力）
    "GPT-5.6 Sol",
    "GPT-5.6 Terra",
    "GPT-5.6 Luna",
    "GPT-5",
    "GPT-4o",
    "Claude Fable 5",
    "Claude Opus 5",
    "Claude Opus 4.8",
    "Claude Opus 4.7",
    "Claude Opus 4.6",
    "Claude Opus 4.5",
    "Claude Sonnet 5",
    "Claude Sonnet 4.6",
    "Claude Sonnet 4.5",
    "Claude Haiku 4.5",
    "Claude 5",
    "Gemini 3.5 Pro",
    "Gemini 3.5 Flash",
    "Gemini 2.5 Pro",
    "Gemini 2.5 Flash",
]

# 国内模型（筛选用：仅国内模型）
DOMESTIC_MODELS = {
    "DeepSeek V4 Pro",
    "DeepSeek V4 Flash",
    "DeepSeek V3.2",
    "Qwen3.7 Max",
    "Qwen3.7 Plus",
    "GLM-5.1",
    "GLM-5.2",
    "Kimi K2.6",
    "Kimi K3",
    "Kimi K2.7 Code",
    "MiniMax M2.7",
    "MiniMax M3",
    "Doubao Seed 2.1 Pro",
    "Doubao Seed 2.1 Turbo",
    "Seedance 2.0",
}

# 海外主流模型官方数据已迁移到 config/mainstream_models.yml
# 旧 OVERSEAS_OFFICIAL 硬编码已移除；_overseas_official_rows() 改为从目录读取。

# 已知噪声片段（精确清理）
_NOISE_PHRASES = (
    "当前能力等同于",
    "Batch调用半价",
    "上下文缓存享有折扣",
    "原厂直供",
    "新品",
)

_TRAILING_SUFFIX = re.compile(
    r"(当前能力|Batch|批处理|调用半价|上下文|缓存|享有折扣|原厂直供|新品).*$",
    re.I,
)
_SPACE_RE = re.compile(r"\s+")


def source_label(source_id: Any) -> str:
    if source_id is None:
        return "—"
    sid = str(source_id).strip()
    if not sid or sid == "—":
        return "—"
    return SOURCE_LABELS.get(sid, sid)


def clean_model_name(name: Any, fallback: str = "—") -> str:
    """仅保留模型名称本身，去掉批注与营销尾巴。"""
    if name is None:
        return fallback
    s = str(name).strip()
    if not s:
        return fallback
    # 先按已知噪声短语硬切
    for phrase in _NOISE_PHRASES:
        idx = s.find(phrase)
        if idx > 0:
            s = s[:idx]
    s = _TRAILING_SUFFIX.sub("", s)
    # 去掉尾部无用标点/空白
    s = s.strip(" \t\r\n-_|·，,。.;；")
    s = _SPACE_RE.sub(" ", s).strip()
    return s or fallback


def _load_new_model_tracking(data_dir: str = "data") -> List[Dict[str, Any]]:
    """读取 config/new_models.yml 新品跟进清单。"""
    cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "new_models.yml")
    if not os.path.exists(cfg_path):
        return []
    try:
        import yaml
        raw = yaml.safe_load(open(cfg_path, encoding="utf-8")) or {}
    except Exception:
        return []
    items = raw.get("models") or []
    out: List[Dict[str, Any]] = []
    for m in items:
        if not isinstance(m, dict):
            continue
        out.append(
            {
                "canonical": m.get("canonical") or "—",
                "family": m.get("family") or "—",
                "region": m.get("region") or "—",
                "status": m.get("status") or "tracking",
                "priority": m.get("priority") or "normal",
                "note": m.get("note") or "",
                "aliases": m.get("aliases") or [],
            }
        )
    # tracking 优先、high 优先
    prio = {"high": 0, "normal": 1, "low": 2}
    st = {"tracking": 0, "active": 1, "retired": 2}
    out.sort(key=lambda x: (st.get(x["status"], 9), prio.get(x["priority"], 9), x["canonical"]))
    return out


def _merge_tracking_status(tracking: List[Dict[str, Any]], known_canons: List[str], overseas_canons: List[str]) -> List[Dict[str, Any]]:
    """把清单与现有报价状态合并：已上榜则 active，否则 tracking。"""
    known = set(known_canons) | set(overseas_canons)
    merged = []
    for t in tracking:
        if t.get("status") == "retired":
            continue
        item = dict(t)
        if item["canonical"] in known:
            item["status"] = "active"
            item["presence"] = "已上榜"
        else:
            item["status"] = item.get("status") or "tracking"
            item["presence"] = "监听中"
        merged.append(item)
    return merged


def _load_json(path: str) -> Optional[Any]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (ValueError, OSError):
        return None


def _fmt_num(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        if v == int(v):
            return str(int(v))
        return "%g" % v
    return str(v)


def _clean_ctx_label(ctx: Any) -> str:
    """把上下文 token 数转成人类可读标签：1048576→1M，131072→128K。"""
    if not isinstance(ctx, int) or not ctx:
        return ""
    if ctx >= 1_000_000:
        m = round(ctx / 1_000_000, 1)
        return ("%g" % m).rstrip("0").rstrip(".") + "M"
    return f"{ctx // 1000}K"


def _esc(s: Any) -> str:
    if s is None:
        return "—"
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _esc_attr(s: Any) -> str:
    return _esc(s).replace("'", "&#39;")


def _is_overseas(r: Dict[str, Any]) -> bool:
    return str(r.get("currency") or "").upper() == "USD"


def _is_official_row(canon: str, r: Dict[str, Any]) -> bool:
    official = OFFICIAL_SOURCE.get(canon)
    return bool(official and str(r.get("source") or "") == official)


def _is_official_any_currency(canon: str, r: Dict[str, Any]) -> bool:
    """官网源（不分币种）识别：厂商国内站(CNY)与海外站(USD)均视为官网官方标价。

    - DeepSeek：中文站(deepseek, CNY) + 英文站(deepseek_us, USD)
    - 智谱 GLM：国内站(bigmodel, CNY) + 海外站(zai, USD)
    - 其余厂商官网源：与 _is_official_row 一致。
    """
    if not canon:
        return False
    src = str(r.get("source") or "")
    if str(canon).startswith("DeepSeek") and src in ("deepseek", "deepseek_us"):
        return True
    if str(canon).startswith("GLM") and src in ("bigmodel", "zai"):
        return True
    return _is_official_row(canon, r)


def _is_channel_row(r: Dict[str, Any]) -> bool:
    return str(r.get("source") or "") in CHANNEL_SOURCES


def _sort_canons(canons: List[str]) -> List[str]:
    """模型排序：同厂连续，厂内按 MODEL_ORDER（旗舰优先）。"""
    order = {name: i for i, name in enumerate(MODEL_ORDER)}
    return sorted(canons, key=lambda c: (order.get(c, 1000), c))


def _vendor_rank(source_or_vendor: Any, region: str = "domestic") -> int:
    """厂商展示序：国内 deepseek→qwen→…；海外 openai→anthropic→google。"""
    key = str(source_or_vendor or "").strip().lower()
    vendor = SOURCE_VENDOR.get(key, key)
    order = DOMESTIC_VENDOR_ORDER if region != "overseas" else OVERSEAS_VENDOR_ORDER
    if vendor in order:
        return order.index(vendor)
    return 1000


def _model_rank(canon: Any) -> int:
    order = {name: i for i, name in enumerate(MODEL_ORDER)}
    return order.get(str(canon or ""), 1000)


def _official_sort_key(r: Dict[str, Any]) -> Tuple[int, int, str, float]:
    """官方表：同厂聚合 + 厂内旗舰优先 + 同型号价格升序。"""
    region = "overseas" if str(r.get("currency") or "").upper() == "USD" else "domestic"
    # 优先用 source 映射；海外 catalog 行 source 已是 openai/anthropic/google
    vendor_key = r.get("source") or r.get("family") or ""
    return (
        _vendor_rank(vendor_key, region),
        _model_rank(r.get("canonical")),
        str(r.get("model") or "").lower(),
        _price_key(r),
    )


def _price_key(r: Dict[str, Any]) -> float:
    v = r.get("input_rmb")
    if v is None:
        v = r.get("input")
    return float(v) if isinstance(v, (int, float)) else 1e18


def _split_condition(cond: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """把 condition 拆成 (peak_cond, source_type, token_cond)。

    peak_cond: 空闲时段 / 高峰时段
    source_type: 原厂直供 / 腾讯云自建 / 阿里云自部署 / 火山引擎自部署
    token_cond: 其它 token 长度条件
    """
    if not cond:
        return None, None, None
    peak = source = token = None
    for part in (p.strip() for p in cond.split("|") if p.strip()):
        if part in ("空闲时段", "高峰时段"):
            peak = part
        elif part in ("原厂直供", "腾讯云自建", "阿里云自部署", "火山引擎自部署"):
            source = part
        else:
            token = part
    return peak, source, token


# ── 峰谷时段定义 ────────────────────────────────────────────────────────────
# 统一以 UTC+8（北京时间）为基准时钟。各渠道虽同为 UTC+8，但峰谷「窗口」可能
# 与 DeepSeek 官方相反（如阿里云国际站：闲时 22:00-08:00，其余忙时），导致同一
# 时刻两边档位可能错位（08-09/12-14/18-22 错峰时段一方闲、一方忙）。
# peak/off 用 [[起,止), ...] 的小时区间表达；二者只定义其一，另一为补集。
PEAK_SCHEDULES = {
    # DeepSeek 官方（国内/英文站）：高峰 09:00-12:00、14:00-18:00，其余空闲
    "deepseek_official": {
        "tz_offset": 8, "tz_label": "北京时间 (UTC+8)",
        "peak": [[9, 12], [14, 18]], "off": None,
        "peak_label": "高峰", "off_label": "空闲",
    },
    # 阿里云国际站 Model Studio：闲时 22:00-次日08:00，其余忙时（同样 UTC+8）
    "aliyun_intl": {
        "tz_offset": 8, "tz_label": "北京时间 (UTC+8)",
        "peak": None, "off": [[22, 24], [0, 8]],
        "peak_label": "忙时", "off_label": "空闲",
    },
}

# 渠道源 → 其自身峰谷窗口 schedule key（仅当该渠道独立峰谷且窗口与官方不同才标注）
_CHANNEL_PEAK_SCHED = {
    "aliyun_intl": "aliyun_intl",
}

# 版本后缀模型 → 父模型（官网基准回退用）。
# 如 OpenRouter 的 DeepSeek V4 Pro 0813（0813 正式版，带峰谷）是 V4 Pro 的旧版本，
# 其官方基准价 = V4 Pro 官网价；父模型官网价在 _build_site_data 计算官方基准时回退查找。
_CANON_PARENT = {
    "DeepSeek V4 Pro 0813": "DeepSeek V4 Pro",
}


def _source_peak_schedule(source: Optional[str], canon: Optional[str] = None) -> Optional[str]:
    """返回某渠道源自身使用的峰谷窗口 key；无独立峰谷返回 None。

    - 常规渠道：按 source 查 _CHANNEL_PEAK_SCHED。
    - OpenRouter：它是市场成交价源，其 DeepSeek 峰的 overrides 时段与 DeepSeek 官网一致
      （北京高峰 09-12/14-18），故带峰谷的 OpenRouter DeepSeek 行复用 deepseek_official
      窗口，便于与官网档位实时对齐验证。
    """
    if not source:
        return None
    if source == "openrouter" and canon and "deepseek" in str(canon).lower():
        return "deepseek_official"
    return _CHANNEL_PEAK_SCHED.get(source)


def _merge_peak_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """合并同一模型+来源的「空闲时段/高峰时段」双行为单行。

    输出 row 保留闲时价作为主价（用于排序与官网基准比较），同时附加 peak_*_low/high
    字段用于展示（展示时闲时在前、高峰在后）。condition 简化为「来源类型 · 峰谷计费」。
    """
    groups: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = {}
    for r in rows:
        peak, source, token = _split_condition(r.get("condition"))
        key = (r.get("canonical"), r.get("source"), source, token)
        groups.setdefault(key, []).append({"peak": peak, "row": r})

    merged: List[Dict[str, Any]] = []
    for items in groups.values():
        if len(items) == 1:
            merged.append(items[0]["row"])
            continue
        by_peak = {item["peak"]: item["row"] for item in items if item["peak"]}
        if "空闲时段" in by_peak and "高峰时段" in by_peak:
            low = by_peak["空闲时段"]
            high = by_peak["高峰时段"]
            # 闲时优先：主价字段（input_rmb/output_rmb/input/output/cache_hit）取闲时价，
            # 高峰价仅通过 peak_*_high 在展示层作为附注呈现。
            mrow = dict(low)
            mrow["peak_input_low"] = low.get("input")
            mrow["peak_input_high"] = high.get("input")
            mrow["peak_output_low"] = low.get("output")
            mrow["peak_output_high"] = high.get("output")
            mrow["peak_cache_low"] = low.get("cache_hit")
            mrow["peak_cache_high"] = high.get("cache_hit")
            # rmb 版本（CNY 渲染用）
            mrow["peak_input_rmb_low"] = low.get("input_rmb")
            mrow["peak_input_rmb_high"] = high.get("input_rmb")
            mrow["peak_output_rmb_low"] = low.get("output_rmb")
            mrow["peak_output_rmb_high"] = high.get("output_rmb")
            # condition 去掉 peak，改为 source + 峰谷计费
            _, source, token = _split_condition(high.get("condition"))
            parts = []
            if source:
                parts.append(source)
            parts.append("峰谷计费")
            if token:
                parts.append(token)
            mrow["condition"] = " | ".join(parts) if parts else "峰谷计费"
            merged.append(mrow)
        else:
            for item in items:
                merged.append(item["row"])
    return merged


def _normalize_row(r: Dict[str, Any], canon: str, min_in: Optional[float], base_in: Optional[float] = None) -> Dict[str, Any]:
    in_rmb = r.get("input_rmb")
    is_low = in_rmb is not None and min_in is not None and in_rmb == min_in
    premium = None
    # 溢价基准 = 官网价（base_in），不在渠道供应商内部互相比较。
    # 无官网价基准时不显示溢价百分比。
    if not is_low and in_rmb is not None and base_in is not None and base_in > 0:
        premium = round((in_rmb - base_in) / base_in * 100, 1)
    sid = r.get("source") or "—"
    model_name = clean_model_name(r.get("model_raw"), fallback=canon)
    return {
        "model": model_name,
        "model_raw": model_name,  # 展示与导出统一用精简名，不保留杂讯尾巴
        "canonical": canon,
        "source": sid,
        "source_label": source_label(sid),
        "family": "国内",
        "input_rmb": in_rmb,
        "output_rmb": r.get("output_rmb"),
        "cache_hit": r.get("cache_hit"),
        "input": r.get("input"),
        "output": r.get("output"),
        "currency": r.get("currency") or "",
        "context": r.get("context"),
        "condition": r.get("condition"),
        "peak_input_low": r.get("peak_input_low"),
        "peak_input_high": r.get("peak_input_high"),
        "peak_output_low": r.get("peak_output_low"),
        "peak_output_high": r.get("peak_output_high"),
        "peak_cache_low": r.get("peak_cache_low"),
        "peak_cache_high": r.get("peak_cache_high"),
        "peak_input_rmb_low": r.get("peak_input_rmb_low"),
        "peak_input_rmb_high": r.get("peak_input_rmb_high"),
        "peak_output_rmb_low": r.get("peak_output_rmb_low"),
        "peak_output_rmb_high": r.get("peak_output_rmb_high"),
        "note": "",
        "is_lowest": is_low,
        "is_official": _is_official_any_currency(canon, r),
        "premium": premium,
        "region": "domestic",
    }


def _overseas_official_rows(rate: float) -> List[Dict[str, Any]]:
    """海外主流厂商官方 API 参考价（USD），按汇率换算 CNY 约价。

    数据来源已迁移到 config/mainstream_models.yml；此函数保留为兼容入口，
    供旧渲染代码和 Excel 导出使用，直到 Task 5 完全替换渲染层。
    """
    rows: List[Dict[str, Any]] = []
    try:
        catalog = mainstream_catalog.load_catalog(_CATALOG_PATH)
    except (OSError, ValueError):
        return rows
    rendered = mainstream_catalog.renderable_sections(catalog)
    order = {name: i for i, name in enumerate(MODEL_ORDER)}
    for vendor in rendered.get("overseas", []):
        sid = vendor.get("source_id") or vendor.get("id") or "—"
        fam = vendor.get("name") or source_label(sid)
        for model in vendor.get("models", []):
            pricing = model.get("pricing", {}) or {}
            tiers = pricing.get("tiers", []) or []
            tier0 = tiers[0] if tiers else {}
            inp = tier0.get("input_price")
            out = tier0.get("output_price")
            # 缓存命中在目录里写在 pricing.cache_input_price，不在 tier 内
            cache = pricing.get("cache_input_price")
            if cache is None:
                cache = tier0.get("cache_input_price")
            in_rmb = round(float(inp) * rate, 4) if isinstance(inp, (int, float)) else None
            out_rmb = round(float(out) * rate, 4) if isinstance(out, (int, float)) else None
            ctx = model.get("context_tokens")
            ctx_label = f"{ctx // 1000}K" if isinstance(ctx, int) and ctx >= 1000 else (str(ctx) if ctx else "—")
            rows.append(
                {
                    "model": model.get("display_name") or model.get("canonical") or "—",
                    "model_raw": model.get("display_name") or model.get("canonical") or "—",
                    "canonical": model.get("canonical") or "—",
                    "source": sid,
                    "source_label": source_label(sid),
                    "family": fam,
                    "input": inp,
                    "output": out,
                    "input_rmb": in_rmb,
                    "output_rmb": out_rmb,
                    "cache_hit": cache,
                    "currency": model.get("currency") or "USD",
                    "context": ctx_label,
                    "note": model.get("role") or "官方 API",
                    "hot": bool(model.get("featured")),
                    "is_lowest": False,
                    "is_official": True,
                    "premium": None,
                    "region": "overseas",
                }
            )
    rows.sort(
        key=lambda x: (
            _vendor_rank(x.get("source") or x.get("family"), "overseas"),
            order.get(x["canonical"], 1000),
            str(x.get("family") or ""),
            str(x.get("model") or "").lower(),
        )
    )
    return rows


def _context_label(tokens: Any) -> str:
    if not isinstance(tokens, int):
        return "—"
    if tokens >= 1000000 and tokens % 1000000 == 0:
        return f"{tokens // 1000000}M"
    if tokens >= 1000:
        return f"{tokens // 1000}K"
    return str(tokens)


def _official_live_prices(watchlist: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """从已抓取的官网记录提取 canonical → 入/出/缓存价，供卡片覆盖目录静态价。"""
    out: Dict[str, Dict[str, Any]] = {}
    for r in watchlist:
        if not isinstance(r, dict):
            continue
        canon = r.get("canonical")
        if not canon or not _is_official_row(str(canon), r):
            continue
        # 同型号多档（如 M3 ≤512K / 512K~1M）保留价格最低的一档作为默认展示，
        # 其余分档仍由 catalog 静态 tiers 或 rows 自行承担。
        inp = r.get("input")
        outp = r.get("output")
        if not isinstance(inp, (int, float)) or not isinstance(outp, (int, float)):
            continue
        prev = out.get(str(canon))
        if prev is not None and float(prev["input"]) <= float(inp):
            continue
        out[str(canon)] = {
            "input": float(inp),
            "output": float(outp),
            "cache_hit": r.get("cache_hit"),
            "context": r.get("context"),
        }
    return out


def _hydrate_catalog_prices(
    rendered: Dict[str, List[Dict[str, Any]]],
    live: Dict[str, Dict[str, Any]],
) -> None:
    """用最新抓取价覆盖目录静态价：输入/输出 + cache_input_price（缓存命中）。

    卡片区原先只读 config/mainstream_models.yml。官网解析器已抓到缓存价时，
    若目录未同步（如 Qwen 仍标 tracking 且无 cache），页面就会「有数据却不显示」。
    这里在渲染前把 live 官网价写回模型节点，并取消「待补」态。
    """
    for vendors in rendered.values():
        for vendor in vendors:
            for model in vendor.get("models", []) or []:
                if not isinstance(model, dict):
                    continue
                canon = model.get("canonical")
                if not canon or str(canon) not in live:
                    continue
                hit = live[str(canon)]
                pricing = model.setdefault("pricing", {})
                if not isinstance(pricing, dict):
                    pricing = {}
                    model["pricing"] = pricing
                tiers = pricing.get("tiers")
                if not isinstance(tiers, list) or not tiers:
                    tiers = [{"condition": "default"}]
                    pricing["tiers"] = tiers
                tier0 = tiers[0] if isinstance(tiers[0], dict) else {}
                if not isinstance(tiers[0], dict):
                    tiers[0] = tier0
                tier0["input_price"] = hit["input"]
                tier0["output_price"] = hit["output"]
                cache = hit.get("cache_hit")
                if isinstance(cache, (int, float)):
                    pricing["cache_input_price"] = float(cache)
                # 已有官网抓取 → 卡片按 official 展示，去掉「待补」
                if model.get("availability") in (None, "tracking", "preview"):
                    model["availability"] = "official"
                role = str(model.get("role") or "")
                if "待修复" in role or "渠道参考" in role:
                    model["role"] = role.replace("官方价格页待修复", "官方 API").replace(
                        "渠道参考价", "官方 API"
                    )


def _build_mainstream_sections(
    catalog: Dict[str, Any],
    channel_canons: set,
    watchlist: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """构建国内/海外主流卡片专区数据，附加展示字段。

    会用 watchlist 里最新官网价覆盖目录静态价（含缓存命中），
    避免「解析器已抓到、卡片还显示渠道参考/无缓存」。
    """
    rendered = mainstream_catalog.renderable_sections(catalog)
    live = _official_live_prices(watchlist or [])
    if live:
        _hydrate_catalog_prices(rendered, live)
    for section_id, vendors in rendered.items():
        for vendor in vendors:
            for model in vendor.get("models", []):
                tiers = model.get("pricing", {}).get("tiers", []) or []
                model["display_tier"] = tiers[0] if tiers else {}
                model["context_label"] = _context_label(model.get("context_tokens"))
                model["source_label"] = source_label(vendor.get("source_id") or vendor.get("id"))
                model["has_channel_price"] = model.get("canonical") in channel_canons
                model["tier_count"] = len(tiers)
    return rendered


def _load_history(data_dir: str, max_points: int = 90) -> Dict[str, Any]:
    """读取 data/history/*.json 快照，构建模型×渠道价格时间序列。

    每个快照文件名为 YYYY-MM-DD.json，内容为当日 prices.json 全量记录。
    返回结构：
    {
      "dates": ["2026-08-22", ...],                     # 升序日期
      "series": {                                        # canonical -> source -> {date: {input, output, currency}}
        "DeepSeek V4 Pro": {
          "deepseek": {"2026-08-22": {"input": 9.0, "output": 27.0, "currency": "CNY"}, ...},
          ...
        },
        ...
      }
    }
    若 history 目录不存在或无快照，返回空结构。
    """
    hist_dir = os.path.join(data_dir, "history")
    if not os.path.isdir(hist_dir):
        return {"dates": [], "series": {}}

    import glob
    files = sorted(glob.glob(os.path.join(hist_dir, "*.json")))
    if max_points and len(files) > max_points:
        files = files[-max_points:]  # 仅保留最近 N 天

    dates: List[str] = []
    series: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for fp in files:
        date_str = os.path.splitext(os.path.basename(fp))[0]  # YYYY-MM-DD
        try:
            with open(fp, encoding="utf-8") as f:
                snap = json.load(f)
        except (ValueError, OSError):
            continue
        if not isinstance(snap, list):
            continue
        dates.append(date_str)
        for r in snap:
            c = r.get("canonical")
            s = r.get("source")
            if not c or not s:
                continue
            series.setdefault(c, {}).setdefault(s, {})[date_str] = {
                "input": r.get("input"),
                "output": r.get("output"),
                "input_rmb": r.get("input_rmb"),
                "output_rmb": r.get("output_rmb"),
                "currency": r.get("currency"),
            }

    return {"dates": dates, "series": series}


def _build_site_data(data_dir: str) -> Dict[str, Any]:
    watchlist: List[Dict[str, Any]] = _load_json(os.path.join(data_dir, "watchlist.json")) or []
    if not isinstance(watchlist, list):
        watchlist = []

    # 兜底补齐 input_rmb/output_rmb 及 peak_*_rmb_* 字段。
    # prices.json/watchlist.json 由 main.py 的 currency.enrich 写出，正常情况已含 rmb 字段；
    # 但历史快照或手改数据可能缺 peak_*_rmb_*，这里再跑一次 enrich 保证下游动态峰谷时钟拿到正确值。
    try:
        currency.enrich(watchlist)
    except Exception:
        pass

    canons: List[str] = []
    for r in watchlist:
        c = r.get("canonical")
        if c and c not in canons:
            canons.append(c)
    canons = _sort_canons(canons)

    srcs: List[str] = []
    for r in watchlist:
        s = r.get("source")
        if s:
            srcs.append(s)
    sources = sorted(set(srcs))
    rate = currency.get_rate()
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str = generated_at.split(" ")[0]

    by_canon: Dict[str, List[Dict[str, Any]]] = {}
    for r in watchlist:
        c = r.get("canonical")
        if c:
            by_canon.setdefault(c, []).append(r)

    official_rows: List[Dict[str, Any]] = []
    channel_domestic: List[Dict[str, Any]] = []
    channel_overseas: List[Dict[str, Any]] = []
    chart: Dict[str, List[Dict[str, Any]]] = {}

    for c in canons:
        rows = by_canon.get(c, [])
        if not rows:
            continue
        # 渠道源：合并同一模型+来源的「空闲/高峰」峰谷双行为单行
        rows = _merge_peak_rows(rows)
        inputs: List[float] = []
        for r in rows:
            v = r.get("input_rmb")
            if v is not None:
                inputs.append(v)
        min_in = min(inputs) if inputs else None
        # 溢价基准：该模型自身的官网价（不在渠道供应商内部比较）。
        # DeepSeek 模型即 DeepSeek 官网价；其余模型取其对应官网价。无官网价则不显示溢价。
        # 版本后缀模型（如 DeepSeek V4 Pro 0813）回退到父模型官网价作为基准。
        parent_c = _CANON_PARENT.get(c)
        official_inputs: List[float] = []
        for r in rows:
            v = r.get("input_rmb")
            if v is not None and _is_official_any_currency(c, r):
                official_inputs.append(v)
        if not official_inputs and parent_c and parent_c in by_canon:
            for r in by_canon[parent_c]:
                v = r.get("input_rmb")
                if v is not None and _is_official_any_currency(parent_c, r):
                    official_inputs.append(v)
        base_in = min(official_inputs) if official_inputs else None
        norm = [_normalize_row(r, c, min_in, base_in) for r in rows]

        # 峰谷动态比价：提取官方「闲/高」两档基准价 + 渠道「闲/高」两档价，
        # 供前端按当前北京时间所在时段实时切换溢价基准。
        ofr = next((x for x in norm if x.get("is_official")), None)
        if ofr is None and parent_c and parent_c in by_canon:
            # 父模型官网行（含峰谷双档）作为基准
            for prow in by_canon[parent_c]:
                if _is_official_any_currency(parent_c, prow):
                    ofr = _normalize_row(prow, parent_c, None, None)
                    break
        official_off_in = base_in
        official_peak_in = None
        if ofr is not None:
            # 官方「闲时」价：优先 peak_input_rmb_low（CNY 换算），否则 peak_input_low
            # （原币种 CNY 时即人民币），最后回退主价 input_rmb。
            of_lo = (
                ofr.get("peak_input_rmb_low")
                if ofr.get("peak_input_rmb_low") is not None
                else ofr.get("peak_input_low")
            )
            official_off_in = of_lo if of_lo is not None else base_in
            official_peak_in = (
                ofr.get("peak_input_rmb_high")
                if ofr.get("peak_input_rmb_high") is not None
                else ofr.get("peak_input_high")
            )
        for x in norm:
            ch_peak = (
                x.get("peak_input_rmb_high")
                if x.get("peak_input_rmb_high") is not None
                else x.get("peak_input_high")
            )
            x["official_off_in"] = official_off_in
            x["official_peak_in"] = official_peak_in
            x["channel_off_in"] = x.get("input_rmb")
            x["channel_peak_in"] = ch_peak
            x["peak_sched"] = _source_peak_schedule(x.get("source"), x.get("canonical"))

        # 官方：官网源（保留原计费币种）。CNY 官网 → 国内官方表；USD 官网（如 DeepSeek 英文站）→ 海外官方表。
        official_cny = [x for x in norm if x["is_official"] and str(x["currency"]).upper() != "USD"]
        official_usd = [x for x in norm if x["is_official"] and str(x["currency"]).upper() == "USD"]
        # DeepSeek 英文站（deepseek_us, USD）也是官方标价，进海外区；其余厂商 USD 行若已化为 CNY 官网则去重
        for x in official_usd:
            already_cny = any(
                y["is_official"] and y["source"] == x["source"] and str(y["currency"]).upper() != "USD"
                for y in official_cny
            )
            if x["source"] == "deepseek_us" or not already_cny:
                official_rows.append(x)
        official_rows.extend(official_cny)

        # 渠道：非官网。按「结算币种」分区：USD 进海外面板；CNY 进国内面板。
        channels = [x for x in norm if not x["is_official"]]
        d_ch = [x for x in channels if str(x["currency"]).upper() != "USD"]
        o_ch = [x for x in channels if str(x["currency"]).upper() == "USD"]
        d_ch = sorted(d_ch, key=lambda x: (_price_key(x), x["source_label"], x["model"].lower()))
        o_ch = sorted(o_ch, key=lambda x: (_price_key(x), x["source_label"], x["model"].lower()))
        channel_domestic.extend(d_ch)
        channel_overseas.extend(o_ch)

        # 图表：官网（国内 CNY）+ 国内渠道
        chart_rows = [x for x in official_cny if str(x["currency"]).upper() != "USD"] + d_ch
        chart_rows = sorted(chart_rows, key=lambda x: (0 if x["is_official"] else 1, _price_key(x)))
        chart[c] = [
            {
                "source": r["source"],
                "source_label": r["source_label"],
                "model": r["model"],
                "input_rmb": r["input_rmb"],
                "output_rmb": r["output_rmb"],
                "currency": r["currency"],
                "is_official": r["is_official"],
            }
            for r in chart_rows
        ]

    # 官方表 / 渠道表：同厂聚合，厂内旗舰优先
    official_rows = sorted(official_rows, key=_official_sort_key)

    def _channel_sort(rows: List[Dict[str, Any]], region: str) -> List[Dict[str, Any]]:
        return sorted(
            rows,
            key=lambda x: (
                _vendor_rank(x.get("source"), region),
                _model_rank(x.get("canonical")),
                _price_key(x),
                x.get("source_label") or "",
                str(x.get("model") or "").lower(),
            ),
        )

    channel_domestic = _channel_sort(channel_domestic, "domestic")
    channel_overseas = _channel_sort(channel_overseas, "overseas")

    # Excel 导出兼容 groups：官方 + 渠道
    groups: List[Dict[str, Any]] = []
    for c in canons:
        o = [r for r in official_rows if r["canonical"] == c]
        d = [r for r in channel_domestic if r["canonical"] == c]
        ov = [r for r in channel_overseas if r["canonical"] == c]
        if o or d:
            groups.append({"canonical": c, "market": "domestic", "rows": o + d})
        if ov:
            groups.append({"canonical": c, "market": "overseas", "rows": ov})

    overseas_rows = _overseas_official_rows(rate)  # 汇率跟随 currency.get_rate()；前端改汇率后 JS 重算
    overseas_canons = [r["canonical"] for r in overseas_rows]

    # 主流模型目录（国内/海外双专区）
    try:
        catalog = mainstream_catalog.load_catalog(_CATALOG_PATH)
        catalog_all_canons = mainstream_catalog.catalog_canons(catalog)
        mainstream_sections = _build_mainstream_sections(
            catalog, set(canons), watchlist=watchlist
        )
        has_domestic_mainstream = bool(mainstream_sections.get("domestic"))
        has_overseas_mainstream = bool(mainstream_sections.get("overseas"))
    except (OSError, ValueError):
        catalog_all_canons = []
        mainstream_sections = {}
        has_domestic_mainstream = False
        has_overseas_mainstream = False

    all_canons = _sort_canons(list(dict.fromkeys(canons + overseas_canons + catalog_all_canons)))
    domestic_canons = [c for c in all_canons if c in DOMESTIC_MODELS or c in canons]
    global_canons = [c for c in all_canons if c in {x["canonical"] for x in overseas_rows} or c in catalog_all_canons]
    tracking_raw = _load_new_model_tracking()
    tracking = _merge_tracking_status(tracking_raw, canons, overseas_canons)

    channel_opts = [
        {"id": sid, "label": source_label(sid)}
        for sid in sorted(set(sources) | {"openai", "anthropic", "google"}, key=lambda x: source_label(x))
    ]

    return {
        "generated_at": generated_at,
        "rate": rate,
        "default_rate": rate,
        "filter_meta": {
            "models": all_canons,
            "all_models": all_canons,
            "domestic_models": domestic_canons,
            "overseas_models": global_canons,
            "deepseek_models": [c for c in all_canons if str(c).startswith("DeepSeek")],
            "channels": channel_opts,
        },
        "metrics": {
            "models": len(all_canons),
            "sources": len(set(sources) | {"openai", "anthropic", "google"}),
            "updated": date_str,
            "rate": rate,
            "official_count": len(official_rows),
            "overseas_count": len(overseas_rows),
            "channel_count": len(channel_domestic) + len(channel_overseas),
        },
        "official_rows": official_rows,
        "overseas_rows": overseas_rows,
        "channel_domestic": channel_domestic,
        "channel_overseas": channel_overseas,
        "groups": groups,
        "chart": chart,
        "canons": all_canons,
        "has_data": bool(watchlist) or bool(overseas_rows),
        "has_official": bool(official_rows),
        "has_overseas": bool(overseas_rows),
        "has_channel_domestic": bool(channel_domestic),
        "has_channel_overseas": bool(channel_overseas),
        "tracking": tracking,
        "has_tracking": bool(tracking),
        "mainstream_sections": mainstream_sections,
        "has_domestic_mainstream": has_domestic_mainstream,
        "has_overseas_mainstream": has_overseas_mainstream,
        "history": _load_history(data_dir),
    }
