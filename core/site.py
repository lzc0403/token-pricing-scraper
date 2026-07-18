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
CHANNEL_SOURCES = {"modelmesh", "tencent", "openrouter"}

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

        # 渠道：非官网
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


def _filter_toolbar() -> str:
    return """
    <section class="filter-bar" id="filterBar" aria-label="筛选与汇率">
      <div class="filter-top">
        <div>
          <div class="filter-kicker">FILTER & FX</div>
          <h2 class="filter-title">筛选与汇率</h2>
          <p class="filter-desc">按模型分类与渠道自由组合；可快速切「仅国内模型」或「仅海外模型」；汇率默认 7.0。</p>
        </div>
        <div class="rate-box">
          <label class="rate-label" for="fxRate">USD → CNY</label>
          <div class="rate-input-wrap">
            <input id="fxRate" class="rate-input" type="number" inputmode="decimal" min="0.1" max="100" step="0.01" value="7.0" aria-describedby="fxHint">
            <button type="button" id="fxReset" class="btn-ghost">重置 7.0</button>
          </div>
          <div id="fxHint" class="rate-hint">当前汇率 <strong id="fxCurrent">7.00</strong></div>
        </div>
      </div>

      <div class="filter-grid">
        <div class="filter-group">
          <div class="filter-group-head">
            <span class="filter-group-title">模型分类</span>
            <div class="mini-actions">
              <button type="button" class="linkish" data-scope="model" data-act="all">全选</button>
              <button type="button" class="linkish" data-scope="model" data-act="none">清空</button>
              <button type="button" class="linkish" data-scope="model" data-act="domestic">仅国内模型</button>
              <button type="button" class="linkish" data-scope="model" data-act="overseas">仅海外模型</button>
            </div>
          </div>
          <div id="modelChips" class="chip-row" role="group" aria-label="模型分类筛选"></div>
        </div>

        <div class="filter-group">
          <div class="filter-group-head">
            <span class="filter-group-title">渠道 / 来源</span>
            <div class="mini-actions">
              <button type="button" class="linkish" data-scope="channel" data-act="all">全选</button>
              <button type="button" class="linkish" data-scope="channel" data-act="none">清空</button>
            </div>
          </div>
          <div id="channelChips" class="chip-row" role="group" aria-label="渠道筛选"></div>
        </div>
      </div>

      <div class="filter-foot">
        <div class="active-summary" id="filterSummary">当前：全部模型 · 全部渠道 · 汇率 7.00</div>
        <div class="filter-actions">
          <button type="button" id="filterReset" class="btn-ghost">重置筛选</button>
          <span class="visible-count" id="visibleCount">显示 0 行</span>
        </div>
      </div>
    </section>
    """


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
          <div class="block-kicker">NEW MODEL RADAR</div>
          <h2 id="tracking-title" class="block-title">新品主动跟进</h2>
          <p class="block-desc">规则：新发布主流模型先登记监听（MiniMax M3 / Kimi K3 / Claude 5 等），命中报价后自动转为「已上榜」。不漏新模型。</p>
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

    accent: domestic（青绿）或 overseas（蓝色）
    """
    total_models = sum(len(v.get("models", [])) for v in vendors)
    vendor_cards: List[str] = []
    for vendor in vendors:
        vid = vendor.get("id") or "—"
        vname = vendor.get("name") or vid
        models = vendor.get("models", [])
        if not models:
            vendor_cards.append(
                f'<div class="ms-vendor" data-vendor="{_esc_attr(vid)}">'
                f'<div class="ms-vendor-head"><span class="ms-vendor-name">{_esc(vname)}</span>'
                f'<span class="ms-vendor-badge ms-pending">官方资料待核验</span></div>'
                f'<div class="ms-empty-vendor">该厂商正式型号暂未进入主流目录</div>'
                f"</div>"
            )
            continue
        model_cards: List[str] = []
        for model in models:
            canon = model.get("canonical") or "—"
            display = model.get("display_name") or canon
            tier = model.get("display_tier") or {}
            ctx_label = model.get("context_label") or "—"
            ctx_tokens = model.get("context_tokens") or ""
            role = model.get("role") or ""
            inp = tier.get("input_price")
            out = tier.get("output_price")
            cache = tier.get("cache_input_price")
            currency = model.get("currency") or ""
            tier_count = model.get("tier_count") or 0
            has_channel = model.get("has_channel_price")
            featured = model.get("featured")
            verified = (model.get("verified_at") or "")[:10]

            price_html = (
                f'<div class="ms-prices">'
                f'<span class="ms-price"><b>{_fmt_num(inp)}</b> <small>{currency}/输入</small></span>'
                f'<span class="ms-price"><b>{_fmt_num(out)}</b> <small>{currency}/输出</small></span>'
                f"</div>"
                if isinstance(inp, (int, float)) and isinstance(out, (int, float))
                else '<div class="ms-prices ms-no-price"><span>价格待官方公布</span></div>'
            )
            cache_html = (
                f'<span class="ms-cache">缓存写入 {_fmt_num(cache)} {currency}</span>'
                if isinstance(cache, (int, float))
                else ""
            )
            tiers_html = ""
            if tier_count > 1:
                tiers_list = "".join(
                    f'<li>{_esc(t.get("condition") or "—")}：'
                    f"{_fmt_num(t.get('input_price'))} / {_fmt_num(t.get('output_price'))} {currency}</li>"
                    for t in model.get("pricing", {}).get("tiers", [])
                )
                tiers_html = f'<details class="ms-tiers"><summary>分档计费（{tier_count} 档）</summary><ul>{tiers_list}</ul></details>'

            channel_html = (
                '<span class="ms-channel-ok">有渠道报价</span>'
                if has_channel
                else '<span data-empty-state="no-channel-price" class="ms-channel-empty">暂无渠道报价</span>'
            )
            hot_badge = '<span class="ms-featured">热门</span>' if featured else ""

            model_cards.append(
                f'<article class="model-pick" data-canonical="{_esc_attr(canon)}" '
                f'data-context="{_esc_attr(ctx_tokens)}" data-source="{_esc_attr(vendor.get("source_id") or vid)}" '
                f'tabindex="0" role="button" aria-label="筛选 {_esc(display)}">'
                f'<div class="ms-model-head">'
                f'<span class="ms-model-name">{_esc(display)}{hot_badge}</span>'
                f'<span class="ms-context">{_esc(ctx_label)}</span>'
                f"</div>"
                f'<div class="ms-role">{_esc(role)}</div>'
                f"{price_html}{cache_html}"
                f"{tiers_html}"
                f'<div class="ms-meta">{channel_html}<span class="ms-verified">核验 {_esc(verified)}</span></div>'
                f"</article>"
            )
        vendor_cards.append(
            f'<div class="ms-vendor" data-vendor="{_esc_attr(vid)}">'
            f'<div class="ms-vendor-head"><span class="ms-vendor-name">{_esc(vname)}</span>'
            f'<span class="ms-vendor-count">{len(models)} 款</span></div>'
            f'<div class="ms-model-grid">{"".join(model_cards)}</div>'
            f"</div>"
        )

    vendors_html = "\n".join(vendor_cards)
    accent_class = "ms-overseas" if accent == "overseas" else "ms-domestic"
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
      <div class="ms-vendors">
        {vendors_html}
      </div>
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
  --primary:#4f46e5; --primary-deep:#4338ca; --primary-soft:#eef2ff;
  --brand-dark:#1e1b4b;
  --green:#059669; --green-soft:#ecfdf5; --green-deep:#047857;
  --amber:#b45309; --amber-soft:#fffbeb;
  --red:#dc2626; --red-soft:#fef2f2;
  --canvas:#fff; --bg:#f8fafc; --line:#e2e8f0;
  --ink:#0f172a; --ink2:#334155; --mute:#64748b;
  --shadow:0 1px 2px rgba(15,23,42,.05), 0 8px 24px rgba(15,23,42,.04);
  --r:14px;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font-family:Inter,'Noto Sans SC',system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
  background:var(--bg);color:var(--ink);-webkit-font-smoothing:antialiased;line-height:1.5}
.visually-hidden{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);border:0}
:focus-visible{outline:2px solid var(--primary);outline-offset:2px}

.hero{background:linear-gradient(135deg,#1e1b4b 0%,#4338ca 100%);position:relative;overflow:hidden}
.hero .mesh{position:absolute;inset:0;background:
  radial-gradient(40% 50% at 15% 20%, rgba(165,180,252,.3), transparent 60%),
  radial-gradient(40% 50% at 85% 15%, rgba(99,102,241,.22), transparent 60%)}
.hero-inner{position:relative;z-index:1;max-width:1120px;margin:0 auto;padding:52px 24px 40px}
.eyebrow{display:inline-block;font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:#c7d2fe;
  border:1px solid rgba(255,255,255,.16);background:rgba(255,255,255,.08);padding:6px 12px;border-radius:999px}
.hero h1{color:#fff;font-size:34px;margin:14px 0 8px;font-weight:800;letter-spacing:-.02em;line-height:1.15}
.hero .sub{color:rgba(255,255,255,.78);margin:0;max-width:640px;font-size:15px}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:24px}
.stat-card{background:#fff;border-radius:12px;padding:14px 16px;box-shadow:var(--shadow)}
.stat-card .label{color:var(--mute);font-size:12px;margin-bottom:4px}
.stat-card .value{color:var(--primary-deep);font-size:24px;font-weight:800;font-variant-numeric:tabular-nums}
.stat-card .value small{font-size:12px;color:var(--mute);margin-left:4px;font-weight:600}

.container{max-width:1120px;margin:0 auto;padding:28px 24px 56px}
.sec-head{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;flex-wrap:wrap;margin:0 0 18px}
.section-title{font-size:22px;font-weight:800;margin:0 0 4px;letter-spacing:-.01em}
.section-sub{margin:0;color:var(--mute);font-size:14px}

.block-card{background:#fff;border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--shadow);margin-bottom:18px;overflow:hidden}
.block-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;padding:18px 20px 12px}
.block-kicker{font-size:11px;font-weight:700;letter-spacing:.08em;color:var(--primary);margin-bottom:4px}
.block-title{font-size:18px;font-weight:800;margin:0 0 4px;letter-spacing:-.01em}
.block-desc{margin:0;color:var(--mute);font-size:13.5px;line-height:1.45;max-width:720px}
.block-count{font-size:12px;font-weight:700;color:var(--mute);background:var(--bg);border:1px solid var(--line);padding:4px 10px;border-radius:999px;white-space:nowrap}
.block-official .block-kicker{color:var(--amber)}
.block-official{border-color:#fde68a}

/* 筛选栏 */
.filter-bar{background:#fff;border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--shadow);padding:18px 20px;margin:0 0 18px}
.filter-top{display:flex;justify-content:space-between;gap:18px;flex-wrap:wrap;margin-bottom:14px}
.filter-kicker{font-size:11px;font-weight:700;letter-spacing:.08em;color:var(--primary);margin-bottom:4px}
.filter-title{margin:0 0 4px;font-size:18px;font-weight:800;letter-spacing:-.01em}
.filter-desc{margin:0;color:var(--mute);font-size:13.5px;max-width:640px;line-height:1.45}
.rate-box{min-width:220px;background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.rate-label{display:block;font-size:12px;font-weight:700;color:var(--mute);margin-bottom:6px}
.rate-input-wrap{display:flex;gap:8px;align-items:center}
.rate-input{width:110px;border:1px solid var(--line);border-radius:10px;padding:9px 10px;font:inherit;font-weight:700;color:var(--ink);background:#fff}
.rate-input:focus{outline:2px solid var(--primary);outline-offset:1px}
.rate-hint{margin-top:6px;font-size:12px;color:var(--mute)}
.rate-hint strong{color:var(--primary-deep)}
.filter-grid{display:grid;grid-template-columns:1.1fr 1fr;gap:12px}
.filter-group{border:1px solid var(--line);border-radius:12px;background:linear-gradient(180deg,#fff 0%,#fbfcfe 100%);padding:12px}
.filter-group-head{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px}
.filter-group-title{font-size:13px;font-weight:800;color:var(--ink2)}
.mini-actions{display:flex;gap:8px}
.linkish{border:0;background:transparent;color:var(--primary);font:inherit;font-size:12px;font-weight:700;cursor:pointer;padding:0}
.linkish:hover{text-decoration:underline}
.chip-row{display:flex;flex-wrap:wrap;gap:8px}
.chip{border:1px solid var(--line);background:#fff;color:var(--ink2);border-radius:999px;padding:7px 12px;font:inherit;font-size:12.5px;font-weight:700;cursor:pointer;transition:.15s}
.chip:hover{border-color:#c7d2fe;background:var(--primary-soft)}
.chip.is-on{background:var(--primary);border-color:var(--primary);color:#fff;box-shadow:0 2px 8px rgba(79,70,229,.22)}
.filter-foot{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-top:12px;padding-top:12px;border-top:1px dashed var(--line)}
.active-summary{font-size:13px;color:var(--mute)}
.filter-actions{display:flex;align-items:center;gap:10px}
.btn-ghost{border:1px solid var(--line);background:#fff;color:var(--ink2);border-radius:10px;padding:8px 12px;font:inherit;font-size:12.5px;font-weight:700;cursor:pointer}
.btn-ghost:hover{background:var(--bg)}
.visible-count{font-size:12.5px;font-weight:700;color:var(--primary-deep);background:var(--primary-soft);border-radius:999px;padding:6px 10px}
tr.js-row.is-hidden{display:none}
.empty-filter{display:none;padding:28px 16px;text-align:center;color:var(--mute);font-size:13.5px}
.empty-filter.is-show{display:block}

.market-tabs{display:inline-flex;margin:0 20px 10px;background:var(--bg);border:1px solid var(--line);border-radius:11px;padding:4px;gap:4px}
.market-tab{border:0;background:transparent;color:var(--mute);font:inherit;font-size:13.5px;font-weight:700;padding:9px 16px;border-radius:8px;cursor:pointer}
.market-tab.is-active{background:var(--primary);color:#fff}
.market-panel{padding:0 0 8px}
.market-panel[hidden]{display:none!important}
.panel-hint{margin:0 20px 10px;color:var(--mute);font-size:13px}

.table-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch;padding:0 0 8px}
.price-table{width:100%;border-collapse:separate;border-spacing:0;min-width:900px;table-layout:fixed}
.w-model{width:24%}.w-canon{width:14%}.w-source{width:11%}.w-num{width:11%}.w-ctx{width:12%}.w-curr{width:6%}
.price-table th,.price-table td{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:middle;font-size:13.5px;text-align:left}
.price-table th{position:sticky;top:0;z-index:1;background:#f8fafc;color:var(--mute);font-size:12px;font-weight:700;white-space:nowrap}
.price-table th.sortable{cursor:pointer;user-select:none}
.price-table th.sortable:hover{color:var(--primary-deep);background:var(--primary-soft)}
.price-table th.sortable::after{content:"⇅";margin-left:4px;font-size:10px;opacity:.4}
.price-table th.sortable[aria-sort="ascending"]::after{content:"↑";opacity:1;color:var(--primary)}
.price-table th.sortable[aria-sort="descending"]::after{content:"↓";opacity:1;color:var(--primary)}
.price-table th.num,.price-table td.num{text-align:right;font-variant-numeric:tabular-nums;font-weight:600;white-space:nowrap}
.price-table tbody tr:hover{background:#fafbff}
.price-table tbody tr:last-child td{border-bottom:0}

.c-model .model{font-weight:700;color:var(--ink2);line-height:1.3;word-break:break-word}
.tags{display:flex;flex-wrap:wrap;gap:5px;margin-top:5px}
.tag{display:inline-block;font-size:10.5px;font-weight:700;padding:1px 7px;border-radius:999px;border:1px solid transparent}
.tag-official{color:var(--amber);background:var(--amber-soft);border-color:rgba(180,83,9,.12)}
.tag-best{color:var(--green-deep);background:var(--green-soft);border-color:rgba(5,150,105,.12)}
.tag-premium{color:var(--red);background:var(--red-soft)}
.muted{color:var(--mute);font-weight:500}
.pill{display:inline-block;padding:3px 9px;border-radius:8px;font-size:12px;font-weight:700;
  background:#f1f5f9;color:var(--ink2);border:1px solid var(--line)}
.sub-hint{font-size:11px;color:var(--mute);font-weight:500;margin-top:2px}
.c-curr{text-align:center;font-weight:600;font-size:12px;color:var(--ink2)}

/* 官方行：极淡底 + 左边细线，不铺大色块 */
tr.is-official td{background:#fffdf7}
tr.is-official td:first-child{box-shadow:inset 3px 0 0 #f59e0b}
tr.is-lowest:not(.is-official) td:first-child{box-shadow:inset 3px 0 0 var(--green)}

.empty-mini{padding:36px 20px;text-align:center;color:var(--mute);font-size:14px}

.chart-card{padding-bottom:16px}
.chart-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;flex-wrap:wrap;padding:18px 20px 10px}
.chart-controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.chart-wrap{height:340px;padding:0 12px 8px;position:relative}
.seg{display:inline-flex;background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:3px;gap:2px}
.seg-btn{border:0;background:transparent;color:var(--mute);font:inherit;font-size:13px;font-weight:600;padding:7px 12px;border-radius:8px;cursor:pointer}
.seg-btn.is-active{background:#fff;color:var(--primary-deep);box-shadow:0 1px 2px rgba(15,23,42,.06)}
select{font:inherit;padding:9px 12px;border-radius:10px;border:1px solid var(--line);background:#fff;min-width:180px;cursor:pointer}

.btn-export{display:inline-flex;align-items:center;gap:6px;border:0;background:var(--green);color:#fff;
  font:inherit;font-size:13.5px;font-weight:700;padding:10px 14px;border-radius:10px;cursor:pointer}
.btn-export:hover{background:var(--green-deep)}
.btn-export[disabled]{opacity:.6;cursor:wait}

footer{background:var(--brand-dark);color:rgba(255,255,255,.72);padding:24px;text-align:center;font-size:13px;line-height:1.65;margin-top:12px}
footer .note{max-width:780px;margin:0 auto 8px}
footer strong{color:#c7d2fe}
footer .disc{color:#a5b4fc}

.totop{position:fixed;right:16px;bottom:16px;width:42px;height:42px;border:0;border-radius:50%;
  background:var(--primary);color:#fff;font-size:18px;cursor:pointer;opacity:0;visibility:hidden;
  transform:translateY(8px);transition:.2s;z-index:40;box-shadow:var(--shadow)}
.totop.is-show{opacity:1;visibility:visible;transform:none}



.hot-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;padding:0 20px 14px}
.hot-card{background:linear-gradient(180deg,#f8fafc 0%,#fff 100%);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.hot-card[data-source="openai"]{border-color:#a7f3d0;background:linear-gradient(180deg,#ecfdf5 0%,#fff 70%)}
.hot-card[data-source="anthropic"]{border-color:#fed7aa;background:linear-gradient(180deg,#fff7ed 0%,#fff 70%)}
.hot-card[data-source="google"]{border-color:#bfdbfe;background:linear-gradient(180deg,#eff6ff 0%,#fff 70%)}
.hot-brand{font-size:11px;font-weight:800;color:var(--mute);letter-spacing:.04em;text-transform:uppercase}
.hot-name{font-size:16px;font-weight:800;margin:4px 0 8px;color:var(--ink)}
.hot-price{display:flex;align-items:baseline;justify-content:space-between;gap:8px;font-weight:800;color:var(--ink2);font-variant-numeric:tabular-nums}
.hot-price small{font-size:11px;color:var(--mute);font-weight:600}
.hot-price.muted{margin-top:2px;font-weight:600;color:var(--mute)}
.tag-hot{color:#b45309;background:#fffbeb;border-color:rgba(180,83,9,.14)}
.block-tracking{border-color:#e9d5ff}
.block-tracking .block-kicker{color:#7c3aed}
.track-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:0 20px 18px}
.track-card{border:1px solid var(--line);border-radius:12px;padding:14px;background:#fafafa}
.track-card.is-tracking{background:linear-gradient(180deg,#faf5ff 0%,#fff 80%);border-color:#e9d5ff}
.track-card.is-active{background:linear-gradient(180deg,#ecfdf5 0%,#fff 80%);border-color:#a7f3d0}
.track-top{display:flex;justify-content:space-between;gap:8px;margin-bottom:6px}
.track-family{font-size:11px;font-weight:800;color:var(--mute)}
.track-status{font-size:11px;font-weight:800;padding:2px 8px;border-radius:999px;background:#fff;border:1px solid var(--line)}
.track-card.is-tracking .track-status{color:#7c3aed;border-color:#ddd6fe;background:#f5f3ff}
.track-card.is-active .track-status{color:#047857;border-color:#a7f3d0;background:#ecfdf5}
.track-name{font-size:16px;font-weight:800;color:var(--ink);margin-bottom:6px}
.track-meta{display:flex;gap:10px;font-size:12px;color:var(--mute);font-weight:600;margin-bottom:8px}
.track-note{margin:0;font-size:12.5px;color:var(--ink2);line-height:1.45}
@media (max-width:1024px){.hot-strip{grid-template-columns:repeat(2,1fr)}.track-grid{grid-template-columns:1fr 1fr}}
@media (max-width:760px){.hot-strip,.track-grid{grid-template-columns:1fr}}

.block-overseas{border-color:#c7d2fe}
.block-overseas .block-kicker{color:#4338ca}
.block-head-right{display:flex;flex-direction:column;align-items:flex-end;gap:6px}
.block-fam{font-size:11px;font-weight:700;color:var(--mute);letter-spacing:.02em}
.family-strip{display:flex;gap:8px;padding:0 20px 10px}
.fam-chip{font-size:11px;font-weight:800;padding:4px 10px;border-radius:999px;border:1px solid var(--line);background:#fff;color:var(--ink2)}
.fam-openai{background:#ecfdf5;border-color:#a7f3d0;color:#047857}
.fam-claude{background:#fff7ed;border-color:#fed7aa;color:#c2410c}
.fam-gemini{background:#eff6ff;border-color:#bfdbfe;color:#1d4ed8}
.tag-global{color:#4338ca;background:#eef2ff;border-color:rgba(79,70,229,.14)}
.tag-family{color:#334155;background:#f8fafc;border-color:var(--line)}
.overseas-note{margin:4px 20px 14px}

/* 主流模型双专区 */
.block-mainstream{border-color:#d1fae5}
.block-mainstream.ms-overseas{border-color:#dbeafe}
.ms-domestic .block-kicker{color:#059669}
.ms-overseas .block-kicker{color:#2563eb}
.ms-vendors{display:grid;grid-template-columns:1fr;gap:16px;padding:0 20px 16px}
.ms-vendor{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.ms-vendor-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
.ms-vendor-name{font-size:15px;font-weight:800;color:var(--ink)}
.ms-vendor-count{font-size:11px;font-weight:700;color:var(--mute);background:#f1f5f9;padding:3px 8px;border-radius:999px}
.ms-vendor-badge{font-size:11px;font-weight:700;padding:3px 8px;border-radius:999px}
.ms-pending{background:#fef3c7;color:#92400e;border:1px solid #fde68a}
.ms-empty-vendor{font-size:13px;color:var(--mute);padding:8px 0}
.ms-model-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.model-pick{background:linear-gradient(180deg,#fafcff 0%,#fff 100%);border:1px solid var(--line);border-radius:12px;padding:12px 14px;cursor:pointer;transition:border-color .15s,box-shadow .15s;outline:none}
.model-pick:hover,.model-pick:focus-visible{border-color:#34d399;box-shadow:0 0 0 3px rgba(52,211,153,.15)}
.ms-overseas .model-pick:hover,.ms-overseas .model-pick:focus-visible{border-color:#60a5fa;box-shadow:0 0 0 3px rgba(96,165,250,.15)}
.ms-model-head{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:4px}
.ms-model-name{font-size:14px;font-weight:800;color:var(--ink)}
.ms-context{font-size:11px;font-weight:700;color:var(--mute);background:#f1f5f9;padding:2px 7px;border-radius:6px;white-space:nowrap}
.ms-role{font-size:12px;color:var(--mute);margin-bottom:8px}
.ms-prices{display:flex;gap:12px;margin-bottom:6px}
.ms-price{display:flex;flex-direction:column}
.ms-price b{font-size:16px;font-weight:800;color:var(--ink)}
.ms-price small{font-size:10px;color:var(--mute)}
.ms-no-price{color:var(--mute);font-size:13px;font-style:italic}
.ms-cache{font-size:11px;color:var(--mute);display:block;margin-bottom:4px}
.ms-tiers{margin:6px 0}
.ms-tiers summary{font-size:11px;font-weight:700;color:var(--ink2);cursor:pointer}
.ms-tiers ul{margin:4px 0 0;padding-left:16px;font-size:11px;color:var(--mute)}
.ms-tiers li{margin:2px 0}
.ms-meta{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:8px;font-size:11px}
.ms-channel-ok{color:#059669;font-weight:700}
.ms-channel-empty{color:#9ca3af}
.ms-featured{display:inline-block;font-size:10px;font-weight:800;color:#fff;background:#f59e0b;padding:1px 6px;border-radius:4px;margin-left:6px;vertical-align:middle}
.ms-verified{color:var(--mute)}
@media (max-width:1024px){.ms-model-grid{grid-template-columns:repeat(2,1fr)}}
@media (max-width:760px){.ms-model-grid{grid-template-columns:1fr}}
tr[data-source="openai"] .pill{background:#ecfdf5;border-color:#a7f3d0;color:#047857}
tr[data-source="anthropic"] .pill{background:#fff7ed;border-color:#fed7aa;color:#c2410c}
tr[data-source="google"] .pill{background:#eff6ff;border-color:#bfdbfe;color:#1d4ed8}

@media (max-width:1024px){.metrics{grid-template-columns:repeat(2,1fr)};.filter-grid{grid-template-columns:1fr}}
@media (max-width:760px){
  .hero-inner{padding:40px 16px 28px}
  .hero h1{font-size:26px}
  .container{padding:20px 14px 40px}
  .btn-export{width:100%;justify-content:center}
  .market-tabs{margin-left:14px;margin-right:14px;display:flex;width:calc(100% - 28px)}
  .market-tab{flex:1}
  .panel-hint,.block-head,.chart-head{padding-left:14px;padding-right:14px}
  .chart-wrap{height:280px}
  .price-table th,.price-table td{padding:9px 8px;font-size:12.5px}
  .filter-bar{padding:14px}
  .rate-input-wrap{flex-wrap:wrap}
}
@media (max-width:480px){.metrics{grid-template-columns:1fr}}
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

    filter_block = _filter_toolbar()
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
      <div class="metrics">{metrics_html}</div>
    </div>
  </header>

  <main class="container" id="main">
    <div class="sec-head">
      <div>
        <h2 class="section-title">定价总览</h2>
        <p class="section-sub">DeepSeek 置顶 · 筛选可组合 · 官网与渠道分区</p>
      </div>
      <button type="button" id="btnExcel" class="btn-export">⬇ 导出 Excel</button>
    </div>

    {filter_block}
    {domestic_ms}
    {overseas_ms}
    {official_block}
    {overseas_block}
    {tracking_block}
    {channel_block}
    {chart_block}
  </main>

  <footer>
    <div class="note">数据来源：国内厂商官网公开定价；OpenAI / Anthropic / Google 官方 API 参考价；胜算云、腾讯云等渠道报价。腾讯云中国大陆区域 USD 归入海外渠道页。GitHub Action 每周自动抓取。</div>
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
