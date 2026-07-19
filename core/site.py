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
    "tencent": "腾讯云",
    "bigmodel": "智谱",
    "deepseek": "DeepSeek",
    "minimax": "MiniMax",
    "kimi": "Kimi",
    "modelmesh": "胜算云",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google": "Google",
    "openrouter": "OpenRouter",
}

# 厂商官网（官方原价）来源
OFFICIAL_SOURCE: Dict[str, str] = {
    "DeepSeek V4 Pro": "deepseek",
    "DeepSeek V4 Flash": "deepseek",
    "DeepSeek V3.2": "deepseek",
    "GLM-5.1": "bigmodel",
    "GLM-5.2": "bigmodel",
    "Kimi K2.6": "kimi",
    "MiniMax M2.7": "minimax",
    "Seedance 2.0": "volcengine",
    "qwen3.7": "aliyun",
}

# 渠道源：非官网聚合/转售渠道
CHANNEL_SOURCES = {"modelmesh", "tencent", "openrouter", "volcengine", "aliyun"}

# 渠道按「结算币种」分区：USD 结算 = 海外渠道面板；CNY/无标价 = 国内渠道面板。
# 腾讯云/火山引擎等国内云厂商也可能以 USD 对外报价（如跨境实例），一律归入海外。

# 主流模型排序：按发布时间/技术先进性降序（越新越强排越前）
# 依据：Kimi K3(2026-07-17) > GLM-5.2(2026-06-17) > DeepSeek V4 Pro > V4 Flash > V3.2
MAINSTREAM_SORT_ORDER: List[str] = [
    # 国内 — 按技术先进性
    "Kimi K3",
    "GLM-5.2",
    "GLM-5.1",
    "DeepSeek V4 Pro",
    "DeepSeek V4 Flash",
    "DeepSeek V3.2",
    "MiniMax M3",
    "Doubao Seed 2.1 Pro",
    "Doubao Seed 2.1 Turbo",
    "MiniMax M2.7",
    "Kimi K2.7 Code",
    "Kimi K2.6",
    "Qwen3.7 Max",
    "Qwen3.7 Plus",
    # 海外 — GPT/Claude/Gemini 旗舰优先
    "GPT-5.6 Sol",
    "Claude Fable 5",
    "GPT-5.6 Terra",
    "Claude Opus 4.8",
    "GPT-5.6 Luna",
    "Claude Sonnet 5",
    "GPT-4o",
    "Claude Haiku 4.5",
    "Gemini 3.5 Pro",
    "Gemini 3.5 Flash",
]

MODEL_ORDER: List[str] = [
    # 国内主力
    "DeepSeek V4 Pro",
    "DeepSeek V4 Flash",
    "DeepSeek V3.2",
    "GLM-5.1",
    "GLM-5.2",
    "Kimi K2.6",
    "Kimi K3",
    "MiniMax M2.7",
    "MiniMax M3",
    "Seedance 2.0",
    "qwen3.7",
    # 海外最主流（只保留热门旗舰/主力）
    "GPT-5",
    "GPT-4o",
    "Claude Opus 4.8",
    "Claude Sonnet 5",
    "Claude 5",
    "Gemini 2.5 Pro",
    "Gemini 2.5 Flash",
]

# 国内模型（筛选用：仅国内模型）
DOMESTIC_MODELS = {
    "DeepSeek V4 Pro",
    "DeepSeek V4 Flash",
    "DeepSeek V3.2",
    "GLM-5.1",
    "GLM-5.2",
    "Kimi K2.6",
    "Kimi K3",
    "MiniMax M2.7",
    "MiniMax M3",
    "Seedance 2.0",
    "qwen3.7",
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


def _is_channel_row(r: Dict[str, Any]) -> bool:
    return str(r.get("source") or "") in CHANNEL_SOURCES


def _sort_canons(canons: List[str]) -> List[str]:
    order = {name: i for i, name in enumerate(MODEL_ORDER)}
    return sorted(canons, key=lambda c: (order.get(c, 1000), c))


def _price_key(r: Dict[str, Any]) -> float:
    v = r.get("input_rmb")
    if v is None:
        v = r.get("input")
    return float(v) if isinstance(v, (int, float)) else 1e18


def _normalize_row(r: Dict[str, Any], canon: str, min_in: Optional[float]) -> Dict[str, Any]:
    in_rmb = r.get("input_rmb")
    is_low = in_rmb is not None and min_in is not None and in_rmb == min_in
    premium = None
    if not is_low and in_rmb is not None and min_in is not None and min_in > 0:
        premium = round((in_rmb - min_in) / min_in * 100, 1)
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
        "note": "",
        "is_lowest": is_low,
        "is_official": _is_official_row(canon, r),
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
            tiers = model.get("pricing", {}).get("tiers", []) or []
            tier0 = tiers[0] if tiers else {}
            inp = tier0.get("input_price")
            out = tier0.get("output_price")
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
    rows.sort(key=lambda x: (order.get(x["canonical"], 1000), x["family"], x["model"].lower()))
    return rows


def _context_label(tokens: Any) -> str:
    if not isinstance(tokens, int):
        return "—"
    if tokens >= 1000000 and tokens % 1000000 == 0:
        return f"{tokens // 1000000}M"
    if tokens >= 1000:
        return f"{tokens // 1000}K"
    return str(tokens)


def _build_mainstream_sections(
    catalog: Dict[str, Any],
    channel_canons: set,
) -> Dict[str, List[Dict[str, Any]]]:
    """构建国内/海外主流卡片专区数据，附加展示字段。"""
    rendered = mainstream_catalog.renderable_sections(catalog)
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
        inputs = [r.get("input_rmb") for r in rows if r.get("input_rmb") is not None]
        min_in = min(inputs) if inputs else None
        norm = [_normalize_row(r, c, min_in) for r in rows]

        # 官方：官网源
        official = [x for x in norm if x["is_official"] and not _is_overseas({"currency": x["currency"]})]
        # 若官网无国内 CNY，取官网任意币种
        if not official:
            official = [x for x in norm if x["is_official"]]
        # 官方块按模型名排序（同模型多规格）
        official = sorted(official, key=lambda x: (x["model"].lower(), _price_key(x)))
        official_rows.extend(official)

        # 渠道：非官网。按「结算币种」分区：USD 进海外面板；CNY 进国内面板。
        channels = [x for x in norm if not x["is_official"]]
        d_ch = [x for x in channels if str(x["currency"]).upper() != "USD"]
        o_ch = [x for x in channels if str(x["currency"]).upper() == "USD"]
        d_ch = sorted(d_ch, key=lambda x: (_price_key(x), x["source_label"], x["model"].lower()))
        o_ch = sorted(o_ch, key=lambda x: (_price_key(x), x["source_label"], x["model"].lower()))
        channel_domestic.extend(d_ch)
        channel_overseas.extend(o_ch)

        # 图表：官网 + 国内渠道
        chart_rows = [x for x in official if str(x["currency"]).upper() != "USD"] + d_ch
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

    # 渠道表按模型序再按价格
    order = {name: i for i, name in enumerate(MODEL_ORDER)}

    def _channel_sort(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(
            rows,
            key=lambda x: (
                order.get(x["canonical"], 1000),
                _price_key(x),
                x["source_label"],
                x["model"].lower(),
            ),
        )

    channel_domestic = _channel_sort(channel_domestic)
    channel_overseas = _channel_sort(channel_overseas)

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

    overseas_rows = _overseas_official_rows(7.0)  # 默认汇率 7.0 约价；前端改汇率后 JS 重算
    overseas_canons = [r["canonical"] for r in overseas_rows]

    # 主流模型目录（国内/海外双专区）
    try:
        catalog = mainstream_catalog.load_catalog(_CATALOG_PATH)
        catalog_all_canons = mainstream_catalog.catalog_canons(catalog)
        mainstream_sections = _build_mainstream_sections(catalog, set(canons))
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
        "default_rate": 7.0,
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


def _price_cells(r: Dict[str, Any], mode: str) -> Tuple[str, str, Any, Any]:
    """返回 (in_html, out_html, sort_in, sort_out)。mode: cny|usd"""
    if mode == "usd" or str(r.get("currency") or "").upper() == "USD":
        in_main = f'{_fmt_num(r.get("input"))} {r.get("currency") or "USD"}'
        out_main = f'{_fmt_num(r.get("output"))} {r.get("currency") or "USD"}'
        in_html = (
            f'{in_main}<div class="sub-hint js-rmb-hint" data-side="input">'
            f'约 ¥{_fmt_num(r.get("input_rmb"))}</div>'
        )
        out_html = (
            f'{out_main}<div class="sub-hint js-rmb-hint" data-side="output">'
            f'约 ¥{_fmt_num(r.get("output_rmb"))}</div>'
        )
        return (
            in_html,
            out_html,
            r.get("input") if r.get("input") is not None else "",
            r.get("output") if r.get("output") is not None else "",
        )
    return (
        f'<span class="js-cny-main" data-side="input">{_fmt_num(r.get("input_rmb"))}</span>',
        f'<span class="js-cny-main" data-side="output">{_fmt_num(r.get("output_rmb"))}</span>',
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
        tags.append(f'<span class="tag tag-premium">+{r["premium"]}%</span>')
    tags_html = f'<div class="tags">{"".join(tags)}</div>' if tags else ""

    model = r.get("model") or clean_model_name(r.get("model_raw"), r.get("canonical", "—"))
    src = r.get("source_label") or source_label(r.get("source"))
    ctx = r.get("context") or "—"
    cur = r.get("currency") or "—"
    cache = _fmt_num(r.get("cache_hit"))
    canon = r.get("canonical") or ""
    sid = r.get("source") or ""

    return f"""
      <tr{cls}
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
        <td class="c-canon muted" data-sort="{_esc_attr(str(canon).lower())}">{_esc(canon or "—")}</td>
        <td class="c-source" data-sort="{_esc_attr(src)}"><span class="pill">{_esc(src)}</span></td>
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
          <col class="w-model"><col class="w-canon"><col class="w-source">
          <col class="w-num"><col class="w-num"><col class="w-num"><col class="w-ctx"><col class="w-curr">
        </colgroup>
        <thead>
          <tr>
            <th class="sortable" data-key="model">模型</th>
            <th class="sortable" data-key="canon">分组</th>
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
          <button type="button" id="filterReset" class="btn-filter-reset">重置全部筛选</button>
          <span class="visible-count" id="visibleCount">显示 0 行</span>
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
    return f"""
    <section class="block-card block-official" aria-labelledby="official-title">
      <div class="block-head">
        <div>
          <div class="block-kicker">TOP · OFFICIAL</div>
          <h2 id="official-title" class="block-title">厂商官网原价</h2>
          <p class="block-desc">大模型厂商官网公开报价，作为基准参考；模型名已精简，仅保留名称本身。</p>
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

    排序按 MAINSTREAM_SORT_ORDER（发布时间/技术先进性）。
    日期统一时仅在顶部展示一次。
    价格紧凑为单行「入 X · 出 Y · 缓存 Z」。

    accent: domestic（青绿）或 overseas（蓝色）
    """
    total_models = sum(len(v.get("models", [])) for v in vendors)

    # ---- 收集全部模型并排序 ----
    flat_models: List[Dict[str, Any]] = []
    for vendor in vendors:
        vid = vendor.get("id") or "—"
        vname = vendor.get("name") or vid
        for model in vendor.get("models", []):
            model["_vid"] = vid
            model["_vname"] = vname
            flat_models.append(model)

    # 按 MAINSTREAM_SORT_ORDER 排序，未列出的排最后
    order_map = {name: i for i, name in enumerate(MAINSTREAM_SORT_ORDER)}
    flat_models.sort(key=lambda m: order_map.get(m.get("canonical", ""), 9999))

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

        # 价格：输入 / 输出 / 缓存命中 三个同级列（单位移入卡片右上角）
        unit_label = "元 / 百万 Token" if currency == "CNY" else "$ / Million Tokens"
        has_price = isinstance(inp, (int, float)) and isinstance(out, (int, float))
        cache_val = _fmt_num(cache_input) if isinstance(cache_input, (int, float)) else "—"
        if has_price:
            price_html = (
                f'<div class="ms-prices">'
                f'<div class="ms-pcol"><span class="ms-plabel">输入</span><span class="ms-pval">{_fmt_num(inp)}</span></div>'
                f'<div class="ms-pcol"><span class="ms-plabel">输出</span><span class="ms-pval">{_fmt_num(out)}</span></div>'
                f'<div class="ms-pcol"><span class="ms-plabel">缓存命中</span><span class="ms-pval">{cache_val}</span></div>'
                f'</div>'
            )
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
            f'data-i="{idx}" style="--i:{idx}" '
            f'tabindex="0" role="button" aria-label="筛选 {_esc(display)}">'
            f'<span class="ms-vendor-stripe" data-vendor="{_esc_attr(vid)}" aria-hidden="true"></span>'
            f'<div class="ms-model-head">'
            f'<span class="ms-model-name">{_esc(display)}{hot_badge}{tracking_badge}</span>'
            f'<span class="ms-unit-badge">{_esc(unit_label)}</span>'
            f'</div>'
            f'<div class="ms-role">{_esc(vname)} · {_esc(role_text)}</div>'
            f"{price_html}"
            f"{cache_html}"
            f"{tiers_html}"
            f'<div class="ms-meta">{channel_html}</div>'
            f"</article>"
        )

    accent_class = "ms-overseas" if accent == "overseas" else "ms-domestic"
    # 日期横幅：仅当所有卡片日期一致时显示
    date_banner = f'<div class="ms-date-banner">数据更新于 <b>{_esc(uniform_date)}</b></div>' if uniform_date else ""

    return f"""
    <section class="block-card block-mainstream {accent_class}" data-section="{section_id}-mainstream" aria-labelledby="{section_id}-mainstream-title">
      <div class="block-head">
        <div>
          <div class="block-kicker">{'DOMESTIC · MAINSTREAM' if accent == 'domestic' else 'GLOBAL · MAINSTREAM'}</div>
          <h2 id="{section_id}-mainstream-title" class="block-title">{_esc(title)}</h2>
          <p class="block-desc">官方 API 参考价 · 点击卡片可联动下方渠道筛选。证据不足的型号不在此展示。</p>
        </div>
        <div class="block-head-right">
          <span class="block-count">{total_models} 款</span>
        </div>
      </div>
      {date_banner}
      <div class="ms-unified-grid">{''.join(all_cards)}</div>
    </section>"""


def _overseas_section(rows: List[Dict[str, Any]], has: bool) -> str:
    table = _render_table(
        rows,
        kind="overseas",
        price_mode="usd",
        empty_text="暂无海外主流模型参考价。",
        table_id="tbl-overseas",
    )
    # 顶栏高亮：只强调最主流（含 GPT-4o）
    highlight = []
    for r in rows:
        if r.get("canonical") in {"GPT-5", "GPT-4o", "Claude Sonnet 5", "Gemini 2.5 Pro"}:
            highlight.append(
                f'<div class="hot-card" data-source="{_esc_attr(r.get("source"))}">'
                f'<div class="hot-brand">{_esc(r.get("family") or r.get("source_label"))}</div>'
                f'<div class="hot-name">{_esc(r.get("model"))}</div>'
                f'<div class="hot-price"><span>$ {_fmt_num(r.get("input"))}</span><small>输入 / 1M</small></div>'
                f'<div class="hot-price muted"><span>$ {_fmt_num(r.get("output"))}</span><small>输出 / 1M</small></div>'
                f'</div>'
            )
    highlight_html = f'<div class="hot-strip">{"".join(highlight)}</div>' if highlight else ""
    families = sorted({r.get("family") or r.get("source_label") for r in rows if r})
    fam_text = " · ".join(families) if families else "OpenAI · Claude · Gemini"
    return f"""
    <section class="block-card block-overseas" aria-labelledby="overseas-title">
      <div class="block-head">
        <div>
          <div class="block-kicker">GLOBAL · HOT ONLY</div>
          <h2 id="overseas-title" class="block-title">海外主流大模型</h2>
          <p class="block-desc">只展示最热门主力：<strong>GPT-5 / GPT-4o / Claude / Gemini</strong> 官方 API 参考价。不堆叠 mini / nano / lite 次级型号。</p>
        </div>
        <div class="block-head-right">
          <span class="block-count">{len(rows)} 条</span>
          <span class="block-fam">{_esc(fam_text)}</span>
        </div>
      </div>
      <div class="family-strip" aria-hidden="true">
        <span class="fam-chip fam-openai">OpenAI · 含 GPT-4o</span>
        <span class="fam-chip fam-claude">Claude</span>
        <span class="fam-chip fam-gemini">Gemini</span>
      </div>
      {highlight_html}
      {table if has else '<div class="empty-mini">暂无海外主流模型参考价。</div>'}
      <p class="panel-hint overseas-note">价格为官方公开标准档参考，可能调整；GPT-4o 作为高频主力必须保留展示。</p>
    </section>"""


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
    return f"""
    <section class="block-card block-channel" aria-labelledby="channel-title">
      <div class="block-head">
        <div>
          <div class="block-kicker">CHANNELS</div>
          <h2 id="channel-title" class="block-title">渠道同类报价</h2>
          <p class="block-desc">各渠道（胜算云、腾讯云等）同类模型报价，样式与字段统一；国内 / 海外分页展示。</p>
        </div>
      </div>
      <div class="market-tabs" role="tablist" aria-label="渠道报价市场">
        <button type="button" class="market-tab is-active" role="tab" aria-selected="true" data-market="domestic" id="tab-domestic">国内渠道</button>
        <button type="button" class="market-tab" role="tab" aria-selected="false" data-market="overseas" id="tab-overseas">海外渠道</button>
      </div>
      <div id="panel-domestic" class="market-panel is-active" role="tabpanel" aria-labelledby="tab-domestic">
        <p class="panel-hint">仅 CNY 报价 · 与上方官网原价同表结构，便于对照。</p>
        {domestic}
      </div>
      <div id="panel-overseas" class="market-panel" role="tabpanel" aria-labelledby="tab-overseas" hidden>
        <p class="panel-hint">仅 USD 报价 · 不与国内合并；旁注人民币约价。</p>
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


_CSS = """
:root{
  --primary:#2BAE85; --primary-deep:#1a9e72; --primary-soft:#e8f8f2;
  --brand-dark:#0f172a;
  --green:#22c55e; --green-soft:#e8f8f2; --green-deep:#16a34a;
  --amber:#f59e0b; --amber-soft:#fff8e7;
  --red:#ef4444; --red-soft:#fef2f2;
  --canvas:#f8fafb; --bg:#ffffff; --line:#e2e8f0;
  --ink:#1e293b; --ink2:#475569; --mute:#64748b;
  --shadow:0 1px 3px rgba(0,0,0,.06);
  --r:10px;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth;overflow-x:clip}
body{margin:0;font-family:Inter,'Noto Sans SC',system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
  background:var(--bg);color:var(--ink);-webkit-font-smoothing:antialiased;line-height:1.5;overflow-x:clip;font-size:13px}
.visually-hidden{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);border:0}
:focus-visible{outline:2px solid var(--primary);outline-offset:2px}

.hero{background:linear-gradient(135deg,#e8f8f2 0%,#d4f0e7 100%);position:relative;overflow:hidden}
.hero .mesh{position:absolute;inset:0;background:radial-gradient(40% 50% at 15% 20%, rgba(43,174,133,.10), transparent 60%),radial-gradient(40% 50% at 85% 15%, rgba(43,174,133,.06), transparent 60%)}
.hero-inner{position:relative;z-index:1;max-width:1160px;margin:0 auto;padding:20px 24px 16px}
.eyebrow{display:none}
.hero h1{color:#0f172a;font-size:18px;margin:0 0 2px;font-weight:800;letter-spacing:-.01em}
.hero .sub{color:rgba(15,23,42,.55);margin:0;font-size:12px}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:12px}
.stat-card{background:#fff;border-radius:8px;padding:8px 10px;border:1px solid var(--line)}
.stat-card .label{color:var(--mute);font-size:11px;margin-bottom:2px}
.stat-card .value{color:var(--primary);font-size:16px;font-weight:800;font-variant-numeric:tabular-nums}
.stat-card .value small{font-size:11px;color:var(--mute);margin-left:4px;font-weight:600}

.container{max-width:1160px;margin:0 auto;padding:16px 24px 40px;min-width:0}

.layout{display:grid;grid-template-columns:260px minmax(0,1fr);gap:16px;align-items:start;min-width:0;transition:grid-template-columns .25s,gap .25s}
.layout.is-collapsed{grid-template-columns:0 minmax(0,1fr);gap:0}
.layout.is-collapsed .sidebar{width:0;padding:0;border:none;overflow:hidden;opacity:0;transform:translateX(-100%)}

.sidebar{position:sticky;top:12px;background:#fff;border:1px solid var(--line);border-radius:var(--r);max-height:calc(100vh - 24px);display:flex;flex-direction:column;overflow:hidden;min-width:0;transition:opacity .25s,transform .25s}
.sidebar.is-peek{box-shadow:0 0 0 2px rgba(43,174,133,.25),0 4px 20px rgba(0,0,0,.12)}
.sidebar-inner{padding:12px;overflow-y:auto;flex:1}
.sidebar-close{display:none}
.sidebar-collapse{display:none;position:absolute;top:8px;right:8px;width:24px;height:24px;border-radius:6px;border:1px solid var(--line);background:#fff;font-size:15px;font-weight:700;color:var(--mute);cursor:pointer;z-index:10;text-align:center;line-height:1}
.sidebar-collapse:hover{color:var(--primary);border-color:var(--primary)}
@media (min-width:1025px){.sidebar-collapse{display:inline-block}}
.sidebar-head{margin-bottom:12px}
.sidebar-title{margin:2px 0 0;font-size:14px;font-weight:800;color:#0f172a}
.sidebar-group{margin-bottom:14px}
.sx-group-head{display:flex;justify-content:space-between;align-items:center;gap:6px;margin-bottom:6px}
.sx-group-title{font-size:11px;font-weight:800;color:var(--mute);text-transform:uppercase;letter-spacing:.06em}
.sidebar-group .mini-actions{display:flex;gap:4px;flex-wrap:wrap}
.sidebar-group .linkish{font-size:10px;color:var(--primary)}
.chip-row-scroll{max-height:200px;overflow-y:auto;padding-right:2px}
.sidebar-group .rate-input-wrap{margin-bottom:2px}
.sidebar-group .rate-suffix{font-size:12px;font-weight:700;color:var(--mute)}
.sidebar-foot{margin-top:6px;padding-top:8px;border-top:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;gap:6px}
.btn-filter-reset{font-size:11px;font-weight:700;color:var(--primary);background:0 0;border:1px solid var(--primary);border-radius:6px;padding:5px 10px;cursor:pointer}
.btn-filter-reset:hover{background:var(--primary);color:#fff}
.sidebar .visible-count{font-size:10px;font-weight:700;color:var(--mute)}

.btn-confirm{display:flex;width:100%;margin-top:12px;justify-content:center;align-items:center;gap:6px;border:0;background:var(--primary);color:#fff;font:inherit;font-size:13px;font-weight:800;padding:9px 14px;border-radius:8px;cursor:pointer;opacity:0;pointer-events:none;transform:translateY(6px);transition:opacity .2s,transform .2s,background .12s}
.btn-confirm.is-show{opacity:1;pointer-events:auto;transform:translateY(0)}
.btn-confirm:hover{background:var(--primary-deep)}
.btn-confirm:active{transform:scale(.97)}

.sidebar-reopen{display:none;position:fixed;top:14px;left:14px;z-index:210;font-size:12px;font-weight:700;color:#fff;background:var(--primary);border:0;border-radius:6px;padding:6px 14px;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.15);transition:background .15s}
.sidebar-reopen:hover{background:var(--primary-deep)}
.layout.is-collapsed ~ .sidebar-reopen{display:block}

@media (max-width:1024px){
  .layout{display:block}
  .sidebar{position:fixed;top:0;left:0;bottom:0;width:280px;max-height:100vh;border-radius:0;z-index:200;transform:translateX(-100%);transition:transform .25s}
  .sidebar.is-open{transform:translateX(0)}
  .sidebar-close{display:block;position:absolute;top:10px;right:10px;width:28px;height:28px;border-radius:6px;border:1px solid var(--line);background:#fff;font-size:18px;color:var(--ink);cursor:pointer;z-index:10}
  .sidebar-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:190;display:none}
  .sidebar-backdrop.is-open{display:block}
  .container{max-width:100%;width:100%;padding:14px 12px 32px}
  .sidebar-reopen{display:none !important}
}
@media (min-width:1025px){.sidebar-backdrop{display:none}}
@media (max-width:760px){.sidebar{width:85vw}}

.sec-head{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin:0 0 6px}
.sec-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px}
.sec-metrics .stat-card{background:#fff;border-radius:8px;padding:6px 10px;border:1px solid var(--line)}
.sec-actions{display:flex;align-items:center;justify-content:flex-end;gap:8px;margin-bottom:8px}
.section-title{font-size:16px;font-weight:800;margin:0;color:#0f172a;letter-spacing:-.01em}
.section-sub{margin:0;color:var(--mute);font-size:12px}

.block-card{background:#fff;border:1px solid var(--line);border-radius:var(--r);margin-bottom:10px;overflow:hidden}
.block-head{display:flex;align-items:center;justify-content:space-between;gap:6px;padding:6px 10px 3px}
.block-kicker{font-size:9px;font-weight:700;letter-spacing:.06em;color:var(--primary);margin-bottom:1px;text-transform:uppercase}
.block-title{font-size:12px;font-weight:800;margin:0;color:#0f172a}
.block-desc{margin:0;color:var(--mute);font-size:12px;line-height:1.4;max-width:600px}
.block-count{font-size:11px;font-weight:700;color:var(--mute);background:var(--canvas);border:1px solid var(--line);padding:2px 8px;border-radius:999px;white-space:nowrap}
.block-official .block-kicker{color:var(--amber)}
.block-official{border-color:#f0e4c8}
.block-head-right{display:flex;flex-direction:column;align-items:flex-end;gap:4px}
.block-fam{font-size:10px;font-weight:700;color:var(--mute);letter-spacing:.02em}
.family-strip{display:flex;gap:6px;padding:0 12px 6px}
.fam-chip{font-size:10px;font-weight:800;padding:2px 8px;border-radius:999px;border:1px solid var(--line);background:var(--canvas);color:var(--ink2)}
.fam-openai{background:#e8f8f2;border-color:#a7d8c4;color:#1a9e72}
.fam-claude{background:#fff8e7;border-color:#e8d08e;color:#b8860b}
.fam-gemini{background:#e8f8f2;border-color:#a7d8c4;color:#1a9e72}

.btn-filter-toggle{display:inline-flex;align-items:center;font-size:12px;font-weight:700;color:var(--primary);background:#fff;border:1px solid var(--line);border-radius:6px;padding:6px 14px;cursor:pointer;gap:4px}
.btn-filter-toggle::before{content:'☰';font-size:13px}

.filter-bar,.filter-top,.filter-grid,.filter-group,.filter-foot{display:none}
.rate-input-wrap{display:flex;gap:6px;align-items:center}
.rate-input{width:90px;border:1px solid var(--line);border-radius:6px;padding:7px 8px;font:inherit;font-weight:700;color:var(--ink);background:#fff}
.rate-input:focus{outline:2px solid var(--primary);outline-offset:1px}
.rate-hint{margin-top:4px;font-size:11px;color:var(--mute)}
.rate-hint strong{color:var(--primary)}
.mini-actions{display:flex;gap:6px}
.linkish{border:0;background:transparent;color:var(--primary);font:inherit;font-size:11px;font-weight:700;cursor:pointer;padding:0}
.linkish:hover{text-decoration:underline}
.chip-row{display:flex;flex-wrap:wrap;gap:6px}
.chip{border:1px solid var(--line);background:#fff;color:var(--ink2);border-radius:999px;padding:5px 10px;font:inherit;font-size:11px;font-weight:700;cursor:pointer;transition:.12s}
.chip:hover{border-color:var(--primary);background:var(--primary-soft);color:var(--primary)}
.chip.is-on{background:var(--primary);border-color:var(--primary);color:#fff;box-shadow:0 0 0 1px var(--primary)}
.visible-count{font-size:11px;font-weight:700;color:var(--primary);background:var(--primary-soft);border-radius:999px;padding:4px 8px}
tr.js-row.is-hidden{display:none}
.empty-filter{display:none;padding:20px 12px;text-align:center;color:var(--mute);font-size:12px}
.empty-filter.is-show{display:block}

.table-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch;padding:0 0 4px}
.price-table{width:100%;border-collapse:collapse;min-width:880px}
.w-model{width:22%}.w-canon{width:13%}.w-source{width:10%}.w-num{width:12%}.w-ctx{width:12%}.w-curr{width:6%}
.price-table th,.price-table td{padding:5px 8px;border-bottom:1px solid var(--line);vertical-align:middle;font-size:11px;text-align:left}
.price-table th{position:sticky;top:0;z-index:1;background:#f8fafb;color:var(--mute);font-size:11px;font-weight:700;white-space:nowrap}
.price-table th.sortable{cursor:pointer;user-select:none}
.price-table th.sortable:hover{color:var(--primary);background:#eef2f7}
.price-table th.sortable::after{content:"⇅";margin-left:3px;font-size:9px;opacity:.3}
.price-table th.sortable[aria-sort="ascending"]::after{content:"↑";opacity:1;color:var(--primary)}
.price-table th.sortable[aria-sort="descending"]::after{content:"↓";opacity:1;color:var(--primary)}
.price-table th.num,.price-table td.num{text-align:right;font-variant-numeric:tabular-nums;font-weight:600;white-space:nowrap}
.price-table tbody tr:hover{background:#f8fafb}
.row-hl{animation:rowHl 2s ease-out}
@keyframes rowHl{0%{background:#fff3cd}60%{background:#fff3cd}100%{background:transparent}}
.price-table tbody tr:last-child td{border-bottom:0}

.c-model .model{font-weight:700;color:var(--ink);line-height:1.3;word-break:break-word}
.tags{display:flex;flex-wrap:wrap;gap:3px;margin-top:3px}
.tag{display:inline-block;font-size:9px;font-weight:700;padding:1px 5px;border-radius:999px;border:1px solid transparent}
.tag-official{color:var(--amber);background:var(--amber-soft);border-color:rgba(245,158,11,.15)}
.tag-best{color:var(--green);background:var(--green-soft)}
.tag-premium{color:var(--red);background:var(--red-soft)}
.muted{color:var(--mute);font-weight:500}
.pill{display:inline-block;padding:2px 7px;border-radius:6px;font-size:11px;font-weight:700;background:var(--canvas);color:var(--ink2);border:1px solid var(--line)}
.sub-hint{font-size:10px;color:var(--mute);font-weight:500;margin-top:2px}
.c-curr{text-align:center;font-weight:600;font-size:11px;color:var(--ink2)}

tr.is-official td{background:#fff8e7}
tr.is-official td:first-child{box-shadow:inset 2px 0 0 var(--amber)}
tr.is-lowest:not(.is-official) td:first-child{box-shadow:inset 2px 0 0 var(--green)}

.empty-mini{padding:24px 14px;text-align:center;color:var(--mute);font-size:13px}

.chart-card{padding-bottom:12px}
.chart-head{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;padding:8px 12px 4px}
.chart-controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.chart-wrap{height:280px;padding:0 10px 4px;position:relative}
.seg{display:inline-flex;background:var(--canvas);border:1px solid var(--line);border-radius:8px;padding:3px;gap:2px}
.seg-btn{border:0;background:transparent;color:var(--mute);font:inherit;font-size:12px;font-weight:600;padding:5px 10px;border-radius:6px;cursor:pointer}
.seg-btn.is-active{background:var(--primary);color:#fff;box-shadow:none}
select{font:inherit;padding:7px 10px;border-radius:6px;border:1px solid var(--line);background:#fff;color:var(--ink);min-width:160px;cursor:pointer}

.btn-export{display:inline-flex;align-items:center;gap:4px;border:0;background:var(--green);color:#fff;font:inherit;font-size:12px;font-weight:700;padding:7px 12px;border-radius:6px;cursor:pointer}
.btn-export:hover{background:var(--green-deep)}
.btn-export[disabled]{opacity:.5;cursor:wait}

footer{background:#f8fafb;color:var(--mute);padding:16px 24px;text-align:center;font-size:12px;line-height:1.6;margin-top:8px;border-top:1px solid var(--line)}
footer .note{max-width:720px;margin:0 auto 6px}
footer strong{color:var(--primary)}
footer .disc{color:var(--mute)}

.totop{position:fixed;right:14px;bottom:14px;width:36px;height:36px;border:0;border-radius:50%;
  background:var(--primary);color:#fff;font-size:16px;cursor:pointer;opacity:0;visibility:hidden;
  transform:translateY(6px);transition:.15s;z-index:40}
.totop.is-show{opacity:1;visibility:visible;transform:none}

.hot-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;padding:0 12px 8px}
.hot-card{background:#fff;border:1px solid var(--line);border-radius:6px;padding:5px 6px}
.hot-card[data-source="openai"]{border-color:#a7d8c4;background:#e8f8f2}
.hot-card[data-source="anthropic"]{border-color:#e8d08e;background:#fff8e7}
.hot-card[data-source="google"]{border-color:#a7d8c4;background:#e8f8f2}
.hot-brand{font-size:10px;font-weight:800;color:var(--mute);letter-spacing:.04em;text-transform:uppercase}
.hot-name{font-size:11px;font-weight:800;margin:1px 0 3px;color:#0f172a}
.hot-price{display:flex;align-items:baseline;justify-content:space-between;gap:6px;font-weight:800;color:var(--ink);font-variant-numeric:tabular-nums}
.hot-price small{font-size:10px;color:var(--mute);font-weight:600}
.hot-price.muted{margin-top:1px;font-weight:600;color:var(--mute)}
.block-tracking{border-color:#e8d08e}
.block-tracking .block-kicker{color:#b8860b}
.track-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;padding:0 10px 10px}
.track-card{border:1px solid var(--line);border-radius:6px;padding:6px;background:#fff}
.track-card.is-tracking{background:#fff8e7;border-color:#e8d08e}
.track-card.is-active{background:#e8f8f2;border-color:#a7d8c4}
.track-top{display:flex;justify-content:space-between;gap:4px;margin-bottom:3px}
.track-family{font-size:9px;font-weight:800;color:var(--mute)}
.track-status{font-size:9px;font-weight:800;padding:1px 5px;border-radius:999px;background:var(--canvas);border:1px solid var(--line)}
.track-card.is-tracking .track-status{color:#b8860b;border-color:#d4a520;background:#fff8e7}
.track-card.is-active .track-status{color:#1a9e72;border-color:#1a9e72;background:#e8f8f2}
.track-name{font-size:11px;font-weight:800;color:#0f172a;margin-bottom:3px}
.track-meta{display:flex;gap:6px;font-size:9px;color:var(--mute);font-weight:600;margin-bottom:3px}
.track-note{margin:0;font-size:9px;color:var(--ink2);line-height:1.4}
@media (max-width:1024px){.hot-strip{grid-template-columns:repeat(2,1fr)}.track-grid{grid-template-columns:1fr 1fr}}
@media (max-width:760px){.hot-strip,.track-grid{grid-template-columns:1fr}}

.block-overseas{border-color:#bcd4e8}
.block-overseas .block-kicker{color:#3b82f6}
.tag-global{color:#3b82f6;background:#e8f0ff}
.tag-family{color:var(--ink2);background:var(--canvas);border-color:var(--line)}
.overseas-note{margin:2px 12px 8px;font-size:12px}

/* 主流模型双专区 */
.block-mainstream{border-color:#a7d8c4}
.block-mainstream.ms-overseas{border-color:#bcd4e8}
.ms-domestic .block-kicker{color:#1a9e72}
.ms-overseas .block-kicker{color:#3b82f6}
.ms-unified-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:5px;padding:0 10px 10px;perspective:1000px}
.model-pick{background:#fff;border:1px solid var(--line);border-radius:5px;padding:4px 5px;cursor:pointer;outline:none;position:relative;overflow:hidden;display:flex;flex-direction:column;gap:1px;transform-style:preserve-3d;will-change:transform;transform:rotateX(var(--rx,0deg)) rotateY(var(--ry,0deg));transition:transform .25s cubic-bezier(.16,1,.3,1),border-color .15s,box-shadow .15s}
.model-pick:hover,.model-pick:focus-visible{--ty:-2px;border-color:var(--primary);box-shadow:0 6px 18px -8px rgba(15,23,42,.28),0 0 0 2px rgba(43,174,133,.14);translate:0 var(--ty,0)}
.ms-overseas .model-pick:hover,.ms-overseas .model-pick:focus-visible{border-color:#3b82f6;box-shadow:0 6px 18px -8px rgba(15,23,42,.28),0 0 0 2px rgba(59,130,246,.14)}
/* 聚光描边：鼠标位置的柔光 */
.model-pick::after{content:"";position:absolute;inset:0;border-radius:inherit;pointer-events:none;z-index:1;opacity:0;transition:opacity .25s;background:radial-gradient(200px circle at var(--mx,50%) var(--my,50%),color-mix(in srgb,var(--vc,#2baE85) 20%,transparent),transparent 62%)}
.model-pick:hover::after,.model-pick:focus-visible::after{opacity:1}
.model-pick>*{position:relative;z-index:2}
.ms-vendor-stripe{position:absolute;top:0;left:0;right:0;height:3px;z-index:3;background:#94a3b8;background-size:200% 100%}
.ms-vendor-stripe[data-vendor=deepseek]{--vc:#4ade80;background-image:linear-gradient(90deg,#4ade80,#bbf7d0,#4ade80)}
.ms-vendor-stripe[data-vendor=qwen]{--vc:#f59e0b;background-image:linear-gradient(90deg,#f59e0b,#fde68a,#f59e0b)}
.ms-vendor-stripe[data-vendor=bigmodel]{--vc:#60a5fa;background-image:linear-gradient(90deg,#60a5fa,#bfdbfe,#60a5fa)}
.ms-vendor-stripe[data-vendor=kimi]{--vc:#a78bfa;background-image:linear-gradient(90deg,#a78bfa,#ddd6fe,#a78bfa)}
.ms-vendor-stripe[data-vendor=minimax]{--vc:#22d3ee;background-image:linear-gradient(90deg,#22d3ee,#a5f3fc,#22d3ee)}
.ms-vendor-stripe[data-vendor=doubao]{--vc:#f472b6;background-image:linear-gradient(90deg,#f472b6,#fbcfe8,#f472b6)}
.ms-vendor-stripe[data-vendor=openai]{--vc:#10b981;background-image:linear-gradient(90deg,#10b981,#a7f3d0,#10b981)}
.ms-vendor-stripe[data-vendor=anthropic]{--vc:#e11d48;background-image:linear-gradient(90deg,#e11d48,#fecdd3,#e11d48)}
.ms-vendor-stripe[data-vendor=google]{--vc:#3b82f6;background-image:linear-gradient(90deg,#3b82f6,#bfdbfe,#3b82f6)}
.model-pick[data-source=deepseek]{--vc:#4ade80}
.model-pick[data-source=qwen]{--vc:#f59e0b}
.model-pick[data-source=bigmodel]{--vc:#60a5fa}
.model-pick[data-source=kimi]{--vc:#a78bfa}
.model-pick[data-source=minimax]{--vc:#22d3ee}
.model-pick[data-source=doubao]{--vc:#f472b6}
.model-pick[data-source=openai]{--vc:#10b981}
.model-pick[data-source=anthropic]{--vc:#e11d48}
.model-pick[data-source=google]{--vc:#3b82f6}
.ms-model-head{display:flex;align-items:flex-start;justify-content:space-between;gap:3px;margin-bottom:0}
.ms-model-name{font-size:9px;font-weight:800;color:#0f172a;line-height:1.15}
.ms-unit-badge{font-size:6px;color:var(--mute);font-weight:600;white-space:nowrap;letter-spacing:.01em;align-self:flex-start;line-height:1.1;flex-shrink:0}
.ms-role{font-size:8px;color:var(--mute);margin-bottom:1px}
/* 价格：输入 / 输出 / 缓存命中 三列同级 */
.ms-prices{display:grid;grid-template-columns:repeat(3,1fr);gap:3px;margin-bottom:1px}
.ms-pcol{display:flex;flex-direction:column;align-items:center;gap:0;background:var(--canvas);border:1px solid var(--line);border-radius:3px;padding:2px 0;transition:background .15s,transform .15s}
.ms-pcol:hover{transform:translateY(-1px);background:#e9f9f1}
.ms-overseas .ms-pcol:hover{background:#eaf2fe}
.model-pick:hover .ms-pcol{background:#f1fbf7}
.ms-overseas .model-pick:hover .ms-pcol{background:#f1f6fe}
.ms-plabel{font-size:7px;color:var(--mute);font-weight:600;line-height:1.1}
.ms-pval{font-size:9px;font-weight:800;color:#0f172a;line-height:1.2}
.ms-prices.ms-no-price{grid-template-columns:1fr;background:transparent;border:0;color:var(--mute);font-style:italic;font-size:8px;text-align:center;padding:2px 0}
.ms-tiers{margin:3px 0}
.ms-tiers summary{font-size:8px;font-weight:700;color:var(--ink2);cursor:pointer}
.ms-tiers ul{margin:1px 0 0;padding-left:10px;font-size:8px;color:var(--mute)}
.ms-tiers li{margin:0}
.ms-meta{display:flex;align-items:center;gap:2px;margin-top:1px;font-size:8px}
.ms-channel-ok{color:#1a9e72;font-weight:700;font-size:8px}
.ms-channel-empty{color:var(--mute);font-size:8px}
.ms-featured{display:inline-block;font-size:7px;font-weight:800;color:#fff;background:var(--primary);padding:0 3px;border-radius:2px;margin-left:2px;vertical-align:middle}
.ms-tracking{display:inline-block;font-size:7px;font-weight:800;color:#b8860b;background:#fff8e7;padding:0 3px;border-radius:2px;margin-left:2px;vertical-align:middle;cursor:help}
.ms-verified{color:var(--mute);font-size:8px}
.ms-date-banner{text-align:center;font-size:8px;color:var(--mute);padding:2px 10px 4px;letter-spacing:.02em}
/* 入场错峰 + 厂商条纹流光 + 热标记脉冲（仅在允许动效时） */
@media (prefers-reduced-motion: no-preference){
  .model-pick{animation:cardIn .55s cubic-bezier(.16,1,.3,1) backwards;animation-delay:calc(var(--i,0)*42ms)}
  .ms-vendor-stripe{animation:stripeSheen 3.6s linear infinite}
  .ms-featured{animation:hotPulse 2.2s ease-in-out infinite}
}
@keyframes cardIn{from{opacity:0;transform:translateY(12px) scale(.98)}to{opacity:1;transform:translateY(0) scale(1)}}
@keyframes stripeSheen{0%{background-position:0% 0}100%{background-position:200% 0}}
@keyframes hotPulse{0%,100%{box-shadow:0 0 0 0 rgba(43,174,133,.55)}50%{box-shadow:0 0 0 3px rgba(43,174,133,0)}}
@media (prefers-reduced-motion: reduce){
  .model-pick,.ms-vendor-stripe,.ms-featured{animation:none!important;transition:none!important}
}
@media (min-width:1280px){.ms-unified-grid{grid-template-columns:repeat(5,1fr);gap:5px}}
@media (max-width:1024px){.ms-unified-grid{grid-template-columns:repeat(2,1fr);gap:5px}}
@media (max-width:760px){.ms-unified-grid{grid-template-columns:1fr}}
tr[data-source="openai"] .pill{background:#e8f8f2;border-color:#a7d8c4;color:#1a9e72}
tr[data-source="anthropic"] .pill{background:#fff8e7;border-color:#e8d08e;color:#b8860b}
tr[data-source="google"] .pill{background:#e8f8f2;border-color:#a7d8c4;color:#1a9e72}

@media (max-width:1024px){.metrics{grid-template-columns:repeat(2,1fr)}.sec-metrics{grid-template-columns:repeat(2,1fr)}}
@media (max-width:760px){
  .hero-inner{padding:16px 12px 12px}
  .hero h1{font-size:16px}
  .container{padding:12px 10px 28px}
  .btn-export{width:100%;justify-content:center}
  .panel-hint,.block-head,.chart-head{padding-left:10px;padding-right:10px}
  .chart-wrap{height:240px}
  .price-table th,.price-table td{padding:4px 6px;font-size:10px}
  .rate-input-wrap{flex-wrap:wrap}
}
@media (max-width:480px){.metrics{grid-template-columns:1fr}.sec-metrics{grid-template-columns:repeat(2,1fr)}}
"""

_JS = """
const SITE_DATA = __SITE_DATA__;
(function(){
  var state = {
    rate: 7.0,
    models: {},     // canonical model -> bool （全部大模型）
    channels: {}    // source id -> bool
  };

  function fmt(n){
    if (n == null || isNaN(n)) return '—';
    if (Math.abs(n - Math.round(n)) < 1e-9) return String(Math.round(n));
    return (Math.round(n * 1000) / 1000).toString();
  }

  var totop = document.getElementById('toTop');
  if (totop){
    window.addEventListener('scroll', function(){
      totop.classList.toggle('is-show', window.scrollY > 500);
    }, {passive:true});
    totop.addEventListener('click', function(){ window.scrollTo({top:0,behavior:'smooth'}); });
  }

  document.querySelectorAll('.market-tab').forEach(function(tab){
    tab.addEventListener('click', function(){
      var m = tab.dataset.market;
      document.querySelectorAll('.market-tab').forEach(function(t){
        var on = t === tab;
        t.classList.toggle('is-active', on);
        t.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      ['domestic','overseas'].forEach(function(key){
        var p = document.getElementById('panel-' + key);
        if (!p) return;
        var show = key === m;
        p.hidden = !show;
        p.classList.toggle('is-active', show);
      });
      updateVisibleCount();
    });
  });

  document.querySelectorAll('th.sortable').forEach(function(th){
    th.addEventListener('click', function(){
      var table = th.closest('table');
      var tbody = table.querySelector('tbody');
      var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr.js-row'));
      var key = th.dataset.key;
      var idx = Array.prototype.indexOf.call(th.parentNode.children, th);
      var asc = th.getAttribute('aria-sort') !== 'ascending';
      th.parentNode.querySelectorAll('th[aria-sort]').forEach(function(t){ if (t!==th) t.removeAttribute('aria-sort'); });
      th.setAttribute('aria-sort', asc ? 'ascending' : 'descending');
      rows.sort(function(a,b){
        if (key==='model'||key==='canon'||key==='source'){
          var av=(a.cells[idx].dataset.sort||a.cells[idx].textContent||'').trim();
          var bv=(b.cells[idx].dataset.sort||b.cells[idx].textContent||'').trim();
          return asc ? av.localeCompare(bv,'zh') : bv.localeCompare(av,'zh');
        }
        var an=parseFloat(a.cells[idx].dataset.sort), bn=parseFloat(b.cells[idx].dataset.sort);
        if (isNaN(an)) an = asc ? Infinity : -Infinity;
        if (isNaN(bn)) bn = asc ? Infinity : -Infinity;
        return asc ? an-bn : bn-an;
      });
      rows.forEach(function(r){ tbody.appendChild(r); });
    });
  });

  var meta = SITE_DATA.filter_meta || {};
  var allModels = meta.models || meta.all_models || SITE_DATA.canons || [];
  var channels = meta.channels || [];
  allModels.forEach(function(m){ state.models[m] = true; });
  channels.forEach(function(c){ state.channels[c.id] = true; });

  function selectedKeys(map){
    return Object.keys(map).filter(function(k){ return map[k]; });
  }
  function allOn(map){
    var ks = Object.keys(map);
    return ks.length && ks.every(function(k){ return map[k]; });
  }

  function renderChips(){
    var mBox = document.getElementById('modelChips');
    var cBox = document.getElementById('channelChips');
    if (mBox){
      mBox.innerHTML = allModels.map(function(m){
        return '<button type="button" class="chip'+(state.models[m]?' is-on':'')+'" data-kind="model" data-id="'+m+'">'+m+'</button>';
      }).join('') || '<span class="rate-hint">无模型数据</span>';
    }
    if (cBox){
      cBox.innerHTML = channels.map(function(c){
        return '<button type="button" class="chip'+(state.channels[c.id]?' is-on':'')+'" data-kind="channel" data-id="'+c.id+'">'+(c.label||c.id)+'</button>';
      }).join('');
    }
  }

  function rowMatches(row){
    var canon = row.getAttribute('data-canonical') || '';
    var source = row.getAttribute('data-source') || '';
    if (!state.models[canon]) return false;
    if (!state.channels[source]) return false;
    return true;
  }

  function updatePrices(){
    var rate = state.rate;
    document.querySelectorAll('tr.js-row').forEach(function(row){
      var cur = (row.getAttribute('data-currency') || '').toUpperCase();
      var input = parseFloat(row.getAttribute('data-input'));
      var output = parseFloat(row.getAttribute('data-output'));
      var inputRmb = parseFloat(row.getAttribute('data-input-rmb'));
      var outputRmb = parseFloat(row.getAttribute('data-output-rmb'));
      if (cur === 'USD'){
        var inHint = row.querySelector('.js-rmb-hint[data-side="input"]');
        var outHint = row.querySelector('.js-rmb-hint[data-side="output"]');
        if (inHint){
          var v = isNaN(input) ? null : input * rate;
          inHint.textContent = v == null ? '约 ¥—' : ('约 ¥' + fmt(v));
        }
        if (outHint){
          var v2 = isNaN(output) ? null : output * rate;
          outHint.textContent = v2 == null ? '约 ¥—' : ('约 ¥' + fmt(v2));
        }
      } else {
        var inMain = row.querySelector('.js-cny-main[data-side="input"]');
        var outMain = row.querySelector('.js-cny-main[data-side="output"]');
        if (inMain && !isNaN(inputRmb)) inMain.textContent = fmt(inputRmb);
        if (outMain && !isNaN(outputRmb)) outMain.textContent = fmt(outputRmb);
      }
    });
  }

  function applyFilter(){
    var shown = 0;
    document.querySelectorAll('tr.js-row').forEach(function(row){
      var ok = rowMatches(row);
      row.classList.toggle('is-hidden', !ok);
      if (ok) shown += 1;
    });
    document.querySelectorAll('.price-table').forEach(function(table){
      var wrap = table.closest('.table-wrap');
      if (!wrap) return;
      var rows = table.querySelectorAll('tr.js-row');
      var visible = table.querySelectorAll('tr.js-row:not(.is-hidden)');
      var empty = wrap.querySelector('.empty-filter');
      if (!empty){
        empty = document.createElement('div');
        empty.className = 'empty-filter';
        empty.textContent = '当前筛选条件下无匹配数据，请调整模型分类或渠道选择。';
        wrap.appendChild(empty);
      }
      empty.classList.toggle('is-show', rows.length > 0 && visible.length === 0);
    });
    updateSummary();
    updateVisibleCount(shown);
    maybeSyncChart();
    updateConfirmButton();
  }

  function updateSummary(){
    var mSel = selectedKeys(state.models);
    var chSel = selectedKeys(state.channels);
    var mText = allOn(state.models) ? '全部模型' : (mSel.length ? mSel.join(' / ') : '无模型');
    var chText = allOn(state.channels) ? '全部渠道' : (chSel.length ? chSel.map(function(id){
      var hit = channels.find(function(c){ return c.id === id; });
      return hit ? hit.label : id;
    }).join(' / ') : '无渠道');
    var el = document.getElementById('filterSummary');
    if (el) el.textContent = '当前：' + mText + ' · ' + chText + ' · 汇率 ' + state.rate.toFixed(2);
  }

  function updateVisibleCount(shown){
    if (typeof shown !== 'number'){
      shown = document.querySelectorAll('tr.js-row:not(.is-hidden)').length;
    }
    var el = document.getElementById('visibleCount');
    if (el) el.textContent = '显示 ' + shown + ' 行';
    var metricRate = document.getElementById('metricRate');
    if (metricRate) metricRate.innerHTML = state.rate.toFixed(2) + '<small>¥/$</small>';
    var fxCur = document.getElementById('fxCurrent');
    if (fxCur) fxCur.textContent = state.rate.toFixed(2);
  }

  function bindChips(){
    document.querySelectorAll('.chip').forEach(function(chip){
      chip.addEventListener('click', function(){
        var kind = chip.dataset.kind;
        var id = chip.dataset.id;
        if (kind === 'model'){
          state.models[id] = !state.models[id];
        } else if (kind === 'channel'){
          state.channels[id] = !state.channels[id];
        }
        chip.classList.toggle('is-on');
        applyFilter();
      });
    });
    document.querySelectorAll('.linkish').forEach(function(btn){
      btn.addEventListener('click', function(){
        var scope = btn.dataset.scope;
        var act = btn.dataset.act;
        if (scope === 'model'){
          if (act === 'all'){
            Object.keys(state.models).forEach(function(k){ state.models[k] = true; });
          } else if (act === 'none'){
            Object.keys(state.models).forEach(function(k){ state.models[k] = false; });
          } else if (act === 'domestic'){
            var domestic = (meta.domestic_models || []);
            var dset = {};
            domestic.forEach(function(m){ dset[m] = true; });
            Object.keys(state.models).forEach(function(k){ state.models[k] = !!dset[k]; });
          } else if (act === 'overseas'){
            var overseas = (meta.overseas_models || []);
            var oset = {};
            overseas.forEach(function(m){ oset[m] = true; });
            Object.keys(state.models).forEach(function(k){ state.models[k] = !!oset[k]; });
          }
        } else if (scope === 'channel'){
          Object.keys(state.channels).forEach(function(k){ state.channels[k] = act === 'all'; });
        }
        renderChips();
        bindChips();
        applyFilter();
      });
    });
  }


  // FIX 2: Click model card → scroll to channel panel, switch tab, highlight row
  function scrollToChannelPanel(canonical){
    // Find a matching row in any channel table to know which tab to show
    var targetRow = null;
    var targetPanel = null;
    ['domestic','overseas'].forEach(function(market){
      var panel = document.getElementById('panel-' + market);
      if (!panel) return;
      var row = panel.querySelector('tr.js-row[data-canonical="' + canonical + '"]');
      if (row){ targetRow = row; targetPanel = market; }
    });
    if (!targetPanel){
      // Fallback: scroll to first channel block
      var block = document.querySelector('.block-channel');
      if (block) block.scrollIntoView({behavior:'smooth', block:'start'});
      return;
    }
    // Switch to the correct tab
    var tab = document.querySelector('.market-tab[data-market="' + targetPanel + '"]');
    if (tab && !tab.classList.contains('is-active')){
      tab.click();
    }
    // Wait a tick for tab to render then scroll + highlight
    setTimeout(function(){
      // Re-find row in case DOM changed
      var panel = document.getElementById('panel-' + targetPanel);
      var row = panel ? panel.querySelector('tr.js-row[data-canonical="' + canonical + '"]') : null;
      if (!row) return;
      row.scrollIntoView({behavior:'smooth', block:'center'});
      // Briefly highlight the row
      row.classList.add('row-hl');
      setTimeout(function(){ row.classList.remove('row-hl'); }, 2000);
    }, 250);
  }

  function selectOnlyModel(canonical){
    Object.keys(state.models).forEach(function(key){ state.models[key] = key === canonical; });
    renderChips();
    bindChips();
    applyFilter();
    // 桌面端：折叠侧边栏；移动端：关闭抽屉
    if (window.matchMedia('(min-width:1025px)').matches){
      if (!isCollapsed && typeof toggleSidebarLayout === 'function') toggleSidebarLayout();
    } else {
      if (typeof closeSidebar === 'function') closeSidebar();
    }
    // FIX 2: 跳转到渠道报价区
    if (typeof scrollToChannelPanel === 'function') scrollToChannelPanel(canonical);
  }

  function bindModelCards(){
    document.querySelectorAll('.model-pick[data-canonical]').forEach(function(card){
      if (card.getAttribute('data-bound') === '1') return;
      card.setAttribute('data-bound','1');
      card.addEventListener('click', function(){
        selectOnlyModel(card.dataset.canonical);
      });
      card.addEventListener('keydown', function(e){
        if (e.key === 'Enter' || e.key === ' '){
          e.preventDefault();
          selectOnlyModel(card.dataset.canonical);
        }
      });
    });
  }
  bindModelCards();

  // 移动端侧边栏展开/收起
  var sidebarToggle = document.getElementById('sidebarToggle');
  var sidebar = document.getElementById('sidebar');
  var sidebarBackdrop = document.getElementById('sidebarBackdrop');
  var sidebarClose = document.getElementById('sidebarClose');
  function openSidebar(){
    if (sidebar) sidebar.classList.add('is-open');
    if (sidebarBackdrop) sidebarBackdrop.classList.add('is-open');
  }
  function closeSidebar(){
    if (sidebar) sidebar.classList.remove('is-open');
    if (sidebarBackdrop) sidebarBackdrop.classList.remove('is-open');
  }
  if (sidebarToggle) sidebarToggle.addEventListener('click', function(){
    // 桌面端：切换侧边栏折叠；移动端：打开侧边栏浮层
    if (layout && window.innerWidth > 1024) {
      toggleSidebarLayout();
    } else {
      openSidebar();
    }
  });
  if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', closeSidebar);
  if (sidebarClose) sidebarClose.addEventListener('click', closeSidebar);

  // 卡片聚光描边 + 轻微 3D 倾斜（尊重 prefers-reduced-motion）
  (function(){
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    var cards = document.querySelectorAll('.model-pick');
    var MAX = 5; // 最大倾斜角度
    cards.forEach(function(card){
      card.addEventListener('pointermove', function(e){
        var r = card.getBoundingClientRect();
        var px = (e.clientX - r.left) / r.width;
        var py = (e.clientY - r.top) / r.height;
        card.style.setProperty('--mx', (px * 100).toFixed(1) + '%');
        card.style.setProperty('--my', (py * 100).toFixed(1) + '%');
        card.style.setProperty('--ry', ((px - 0.5) * MAX * 2).toFixed(2) + 'deg');
        card.style.setProperty('--rx', ((0.5 - py) * MAX * 2).toFixed(2) + 'deg');
      });
      card.addEventListener('pointerleave', function(){
        card.style.setProperty('--ry', '0deg');
        card.style.setProperty('--rx', '0deg');
      });
    });
  })();


  // 桌面端折叠/展开侧边栏（FIX 3: 增加 hover-peek + 自动收起）
  var layout = document.querySelector('.layout');
  var sidebarCollapse = document.getElementById('sidebarCollapse');
  var sidebarReopen = document.getElementById('sidebarReopen');
  var sidebarWarmupTimer = null;
  var sidebarLeaveTimer = null;
  var isCollapsed = false;
  var isPeek = false;

  function clearSidebarTimers(){
    if (sidebarWarmupTimer){ clearTimeout(sidebarWarmupTimer); sidebarWarmupTimer = null; }
    if (sidebarLeaveTimer){ clearTimeout(sidebarLeaveTimer); sidebarLeaveTimer = null; }
  }

  function collapseSidebar(){
    if (!layout || isCollapsed) return;
    isCollapsed = true;
    layout.classList.add('is-collapsed');
    sidebarReopen.classList.add('is-show');
    isPeek = false;
  }
  function expandSidebar(){
    if (!layout || !isCollapsed) return;
    isCollapsed = false;
    layout.classList.remove('is-collapsed');
    sidebarReopen.classList.remove('is-show');
    isPeek = false;
  }
  function toggleSidebarLayout(){
    if (!layout) return;
    if (isCollapsed) expandSidebar(); else collapseSidebar();
  }

  // Hover-peek: hover reopen button → temporarily expand; leave → collapse
  if (sidebarReopen){
    sidebarReopen.addEventListener('mouseenter', function(){
      if (!isCollapsed) return;
      clearSidebarTimers();
      isPeek = true;
      layout.classList.remove('is-collapsed');
      sidebar.classList.add('is-peek');
    });
    sidebarReopen.addEventListener('mouseleave', function(){
      if (!isPeek) return;
      clearSidebarTimers();
      sidebarLeaveTimer = setTimeout(function(){
        if (isCollapsed && isPeek){
          layout.classList.add('is-collapsed');
          sidebar.classList.remove('is-peek');
          isPeek = false;
        }
      }, 800);
    });
  }
  // When peeking, moving into sidebar keeps it open
  if (sidebar){
    sidebar.addEventListener('mouseenter', function(){
      if (isPeek){ clearSidebarTimers(); }
    });
    sidebar.addEventListener('mouseleave', function(){
      if (!isPeek || !isCollapsed) return;
      clearSidebarTimers();
      sidebarLeaveTimer = setTimeout(function(){
        if (isCollapsed && isPeek){
          layout.classList.add('is-collapsed');
          sidebar.classList.remove('is-peek');
          isPeek = false;
        }
      }, 600);
    });
  }

  if (sidebarCollapse) sidebarCollapse.addEventListener('click', toggleSidebarLayout);
  if (sidebarReopen) sidebarReopen.addEventListener('click', function(){
    // click fully toggles (cancel peek state)
    isPeek = false;
    clearSidebarTimers();
    toggleSidebarLayout();
  });

  // 确认按钮：有选中内容时显示，点击后收起侧边栏
  var sidebarConfirm = document.getElementById('sidebarConfirm');
  function isDefaultFilter(){
    return allOn(state.models) && allOn(state.channels) && Math.abs(state.rate - 7.0) < 0.01;
  }
  function updateConfirmButton(){
    if (!sidebarConfirm) return;
    sidebarConfirm.classList.toggle('is-show', !isDefaultFilter());
  }
  if (sidebarConfirm){
    sidebarConfirm.addEventListener('click', function(){
      closeSidebar();
      document.getElementById('main').scrollIntoView({behavior:'smooth', block:'start'});
    });
  }

  var fx = document.getElementById('fxRate');
  var fxReset = document.getElementById('fxReset');
  function setRate(v){
    var n = parseFloat(v);
    if (isNaN(n) || n <= 0) n = 7.0;
    if (n > 100) n = 100;
    state.rate = Math.round(n * 100) / 100;
    if (fx) fx.value = state.rate;
    updatePrices();
    applyFilter();
  }
  if (fx){
    fx.addEventListener('change', function(){ setRate(fx.value); });
    fx.addEventListener('input', function(){
      var n = parseFloat(fx.value);
      if (!isNaN(n) && n > 0) {
        state.rate = Math.round(n * 100) / 100;
        updatePrices();
        updateSummary();
        updateVisibleCount();
        updateConfirmButton();
      }
    });
  }
  if (fxReset) fxReset.addEventListener('click', function(){ setRate(7.0); });
  var filterReset = document.getElementById('filterReset');
  if (filterReset){
    filterReset.addEventListener('click', function(){
      Object.keys(state.models).forEach(function(k){ state.models[k]=true; });
      Object.keys(state.channels).forEach(function(k){ state.channels[k]=true; });
      renderChips();
      bindChips();
      setRate(7.0);
    });
  }

  var btn = document.getElementById('btnExcel');
  if (btn){
    btn.addEventListener('click', function(){
      if (typeof XLSX === 'undefined'){ alert('Excel 组件未加载，请联网后重试。'); return; }
      btn.disabled = true;
      try{
        var rows = [['区块','模型分组','模型','来源','输入','输出','输入¥(当前汇率)','输出¥(当前汇率)','缓存','上下文','货币','官方','最低']];
        function push(kind, list){
          (list||[]).forEach(function(r){
            if (!state.models[r.canonical]) return;
            if (!state.channels[r.source]) return;
            var inRmb = r.input_rmb, outRmb = r.output_rmb;
            if ((r.currency||'').toUpperCase()==='USD'){
              inRmb = r.input == null ? null : r.input * state.rate;
              outRmb = r.output == null ? null : r.output * state.rate;
            }
            rows.push([
              kind, r.canonical||'', r.model||r.model_raw||'', r.source_label||r.source||'',
              r.input==null?'':r.input, r.output==null?'':r.output,
              inRmb==null?'':Math.round(inRmb*1000)/1000, outRmb==null?'':Math.round(outRmb*1000)/1000,
              r.cache_hit==null?'':r.cache_hit, r.context||'', r.currency||'',
              r.is_official?'是':'否', r.is_lowest?'是':'否'
            ]);
          });
        }
        push('官网原价', SITE_DATA.official_rows);
        push('海外主流', SITE_DATA.overseas_rows);
        push('国内渠道', SITE_DATA.channel_domestic);
        push('海外渠道', SITE_DATA.channel_overseas);
        // 主流模型目录（国内/海外双专区）
        function pushMainstream(region, vendors){
          (vendors||[]).forEach(function(vendor){
            (vendor.models||[]).forEach(function(model){
              var tier = (model.pricing && model.pricing.tiers && model.pricing.tiers[0]) || {};
              rows.push([
                region, vendor.name||vendor.id||'', model.display_name||model.canonical||'',
                model.source_label||vendor.source_id||vendor.id||'',
                tier.input_price==null?'':tier.input_price,
                tier.output_price==null?'':tier.output_price,
                '', '',
                tier.cache_input_price==null?'':tier.cache_input_price,
                model.context_label||'', model.currency||'',
                '是', ''
              ]);
            });
          });
        }
        if (SITE_DATA.mainstream_sections){
          pushMainstream('国内主流', SITE_DATA.mainstream_sections.domestic);
          pushMainstream('海外主流', SITE_DATA.mainstream_sections.overseas);
        }
        var ws = XLSX.utils.aoa_to_sheet(rows);
        var wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, '比价');
        var stamp = (SITE_DATA.generated_at||'').replace(/[: ]/g,'-').slice(0,19);
        XLSX.writeFile(wb, 'token-pricing-'+stamp+'.xlsx');
      } finally { btn.disabled=false; }
    });
  }

  var chart = null, metric = 'input';
  var COLORS = { primary:'#4f46e5', green:'#059669', muted:'#cbd5e1' };
  var sel = document.getElementById('modelSelect');
  var canvas = document.getElementById('priceChart');
  function getRows(c){ return (SITE_DATA.chart && SITE_DATA.chart[c]) || []; }
  function valOf(r){
    if (metric==='output'){
      if ((r.currency||'').toUpperCase()==='USD' && r.output != null) return r.output * state.rate;
      return r.output_rmb;
    }
    if ((r.currency||'').toUpperCase()==='USD' && r.input != null) return r.input * state.rate;
    return r.input_rmb;
  }
  function draw(canon){
    if (typeof Chart === 'undefined' || !canvas) return;
    var rows = getRows(canon).filter(function(r){
      return state.channels[r.source] !== false && state.models[canon] !== false;
    });
    if (state.models[canon] === false) rows = [];
    var vals = rows.map(function(r){ var v=valOf(r); return v==null?null:v; });
    var nums = vals.filter(function(v){ return v!=null; });
    var min = nums.length ? Math.min.apply(null, nums) : null;
    var colors = vals.map(function(v){ return (v!=null && min!=null && v===min) ? COLORS.green : COLORS.primary; });
    var ctx = canvas.getContext('2d');
    if (chart) chart.destroy();
    chart = new Chart(ctx, {
      type:'bar',
      data:{
        labels: rows.map(function(r){ return (r.source_label||r.source) + (r.model?(' · '+r.model):''); }),
        datasets:[{ label: metric==='output'?'输出价':'输入价', data:vals, backgroundColor:colors, borderRadius:6, maxBarThickness:48 }]
      },
      options:{
        responsive:true, maintainAspectRatio:false,
        plugins:{ legend:{display:false}, tooltip:{ callbacks:{ label:function(c){ return c.parsed.y==null?'无数据':'¥ '+fmt(c.parsed.y); } } } },
        scales:{
          y:{ beginAtZero:true, ticks:{ callback:function(v){ return '¥'+v; }, color:'#64748b' }, grid:{ color:'#eef2f7' } },
          x:{ grid:{ display:false }, ticks:{ color:'#64748b', maxRotation:45, minRotation:0 } }
        }
      }
    });
  }
  function maybeSyncChart(){
    if (!sel) return;
    var mSel = selectedKeys(state.models);
    if (mSel.length === 1){
      for (var i=0;i<sel.options.length;i++){
        if (sel.options[i].value === mSel[0]){ sel.value = mSel[0]; break; }
      }
    }
    draw(sel.value);
  }
  if (sel){
    sel.addEventListener('change', function(e){ draw(e.target.value); });
    document.querySelectorAll('.seg-btn').forEach(function(btn){
      btn.addEventListener('click', function(){
        metric = btn.dataset.metric;
        document.querySelectorAll('.seg-btn').forEach(function(b){
          var on = b.dataset.metric===metric;
          b.classList.toggle('is-active', on);
          b.setAttribute('aria-pressed', on?'true':'false');
        });
        draw(sel.value);
      });
    });
  }

  renderChips();
  bindChips();
  setRate(7.0);
  if (sel) draw(sel.value);
})();
"""


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
                f'<div class="stat-card">'
                f'<div class="label">汇率 USD→CNY</div>'
                f'<div class="value" id="metricRate">7.00<small>¥/$</small></div>'
                f"</div>"
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
    tracking_block = _tracking_section(data.get("tracking") or [], data.get("has_tracking"))
    channel_block = _channel_section(data)
    chart_block = _chart_section(canons, bool(data.get("chart")))

    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    js = _JS.replace("__SITE_DATA__", data_json)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>大模型 Token 定价追踪</title>
<meta name="description" content="厂商官网原价与渠道同类报价分区展示；支持 DeepSeek/渠道筛选与自定义汇率。">
<meta name="theme-color" content="#4338ca">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
<style>{_CSS}</style>
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

  <div class="layout">
    {filter_block}
    <main class="container" id="main">
      <div class="sec-head">
        <div>
          <h2 class="section-title">定价总览</h2>
          <p class="section-sub">DeepSeek 置顶 · 筛选可组合 · 官网与渠道分区</p>
        </div>
      </div>
      <div class="sec-metrics">{metrics_html}</div>
      <div class="sec-actions">
        <button type="button" class="btn-filter-toggle" id="sidebarToggle" aria-label="展开筛选">≡ 筛选</button>
        <button type="button" id="btnExcel" class="btn-export">⬇ 导出 Excel</button>
      </div>

      {domestic_ms}
      {overseas_ms}
      {official_block}
      {overseas_block}
      {tracking_block}
      {channel_block}
      {chart_block}
    </main>
  </div>

  <button type="button" class="sidebar-reopen" id="sidebarReopen" aria-label="展开筛选">› 筛选</button>
  <div class="sidebar-backdrop" id="sidebarBackdrop"></div>

  <footer>
    <div class="note">数据来源：国内厂商官网公开定价；OpenAI / Anthropic / Google 官方 API 参考价；胜算云、腾讯云、火山引擎等渠道报价。USD 结算的渠道归入海外渠道页。GitHub Action 每周自动抓取。</div>
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
