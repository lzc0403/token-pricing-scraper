"""生成美化静态网页：读取 data/ 中的定价数据，输出自包含 site/index.html。

布局：
  Hero 指标
  → 顶部「厂商官网原价」独立区块
  → 下方「渠道比价」统一表格（国内 / 海外分页）
  → 图表 / Footer

规则：
  - 模型名仅保留名称本身，去掉批注、折扣说明、新品标记等杂讯
  - ModelMesh 展示为「胜算云」
  - DeepSeek 模型置顶
  - 国内 CNY 与海外 USD 分页，不合并
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
        import yaml  # type: ignore
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

    sources = sorted({r.get("source") for r in watchlist if r.get("source")})
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
        inputs = [r.get("input_rmb") for r in rows if r.get("input_rmb") is not None]
        min_in = min(inputs) if inputs else None
        # 溢价基准：该模型自身的官网价（不在渠道供应商内部比较）。
        # DeepSeek 模型即 DeepSeek 官网价；其余模型取其对应官网价。无官网价则不显示溢价。
        # 版本后缀模型（如 DeepSeek V4 Pro 0813）回退到父模型官网价作为基准。
        parent_c = _CANON_PARENT.get(c)
        official_inputs = [
            r.get("input_rmb") for r in rows
            if r.get("input_rmb") is not None and _is_official_any_currency(c, r)
        ]
        if not official_inputs and parent_c and parent_c in by_canon:
            official_inputs = [
                r.get("input_rmb") for r in by_canon[parent_c]
                if r.get("input_rmb") is not None and _is_official_any_currency(parent_c, r)
            ]
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
    }


def _stat_card(label: str, value: str, unit: str = "") -> str:
    unit_html = f"<small>{unit}</small>" if unit else ""
    return (
        f'<div class="stat-card">'
        f'<div class="label">{_esc(label)}</div>'
        f'<div class="value">{value}{unit_html}</div>'
        f"</div>"
    )


def _attr_num(v: Any) -> str:
    if v is None:
        return ""
    return _esc_attr(v)


def _peak_duo(low_val: Any, high_val: Any, fmt_cur: str = "") -> str:
    """峰谷双价 HTML：闲 X / 高 Y。low/high 均可为 None。

    闲时时段价为主价（默认优先展示），高峰价为附注。
    """
    lo = _fmt_num(low_val)
    hi = _fmt_num(high_val)
    cur = f'<span class="px-cur">{_esc(fmt_cur)}</span>' if fmt_cur else ""
    return (
        f'<span class="px-val px-peak"><span class="px-peak-lo">闲 {lo}</span>'
        f'<span class="px-peak-sep">/</span>'
        f'<span class="px-peak-hi">高 {hi}</span></span>{cur}'
    )


def _price_cells(r: Dict[str, Any], mode: str) -> Tuple[str, str, Any, Any]:
    """返回 (in_html, out_html, sort_in, sort_out)。mode: cny|usd

    若 row 含 peak_*_low/high 字段（峰谷计费合并行），渲染「闲 X / 高 Y」双价。
    """
    is_usd = mode == "usd" or str(r.get("currency") or "").upper() == "USD"
    has_peak = r.get("peak_input_low") is not None or r.get("peak_input_high") is not None
    if is_usd:
        cur = _esc(r.get("currency") or "USD")
        if has_peak:
            in_html = (
                f'{_peak_duo(r.get("peak_input_low"), r.get("peak_input_high"), cur)}'
                f'<div class="sub-hint js-rmb-hint" data-side="input">'
                f'约 ¥{_fmt_num(r.get("input_rmb"))}</div>'
            )
            out_html = (
                f'{_peak_duo(r.get("peak_output_low"), r.get("peak_output_high"), cur)}'
                f'<div class="sub-hint js-rmb-hint" data-side="output">'
                f'约 ¥{_fmt_num(r.get("output_rmb"))}</div>'
            )
        else:
            in_html = (
                f'<span class="px-val">{_fmt_num(r.get("input"))}</span>'
                f'<span class="px-cur">{cur}</span>'
                f'<div class="sub-hint js-rmb-hint" data-side="input">'
                f'约 ¥{_fmt_num(r.get("input_rmb"))}</div>'
            )
            out_html = (
                f'<span class="px-val">{_fmt_num(r.get("output"))}</span>'
                f'<span class="px-cur">{cur}</span>'
                f'<div class="sub-hint js-rmb-hint" data-side="output">'
                f'约 ¥{_fmt_num(r.get("output_rmb"))}</div>'
            )
        return (
            in_html,
            out_html,
            r.get("input") if r.get("input") is not None else "",
            r.get("output") if r.get("output") is not None else "",
        )
    # CNY mode
    if has_peak:
        # CNY 源原币种即 CNY，无 rmb 换算字段，fallback 到原币种 peak 值
        in_low = r.get("peak_input_rmb_low") if r.get("peak_input_rmb_low") is not None else r.get("peak_input_low")
        in_high = r.get("peak_input_rmb_high") if r.get("peak_input_rmb_high") is not None else r.get("peak_input_high")
        out_low = r.get("peak_output_rmb_low") if r.get("peak_output_rmb_low") is not None else r.get("peak_output_low")
        out_high = r.get("peak_output_rmb_high") if r.get("peak_output_rmb_high") is not None else r.get("peak_output_high")
        in_html = (
            f'<span class="js-cny-main px-val" data-side="input">'
            f'{_peak_duo(in_low, in_high)}'
            f'</span>'
        )
        out_html = (
            f'<span class="js-cny-main px-val" data-side="output">'
            f'{_peak_duo(out_low, out_high)}'
            f'</span>'
        )
        sort_in = in_low if in_low is not None else r.get("input_rmb")
        sort_out = out_low if out_low is not None else r.get("output_rmb")
        return in_html, out_html, sort_in if sort_in is not None else "", sort_out if sort_out is not None else ""
    return (
        f'<span class="js-cny-main px-val" data-side="input">{_fmt_num(r.get("input_rmb"))}</span>',
        f'<span class="js-cny-main px-val" data-side="output">{_fmt_num(r.get("output_rmb"))}</span>',
        r.get("input_rmb") if r.get("input_rmb") is not None else "",
        r.get("output_rmb") if r.get("output_rmb") is not None else "",
    )


def _table_row(r: Dict[str, Any], *, kind: str, price_mode: str) -> str:
    """kind: official|channel"""
    classes = ["data-row", "js-row"]
    if kind == "official" or r.get("is_official"):
        classes.append("is-official")
    if r.get("is_lowest") and kind == "channel":
        classes.append("is-lowest")
    cls = f' class="{" ".join(classes)}"'

    in_html, out_html, sort_in, sort_out = _price_cells(r, price_mode)
    tags = []
    if kind == "official" or r.get("is_official"):
        tags.append('<span class="tag tag-official">官网</span>')
    if r.get("region") == "overseas" or kind == "overseas":
        tags.append('<span class="tag tag-global">海外</span>')
    if r.get("hot") or str(r.get("canonical") or "") == "GPT-4o":
        tags.append('<span class="tag tag-hot">主流</span>')
    if r.get("family") and r.get("region") == "overseas":
        tags.append(f'<span class="tag tag-family">{_esc(r["family"])}</span>')
    if r.get("is_lowest"):
        tags.append('<span class="tag tag-best">最低</span>')
    if r.get("premium") is not None and kind == "channel" and not r.get("is_lowest"):
        tags.append(f'<span class="tag tag-premium js-premium" data-static="{r["premium"]}">+{r["premium"]}%</span>')
    tags_html = f'<div class="tags">{"".join(tags)}</div>' if tags else ""

    model = r.get("model") or clean_model_name(r.get("model_raw"), r.get("canonical", "—"))
    src = r.get("source_label") or source_label(r.get("source"))
    ctx = r.get("context") or "—"
    cur = r.get("currency") or "—"
    cache = _fmt_num(r.get("cache_hit"))
    canon = r.get("canonical") or ""
    sid = r.get("source") or ""
    cond = r.get("condition")
    cond_html = f'<span class="tag tag-cond">{_esc(cond)}</span>' if cond else ""
    src_html = f'<span class="pill">{_esc(src)}</span>{cond_html}'

    # 渠道行注入峰谷比价数据（供前端按当前时段动态切换溢价基准）
    peak_attrs = ""
    if kind == "channel":
        peak_attrs = (
            f' data-ch-off="{_attr_num(r.get("channel_off_in"))}"'
            f' data-ch-peak="{_attr_num(r.get("channel_peak_in"))}"'
            f' data-of-off="{_attr_num(r.get("official_off_in"))}"'
            f' data-of-peak="{_attr_num(r.get("official_peak_in"))}"'
            f' data-sched="{_esc_attr(r.get("peak_sched") or "")}"'
        )

    return f"""
      <tr{cls}{peak_attrs}
        data-canonical="{_esc_attr(canon)}"
        data-source="{_esc_attr(sid)}"
        data-currency="{_esc_attr(cur)}"
        data-input="{_attr_num(r.get("input"))}"
        data-output="{_attr_num(r.get("output"))}"
        data-input-rmb="{_attr_num(r.get("input_rmb"))}"
        data-output-rmb="{_attr_num(r.get("output_rmb"))}">
        <td class="c-model" data-sort="{_esc_attr(str(model).lower())}">
          <div class="model">{_esc(model)}</div>
          {tags_html}
        </td>
        <td class="c-source" data-sort="{_esc_attr(src)}">{src_html}</td>
        <td class="num c-price js-price-in" data-sort="{sort_in}">{in_html}</td>
        <td class="num c-price js-price-out" data-sort="{sort_out}">{out_html}</td>
        <td class="num c-cache">{cache}</td>
        <td class="c-ctx muted">{_esc(ctx)}</td>
        <td class="c-curr">{_esc(cur)}</td>
      </tr>"""


def _render_table(
    rows: List[Dict[str, Any]],
    *,
    kind: str,
    price_mode: str,
    empty_text: str,
    table_id: str,
) -> str:
    if not rows:
        return f'<div class="empty-mini">{_esc(empty_text)}</div>'
    body = "".join(_table_row(r, kind=kind, price_mode=price_mode) for r in rows)
    in_h = "输入价 (¥)" if price_mode == "cny" else "输入价"
    out_h = "输出价 (¥)" if price_mode == "cny" else "输出价"
    return f"""
    <div class="table-wrap" id="{_esc_attr(table_id)}">
      <table class="price-table">
        <colgroup>
          <col class="w-model"><col class="w-source">
          <col class="w-num"><col class="w-num"><col class="w-num"><col class="w-ctx"><col class="w-curr">
        </colgroup>
        <thead>
          <tr>
            <th class="sortable" data-key="model">模型</th>
            <th class="sortable" data-key="source">来源</th>
            <th class="sortable num" data-key="input">{in_h}</th>
            <th class="sortable num" data-key="output">{out_h}</th>
            <th class="num">缓存</th>
            <th>上下文</th>
            <th>货币</th>
          </tr>
        </thead>
        <tbody>{body}</tbody>
      </table>
    </div>"""


def _sidebar() -> str:
    return """
    <aside class="sidebar" id="sidebar" aria-label="筛选">
      <button type="button" class="sidebar-close" id="sidebarClose" aria-label="收起筛选">×</button>
      <button type="button" class="sidebar-collapse" id="sidebarCollapse" aria-label="折叠侧边栏">‹</button>
      <div class="sidebar-inner">
        <div class="sidebar-head">
          <span class="filter-kicker">FILTER &amp; FX</span>
          <h2 class="sidebar-title">筛选与汇率</h2>
        </div>

        <div class="sidebar-group">
          <div class="sx-group-head">
            <span class="sx-group-title">模型分类</span>
            <div class="mini-actions">
              <button type="button" class="linkish" data-scope="model" data-act="all">全选</button>
              <button type="button" class="linkish" data-scope="model" data-act="none">清空</button>
              <button type="button" class="linkish" data-scope="model" data-act="domestic">仅国内</button>
              <button type="button" class="linkish" data-scope="model" data-act="overseas">仅海外</button>
            </div>
          </div>
          <div id="modelChips" class="chip-row chip-row-scroll" role="group" aria-label="模型分类筛选"></div>
        </div>

        <div class="sidebar-group">
          <div class="sx-group-head">
            <span class="sx-group-title">渠道 / 来源</span>
            <div class="mini-actions">
              <button type="button" class="linkish" data-scope="channel" data-act="all">全选</button>
              <button type="button" class="linkish" data-scope="channel" data-act="none">清空</button>
            </div>
          </div>
          <div id="channelChips" class="chip-row chip-row-scroll" role="group" aria-label="渠道筛选"></div>
        </div>

        <div class="sidebar-group">
          <div class="sx-group-head">
            <span class="sx-group-title">汇率</span>
            <button type="button" id="fxReset" class="linkish">重置 7.0</button>
          </div>
          <div class="rate-input-wrap">
            <input id="fxRate" class="rate-input" type="number" inputmode="decimal" min="0.1" max="100" step="0.01" value="7.0" aria-describedby="fxHint">
            <span class="rate-suffix">¥/$</span>
          </div>
          <div id="fxHint" class="rate-hint">当前 <strong id="fxCurrent">7.00</strong></div>
        </div>

        <div class="sidebar-foot">
          <button type="button" id="filterReset" class="btn-filter-reset">重置筛选</button>
          <span class="visible-count" id="visibleCount">显示 0 行</span>
        </div>
        <div class="sidebar-actions">
          <button type="button" class="btn-filter-toggle" id="sidebarToggle" aria-label="收起筛选">≡ 收起</button>
          <button type="button" id="btnExcel" class="btn-export">⬇ 导出 Excel</button>
        </div>
        <button type="button" id="sidebarConfirm" class="btn-confirm">确认筛选 ✓</button>
      </div>
    </aside>
    """


def _filter_toolbar() -> str:
    return ""


def _official_section(rows: List[Dict[str, Any]], has: bool) -> str:
    table = _render_table(
        rows,
        kind="official",
        price_mode="cny",
        empty_text="暂无厂商官网原价数据。",
        table_id="tbl-official",
    )
    # 官方区说明：国内厂商官网价（含人民币站 + 海外官方站的美元标价）
    return f"""
    <section class="block-card block-official" aria-labelledby="official-title">
      <div class="block-head">
        <div>
          <div class="block-kicker">TOP · OFFICIAL</div>
          <h2 id="official-title" class="block-title">国内厂商官方定价</h2>
          <p class="block-desc">DeepSeek / 通义千问 / 智谱 GLM / Kimi / MiniMax / 豆包 官方 API 参考价。国内官网以人民币标价；部分厂商同时提供海外官方站（英文站 / Z.ai 等）美元标价，币种不同但均为厂商官方定价，一并列出作为基准。</p>
        </div>
        <span class="block-count">{len(rows)} 条</span>
      </div>
      {table if has else '<div class="empty-mini">暂无厂商官网原价数据。</div>'}
    </section>"""


def _tracking_section(items: List[Dict[str, Any]], has: bool) -> str:
    if not has:
        return ""
    cards = []
    for t in items:
        status = t.get("status") or "tracking"
        presence = t.get("presence") or ("已上榜" if status == "active" else "监听中")
        region = "国内" if t.get("region") == "domestic" else ("海外" if t.get("region") == "overseas" else _esc(t.get("region")))
        st_cls = "is-active" if status == "active" else "is-tracking"
        cards.append(
            f'<article class="track-card {st_cls}">'
            f'<div class="track-top"><span class="track-family">{_esc(t.get("family"))}</span>'
            f'<span class="track-status">{_esc(presence)}</span></div>'
            f'<div class="track-name">{_esc(t.get("canonical"))}</div>'
            f'<div class="track-meta"><span>{region}</span><span>优先级 {_esc(t.get("priority") or "normal")}</span></div>'
            f'<p class="track-note">{_esc(t.get("note") or "主动跟进新发布型号")}</p>'
            f'</article>'
        )
    return f"""
    <section class="block-card block-tracking" aria-labelledby="tracking-title">
      <div class="block-head">
        <div>
          <div class="block-kicker">PRICING GAP</div>
          <h2 id="tracking-title" class="block-title">定价待补监测</h2>
          <p class="block-desc">官网定价尚未抓取到的型号，依靠渠道报价先行展示；数据源更新后自动转为官方定价。</p>
        </div>
        <span class="block-count">{len(items)} 项</span>
      </div>
      <div class="track-grid">{''.join(cards)}</div>
    </section>"""


def _mainstream_section(
    section_id: str,
    title: str,
    vendors: List[Dict[str, Any]],
    *,
    accent: str = "domestic",
) -> str:
    """渲染国内/海外统一主流模型卡片专区。

    采用统一网格布局：所有厂商的型号在同一网格中展示，
    使用厂商色带（vendor stripe）标记每张卡片的来源，
    视觉整齐划一，消除各厂商子网格列数不一致的问题。

    排序规则：
      1) 同厂模型聚合连续（按目录 vendors 顺序 / 厂商序）
      2) 厂内按 MAINSTREAM_SORT_ORDER 旗舰优先
    日期统一时仅在顶部展示一次。
    价格紧凑为单行「入 X · 出 Y · 缓存 Z」。

    accent: domestic（青绿）或 overseas（蓝色）
    """
    total_models = sum(len(v.get("models", [])) for v in vendors)
    region = "overseas" if accent == "overseas" else "domestic"
    model_order = {name: i for i, name in enumerate(MAINSTREAM_SORT_ORDER)}

    # ---- 收集全部模型：同厂连续，厂内旗舰优先 ----
    flat_models: List[Dict[str, Any]] = []
    # 先按目录 vendors 既有顺序；若缺序再用厂商 id 排序兜底
    vendor_list = list(vendors)
    vendor_list.sort(
        key=lambda v: (
            _vendor_rank(v.get("id") or v.get("source_id"), region),
            str(v.get("id") or ""),
        )
    )
    for vendor in vendor_list:
        vid = vendor.get("id") or "—"
        vname = vendor.get("name") or vid
        models = list(vendor.get("models", []) or [])
        models.sort(
            key=lambda m: (
                model_order.get(m.get("canonical", ""), 9999),
                str(m.get("canonical") or ""),
            )
        )
        for model in models:
            model["_vid"] = vid
            model["_vname"] = vname
            flat_models.append(model)

    # ---- 日期去重检测 ----
    all_dates = set()
    for m in flat_models:
        d = (m.get("verified_at") or "")[:10]
        if d:
            all_dates.add(d)
    uniform_date = all_dates.pop() if len(all_dates) == 1 else ""

    # ---- 渲染卡片 ----
    all_cards: List[str] = []

    for idx, model in enumerate(flat_models):
        canon = model.get("canonical") or "—"
        display = model.get("display_name") or canon
        pricing = model.get("pricing") or {}
        tiers = pricing.get("tiers") or []
        cache_input = pricing.get("cache_input_price")
        ctx_label = model.get("context_label") or "—"
        ctx_tokens = model.get("context_tokens") or ""
        role = model.get("role") or ""
        inp = tiers[0].get("input_price") if tiers else None
        out = tiers[0].get("output_price") if tiers else None
        currency = model.get("currency") or ""
        has_channel = model.get("has_channel_price")
        featured = model.get("featured")
        vid = model.get("_vid", "—")
        vname = model.get("_vname", vid)

        # 价格：紧凑单行，标签+数值内联，竖线分隔（无边框格子）
        has_price = isinstance(inp, (int, float)) and isinstance(out, (int, float))
        cache_val = _fmt_num(cache_input) if isinstance(cache_input, (int, float)) else ""
        if has_price:
            sep = '<span class="ms-sep">|</span>'
            price_html = (
                f'<div class="ms-prices">'
                f'<span class="ms-pair"><span class="ms-plabel">输入</span><span class="ms-pval">{_fmt_num(inp)}</span></span>'
                f'{sep}'
                f'<span class="ms-pair"><span class="ms-plabel">输出</span><span class="ms-pval">{_fmt_num(out)}</span></span>'
            )
            if cache_val:
                price_html += (
                    f'{sep}'
                    f'<span class="ms-pair"><span class="ms-plabel">缓存命中</span><span class="ms-pval">{cache_val}</span></span>'
                )
            price_html += '</div>'
        else:
            price_html = '<div class="ms-prices ms-no-price"><span>价格待公布</span></div>'
        cache_html = ""
        # 上下文：并入 role 行，避免与右上角标签重复
        clean_ctx = _clean_ctx_label(ctx_tokens)
        role_text = role or ""
        if clean_ctx and "上下文" not in role_text:
            role_text = f"{role_text} · {clean_ctx} 上下文" if role_text else f"{clean_ctx} 上下文"
        tiers_html = ""
        if len(tiers) > 1:
            tiers_list = "".join(
                f'<li>{_esc(t.get("condition") or "—")}：'
                f"{_fmt_num(t.get('input_price'))} / {_fmt_num(t.get('output_price'))} {currency}</li>"
                for t in tiers
            )
            tiers_html = f'<details class="ms-tiers"><summary>分档（{len(tiers)}档）</summary><ul>{tiers_list}</ul></details>'

        channel_html = (
            '<span class="ms-channel-ok">渠道✓</span>'
            if has_channel
            else '<span data-empty-state="no-channel-price" class="ms-channel-empty">无渠道</span>'
        )
        hot_badge = '<span class="ms-featured">热</span>' if featured else ""
        availability = model.get("availability")
        is_pending = availability not in ("official", "preview")
        tracking_badge = '<span class="ms-tracking" title="官网定价尚未抓取，以下为渠道参考价">待补</span>' if is_pending else ""

        all_cards.append(
            f'<article class="model-pick" data-canonical="{_esc_attr(canon)}" '
            f'data-context="{_esc_attr(ctx_tokens)}" data-source="{_esc_attr(vid)}" '
            f'data-region="{_esc_attr(region)}" '
            f'data-i="{idx}" style="--i:{idx}" '
            f'tabindex="0" role="button" aria-label="筛选 {_esc(display)}">'
            f'<span class="ms-vendor-stripe" data-vendor="{_esc_attr(vid)}" aria-hidden="true"></span>'
            f'<div class="ms-model-head">'
            f'<span class="ms-model-name">{_esc(display)}{hot_badge}{tracking_badge}</span>'
            f'</div>'
            f'<div class="ms-role">{_esc(vname)} · {_esc(role_text)}</div>'
            f"{price_html}"
            f"{cache_html}"
            f"{tiers_html}"
            f'<div class="ms-meta">{channel_html}</div>'
            f"</article>"
        )

    accent_class = "ms-overseas" if accent == "overseas" else "ms-domestic"
    # 日期横幅 + 单位说明（区块级，不每张卡片重复）
    unit_note = "$ / Million Tokens" if accent == "overseas" else "元 / 百万 Token"
    date_banner = f'<div class="ms-date-banner">数据更新于 <b>{_esc(uniform_date)}</b> <span class="ms-unit-note">{unit_note}</span></div>' if uniform_date else ""

    desc = (
        "官方 API 参考价 · 点击卡片可联动下方渠道筛选。证据不足的型号不在此展示。"
        if accent == "domestic"
        else "OpenAI / Anthropic / Google / xAI 热门主力官方 API 参考价。仅展示 GPT-5 / GPT-4o / Claude / Gemini 等核心型号，不堆叠 mini / nano / lite 次级款。点击卡片联动海外渠道筛选。"
    )
    return f"""
    <section class="block-card block-mainstream {accent_class}" data-section="{section_id}-mainstream" aria-labelledby="{section_id}-mainstream-title">
      <div class="block-head">
        <div>
          <div class="block-kicker">{'DOMESTIC · MAINSTREAM' if accent == 'domestic' else 'GLOBAL · MAINSTREAM'}</div>
          <h2 id="{section_id}-mainstream-title" class="block-title">{_esc(title)}</h2>
          <p class="block-desc">{_esc(desc)}</p>
        </div>
        <div class="block-head-right">
          <span class="block-count">{total_models} 款</span>
        </div>
      </div>
      {date_banner}
      <div class="ms-unified-grid">{''.join(all_cards)}</div>
    </section>"""


def _overseas_section(rows: List[Dict[str, Any]], has: bool) -> str:
    """海外厂商官方定价表已弃用：海外主力模型在上方「海外主流大模型」卡片专区展示，此处不再重复列表。"""
    return ""


def _channel_section(data: Dict[str, Any]) -> str:
    domestic = _render_table(
        data.get("channel_domestic") or [],
        kind="channel",
        price_mode="cny",
        empty_text="暂无国内渠道报价。",
        table_id="tbl-channel-domestic",
    )
    overseas = _render_table(
        data.get("channel_overseas") or [],
        kind="channel",
        price_mode="usd",
        empty_text="暂无海外渠道报价。",
        table_id="tbl-channel-overseas",
    )
    # DeepSeek 峰谷定价说明：腾讯云国际站展示空闲/高峰双档合并价
    has_peak = any(
        r.get("peak_input_low") is not None or r.get("peak_input_high") is not None
        for r in (data.get("channel_overseas") or [])
    )
    # 峰谷说明：官方与阿里云国际站窗口相反，需标注错峰错位
    peak_note = """
        <div class="peak-note">
          <strong>峰谷计费说明</strong>
          <span>
            <b>DeepSeek 官方</b>：高峰 09:00–12:00、14:00–18:00（北京时间 UTC+8）全价，其余空闲减半。
            <b>阿里云国际站</b>：闲时 22:00–次日 08:00（同为 UTC+8）半价，其余忙时。
            两者窗口相反，<b>08–09 / 12–14 / 18–22 错峰时段一边闲、一边忙</b>，下方溢价比价会按各自当前时段实时计算，请勿直接横向比「闲/高」两档。
          </span>
        </div>"""
    return f"""
    <section class="block-card block-channel" aria-labelledby="channel-title">
      <div class="block-head">
        <div>
          <div class="block-kicker">CHANNELS</div>
          <h2 id="channel-title" class="block-title">渠道同类报价</h2>
          <p class="block-desc">各渠道（胜算云、腾讯云等）同类模型报价，样式与字段统一；国内 / 海外分页展示。</p>
        </div>
      </div>
      <div id="peak-clock" class="peak-clock" aria-live="polite"></div>
      <div class="market-tabs" role="tablist" aria-label="渠道报价市场">
        <button type="button" class="market-tab is-active" role="tab" aria-selected="true" data-market="domestic" id="tab-domestic">国内渠道</button>
        <button type="button" class="market-tab" role="tab" aria-selected="false" data-market="overseas" id="tab-overseas">海外渠道</button>
      </div>
      <div id="panel-domestic" class="market-panel is-active" role="tabpanel" aria-labelledby="tab-domestic">
        <p class="panel-hint">仅 CNY 报价 · 与上方官网原价同表结构，便于对照。</p>
        {domestic}
      </div>
      <div id="panel-overseas" class="market-panel" role="tabpanel" aria-labelledby="tab-overseas" hidden>
        <p class="panel-hint">仅 USD 报价 · 不与国内合并；旁注人民币约价。DeepSeek 峰谷价（闲/高双档）单行合并展示。</p>
        {peak_note}
        {overseas}
      </div>
    </section>"""


def _chart_section(canons: List[str], has_data: bool) -> str:
    if not has_data or not canons:
        return ""
    options = "".join(f'<option value="{_esc(c)}">{_esc(c)}</option>' for c in canons)
    return f"""
    <section class="block-card chart-card" aria-labelledby="chart-title">
      <div class="chart-head">
        <div>
          <h2 id="chart-title" class="block-title" style="margin:0">国内价格对比</h2>
          <p class="block-desc" style="margin:4px 0 0">官网 + 国内渠道 · ¥ / 1M tokens · 绿色为最低价</p>
        </div>
        <div class="chart-controls">
          <div class="seg" role="group" aria-label="价格维度">
            <button type="button" class="seg-btn is-active" data-metric="input" aria-pressed="true">输入价</button>
            <button type="button" class="seg-btn" data-metric="output" aria-pressed="false">输出价</button>
          </div>
          <select id="modelSelect" aria-label="选择模型">{options}</select>
        </div>
      </div>
      <div class="chart-wrap">
        <canvas id="priceChart" role="img" aria-label="价格柱状图"></canvas>
        <p id="chartLive" class="visually-hidden" aria-live="polite"></p>
      </div>
    </section>"""


# --------------------------------------------------------------------------- #
# 前端资源（独立文件管理，build 时内联保持单 HTML 部署）
# --------------------------------------------------------------------------- #
_SITE_DIR = os.path.dirname(os.path.abspath(__file__))
_ASSETS_ROOT = os.path.join(os.path.dirname(_SITE_DIR), "site", "assets")


def _load_asset(name: str) -> str:
    """读取 site/assets/ 下的前端资源文件。"""
    path = os.path.join(_ASSETS_ROOT, name)
    with open(path, encoding="utf-8") as f:
        return f.read()


def build_site(data_dir: str, out_path: str = None) -> str:
    if out_path is None:
        out_path = os.path.join(
            os.path.dirname(os.path.abspath(data_dir)), "site", "index.html"
        )
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    data = _build_site_data(data_dir)
    m = data["metrics"]
    canons = data.get("canons") or []

    metrics_html = "".join(
        [
            _stat_card("追踪模型", str(m["models"]), "个"),
            _stat_card("数据源", str(m["sources"]), "个"),
            _stat_card("官网原价", str(m.get("official_count", 0)), "条"),
            (
                '<div class="stat-card">'
                '<div class="label">汇率 USD→CNY</div>'
                '<div class="value" id="metricRate">7.00<small>¥/$</small></div>'
                "</div>"
            ),
        ]
    )

    filter_block = _sidebar()
    ms = data.get("mainstream_sections") or {}
    domestic_ms = _mainstream_section(
        "domestic", "国内主流大模型", ms.get("domestic") or [], accent="domestic"
    )
    overseas_ms = _mainstream_section(
        "overseas", "海外主流大模型", ms.get("overseas") or [], accent="overseas"
    )
    official_block = _official_section(data.get("official_rows") or [], data.get("has_official"))
    overseas_block = _overseas_section(data.get("overseas_rows") or [], data.get("has_overseas"))
    channel_block = _channel_section(data)
    chart_block = _chart_section(canons, bool(data.get("chart")))

    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    peak_json = json.dumps(
        {"schedules": PEAK_SCHEDULES, "channelSched": _CHANNEL_PEAK_SCHED},
        ensure_ascii=False,
    ).replace("</", "<\\/")
    js = _load_asset("app.js").replace("__SITE_DATA__", data_json).replace("__PEAK_DATA__", peak_json)
    css = _load_asset("style.css")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>大模型 Token 定价追踪</title>
<meta name="description" content="国内/海外主流大模型官方定价与渠道同类报价分区展示；支持模型筛选与自定义汇率。">
<meta name="theme-color" content="#2BAE85">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
  <body>
  <a href="#main" class="visually-hidden">跳到主要内容</a>
  <header class="hero">
    <div class="mesh" aria-hidden="true"></div>
    <div class="hero-inner">
      <span class="eyebrow">官网基准 · 渠道对照 · 可筛选</span>
      <h1>大模型 Token 定价追踪</h1>
      <p class="sub">顶部官网原价，下方渠道报价；支持 DeepSeek 模型与渠道组合筛选，汇率默认 7.0 可手动调整。</p>
    </div>
  </header>

  <div class="layout is-collapsed">
    {filter_block}
    <main class="container" id="main">
      <div class="sec-head">
        <div>
          <h2 class="section-title">定价总览</h2>
          <p class="section-sub">DeepSeek 置顶 · 筛选可组合 · 官网与渠道分区</p>
        </div>
      </div>
      <div class="sec-metrics">{metrics_html}</div>

      {domestic_ms}
      {overseas_ms}
      {official_block}
      {overseas_block}
      {channel_block}
      {chart_block}
    </main>
  </div>

  <button type="button" class="sidebar-reopen" id="sidebarReopen" aria-label="展开筛选">› 筛选</button>
  <div class="sidebar-backdrop" id="sidebarBackdrop"></div>

  <div class="portal">
    <h3>厂商价格查询入口</h3>
    <p class="ph">同一大模型厂商通常提供「人民币（国内官网）」与「美元（英文 / 国际站）」两套定价。下方按币种分色：<span style="color:#0a8043;font-weight:700">绿 ¥</span> 国内官网、<span style="color:#4338ca;font-weight:700">蓝 $</span> 英文 / 国际站。DeepSeek / Kimi / MiniMax 已补充美元定价入口。</p>
    <div class="portal-grid">
      <a class="portal-card" href="https://help.aliyun.com/zh/hologres/user-guide/managed-models-billing" target="_blank" rel="noopener">
        <span><span class="pc-name">阿里云</span><span class="pc-tag pc-tag-cny">国内站 ¥</span></span>
        <span class="pc-meta">Hologres 托管模型计费</span>
      </a>
      <a class="portal-card" href="https://modelstudio.console.alibabacloud.com/ap-southeast-1?tab=doc#/doc/?type=model&url=prices" target="_blank" rel="noopener">
        <span><span class="pc-name">阿里云</span><span class="pc-tag pc-tag-usd">国际站 $</span></span>
        <span class="pc-meta">Model Studio 定价</span>
      </a>
      <a class="portal-card" href="https://www.volcengine.com/docs/82379/1544106" target="_blank" rel="noopener">
        <span><span class="pc-name">火山引擎</span><span class="pc-tag pc-tag-cny">国内站 ¥</span></span>
        <span class="pc-meta">豆包模型计费</span>
      </a>
      <a class="portal-card" href="https://cloud.tencent.com/document/product/1823/130055" target="_blank" rel="noopener">
        <span><span class="pc-name">腾讯云</span><span class="pc-tag pc-tag-cny">国内站 ¥</span></span>
        <span class="pc-meta">TI 平台模型计费</span>
      </a>
      <a class="portal-card" href="https://www.tencentcloud.com/document/product/1300/78937" target="_blank" rel="noopener">
        <span><span class="pc-name">Tencent Cloud</span><span class="pc-tag pc-tag-usd">国际站 $</span></span>
        <span class="pc-meta">International Pricing</span>
      </a>
      <a class="portal-card" href="https://api-docs.deepseek.com/zh-cn/quick_start/pricing/" target="_blank" rel="noopener">
        <span><span class="pc-name">DeepSeek</span><span class="pc-tag pc-tag-cny">官网 ¥</span></span>
        <span class="pc-meta">API 定价</span>
      </a>
      <a class="portal-card" href="https://api-docs.deepseek.com/quick_start/pricing" target="_blank" rel="noopener">
        <span><span class="pc-name">DeepSeek</span><span class="pc-tag pc-tag-usd">官网 $</span></span>
        <span class="pc-meta">API Pricing (USD)</span>
      </a>
      <a class="portal-card" href="https://open.bigmodel.cn/pricing" target="_blank" rel="noopener">
        <span><span class="pc-name">智谱</span><span class="pc-tag pc-tag-cny">官网 ¥</span></span>
        <span class="pc-meta">GLM 定价</span>
      </a>
      <a class="portal-card" href="https://platform.minimaxi.com/subscribe/token-plan?tab=api-enterprise" target="_blank" rel="noopener">
        <span><span class="pc-name">MiniMax</span><span class="pc-tag pc-tag-cny">官网 ¥</span></span>
        <span class="pc-meta">Token 套餐</span>
      </a>
      <a class="portal-card" href="https://platform.minimax.io/docs/guides/pricing-paygo" target="_blank" rel="noopener">
        <span><span class="pc-name">MiniMax</span><span class="pc-tag pc-tag-usd">官网 $</span></span>
        <span class="pc-meta">Pay-as-You-Go (USD)</span>
      </a>
      <a class="portal-card" href="https://platform.kimi.com/docs/pricing/chat-k3" target="_blank" rel="noopener">
        <span><span class="pc-name">Kimi</span><span class="pc-tag pc-tag-cny">官网 ¥</span></span>
        <span class="pc-meta">K 系列定价</span>
      </a>
      <a class="portal-card" href="https://platform.moonshot.ai/" target="_blank" rel="noopener">
        <span><span class="pc-name">Kimi</span><span class="pc-tag pc-tag-usd">官网 $</span></span>
        <span class="pc-meta">Kimi API Platform (USD)</span>
      </a>
      <a class="portal-card" href="https://openai.com/api/pricing/" target="_blank" rel="noopener">
        <span><span class="pc-name">OpenAI</span><span class="pc-tag pc-tag-usd">官网 $</span></span>
        <span class="pc-meta">API Pricing</span>
      </a>
      <a class="portal-card" href="https://www.anthropic.com/pricing" target="_blank" rel="noopener">
        <span><span class="pc-name">Anthropic</span><span class="pc-tag pc-tag-usd">官网 $</span></span>
        <span class="pc-meta">Claude Pricing</span>
      </a>
      <a class="portal-card" href="https://ai.google.dev/pricing" target="_blank" rel="noopener">
        <span><span class="pc-name">Google</span><span class="pc-tag pc-tag-usd">官网 $</span></span>
        <span class="pc-meta">Gemini Pricing</span>
      </a>
      <a class="portal-card" href="https://global.modelmesh.info/model" target="_blank" rel="noopener">
        <span><span class="pc-name">胜算云</span><span class="pc-tag pc-tag-cny">渠道 ¥</span></span>
        <span class="pc-meta">聚合渠道</span>
      </a>
      <a class="portal-card" href="https://openrouter.ai/models" target="_blank" rel="noopener">
        <span><span class="pc-name">OpenRouter</span><span class="pc-tag pc-tag-usd">渠道 $</span></span>
        <span class="pc-meta">聚合渠道</span>
      </a>
    </div>
  </div>

  <footer>
    <div class="note">数据来源：国内厂商官网公开定价；OpenAI / Anthropic / Google 官方 API 参考价；胜算云、腾讯云、火山引擎等渠道报价。USD 结算的渠道归入海外渠道页。国内厂商（DeepSeek / Kimi / MiniMax 等）同时提供人民币与美元官方定价，上方入口已分别给出中文(¥)与英文($)链接。GitHub Action 每周自动抓取。</div>
    <div class="disc">⚠️ 仅供参考，请以各官网实时报价为准 · 最近更新：{_esc(data['generated_at'])}</div>
  </footer>
  <button type="button" id="toTop" class="totop" aria-label="回到顶部">↑</button>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>
  <script>{js}</script>
</body>
</html>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return os.path.abspath(out_path)
