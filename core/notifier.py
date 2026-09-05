"""价格变动推送：对比当前与上一日快照，推送飞书 / 企业微信 webhook。

设计：
- 无外部依赖（标准库 urllib），不引入 requests 额外负担。
- 完全配置驱动：未设置 webhook 环境变量时静默跳过，不影响主流程。
- 支持飞书自定义机器人（markdown）与企业微信机器人（markdown）两种格式。

环境变量：
- FEISHU_WEBHOOK_URL : 飞书自定义机器人 webhook 地址
- WECOM_WEBHOOK_URL  : 企业微信机器人 webhook 地址
- PRICE_WEBHOOK_URL  : 通用 webhook 地址（配合 PRICE_WEBHOOK_TYPE=feishu|wecom）
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("tps.notify")


SITE_URL = "https://lzc0403.github.io/token-pricing-scraper/"

# 变动幅度达到该阈值（绝对值 %）的归入「重点变动」，其余进「其他变动」
MAJOR_PCT = 30.0

_FIELD_LABEL = {"input": "入", "output": "出", "cache": "缓存", "cache_hit": "缓存命中", "cache_write": "缓存写入"}
_CUR_SYMBOL = {"USD": "$", "CNY": "¥", "USDT": "$"}
_FIELD_ORDER = {"input": 0, "output": 1, "cache_hit": 2, "cache_write": 3, "cache": 4}

# 来源 ID → 站点中文名（与站点页 SOURCE_LABELS 保持一致）
SOURCE_LABELS = {
    "tencent": "腾讯云国际",
    "tencent_cn": "腾讯云CN",
    "aliyun": "阿里云",
    "aliyun_intl": "阿里云国际",
    "aliyun_bailian": "阿里云百炼",
    "volcengine": "火山引擎",
    "volcengine_intl": "火山云海外",
    "bigmodel": "智谱",
    "zai": "智谱Z.ai",
    "deepseek": "DeepSeek官网",
    "deepseek_us": "DeepSeek海外官网",
    "minimax": "MiniMax官网",
    "kimi": "Kimi官网",
    "openai": "OpenAI官网",
    "anthropic": "Anthropic官网",
    "google": "Google官网",
    "gemini": "Gemini官网",
    "grok": "Grok官网",
    "openrouter": "OpenRouter",
    "atlascloud": "AtlasCloud",
    "modelmesh": "胜算云",
}

# 官方调价预警区块用的字段中文全称（区分缓存命中/写入两种计费动作）
_FIELD_CN = {
    "input": "输入",
    "output": "输出",
    "cache_hit": "缓存命中",
    "cache_write": "缓存写入",
    "cache": "缓存",
}


def _condition_label(condition: Any) -> str:
    """计费口径 → 人类可读短标签。空/None 返回空串。"""
    c = str(condition or "").strip()
    if not c or c == "None":
        return ""
    # 常见口径映射；未识别的原文展示
    mapping = {
        "空闲时段 | 原厂直供": "原厂·闲时",
        "高峰时段 | 原厂直供": "原厂·高峰",
        "原厂直供": "原厂直供",
        "腾讯云自建": "自建",
        "阿里云自部署": "自部署",
        "火山引擎自部署": "自部署",
        "峰谷计费": "峰谷",
    }
    return mapping.get(c) or c


def _fmt_currency(v: Any, cur: str) -> str:
    if v is None:
        return "—"
    sym = _CUR_SYMBOL.get(cur, cur)
    try:
        fv = float(v)
    except (TypeError, ValueError):
        return f"{sym}{v}"
    s = f"{fv:.2f}".rstrip("0").rstrip(".") or "0"
    return f"{sym}{s}"


def _pct(old: Any, new: Any) -> Optional[float]:
    """涨跌幅百分比：(new-old)/old*100。无法计算返回 None。"""
    try:
        if old in (None, 0) or new is None:
            return None
        return (float(new) - float(old)) / float(old) * 100
    except (TypeError, ValueError):
        return None


def _fmt_pct(p: Optional[float]) -> str:
    if p is None:
        return ""
    arrow = "⬆️" if p > 0 else ("⬇️" if p < 0 else "➡️")
    return f"{arrow}{'+' if p > 0 else ''}{p:.0f}%"


def _group_key(d: Dict[str, Any]) -> tuple:
    return (d.get("canonical") or "?", d.get("source") or "?", d.get("condition") or "")


# ---------------------------------------------------------------------------
# 分时档位归并：区分「刊例价整体调整」与「分时结构调整」
#
# 同一 (模型, 来源) 下常有闲时/高峰两条计费口径。若两档同字段涨跌幅一致
# （±_TIER_TOL_PP 百分点内且方向相同），说明只是刊例价变了、峰谷比例没动
# —— 应合并为一条「刊例价调整」，而不是误报成两次独立涨价；
# 若仅一档变动或两档幅度背离，则是峰谷价差结构本身在调整，需单独提示。
# ---------------------------------------------------------------------------

_TIER_TOL_PP = 3.0  # 各档涨跌幅一致性容差（百分点）


def _is_tier(condition: Any) -> bool:
    """该行是否属于分时档位（闲时/高峰/峰谷）。"""
    c = str(condition or "")
    return "闲" in c or "峰" in c


def consolidate_tiers(deltas: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """归并分时档位，返回 (归并后的 deltas, 发生结构调整的模型名列表)。

    - 各档涨跌幅一致 → 只保留闲时档为代表（标记 tier_sync=True），计数不重复
    - 幅度背离或单档变动 → 全部保留，模型名记入结构性调整清单
    """
    by_cs: Dict[tuple, List[Dict[str, Any]]] = {}
    for d in deltas:
        by_cs.setdefault((d.get("canonical"), d.get("source")), []).append(d)

    out: List[Dict[str, Any]] = []
    structural: List[str] = []
    for (canon, _src), items in by_cs.items():
        tier_items = [d for d in items if _is_tier(d.get("condition"))]
        plain = [d for d in items if not _is_tier(d.get("condition"))]
        conds = sorted({str(d.get("condition")) for d in tier_items})
        # 该模型在该来源下的档位总数（来自 store 对比阶段，含未变动档）
        tier_n = max((int(d.get("tier_count") or 0) for d in items), default=0)
        if len(conds) >= 2:
            # 多档都有变动：逐字段比较各档涨跌幅是否一致
            fields = {d.get("field") for d in tier_items}
            synced = True
            for f in fields:
                ps = [
                    _pct(d.get("old"), d.get("new"))
                    for d in tier_items
                    if d.get("field") == f
                ]
                ps_clean: List[float] = [p for p in ps if p is not None]
                # 某字段只有一档有变动 → 价差结构在调整
                if len(ps_clean) == 1:
                    synced = False
                    break
                if len(ps_clean) >= 2 and (
                    max(ps_clean) - min(ps_clean) > _TIER_TOL_PP
                    or len({p > 0 for p in ps_clean}) > 1
                ):
                    synced = False
                    break
            if synced:
                # 刊例价整体调整：取闲时档作代表，避免重复计数
                rep_cond = next((c for c in conds if "闲" in c), conds[0])
                for d in tier_items:
                    if str(d.get("condition")) == rep_cond:
                        nd = dict(d)
                        nd["tier_sync"] = True
                        out.append(nd)
                out.extend(plain)
                continue
            structural.append(str(canon))
        elif tier_n >= 2 and len(conds) == 1:
            # 模型确有多档但仅一档出现变动 → 峰谷价差结构调整
            structural.append(str(canon))
        out.extend(items)
    return out, structural


# ---------------------------------------------------------------------------
# 官网基准（市场行情锚点）
#
# 永远以大模型厂商官网原价为行情基准：
#   - 官网调价 + 渠道未跟进 → 「市场行情」强提醒：价差扩大，渠道报价即将过期；
#   - 官网调价 + 渠道同幅跟进 → 渠道行标「跟进官网」，不再重复报警
#     （即"官网正式调价的第二天，渠道跟上了就恢复正常"）。
# 判定按换算后的涨跌幅百分比比较，天然跨币种可比（CNY 官网 vs USD 渠道）。
# ---------------------------------------------------------------------------

# 多币种厂商的官方源集合（与 site_data._is_official_any_currency 同口径镜像，
# 由 test_notifier_official_source_mirror 保证两处不漂移）
_OFFICIAL_SOURCES_ANY: Dict[str, Tuple[str, ...]] = {
    "DeepSeek": ("deepseek", "deepseek_us"),
    "GLM": ("bigmodel", "zai"),
    "Kimi": ("kimi", "kimi_ai"),
}

# 单一官方源厂商（canonical 前缀 → source id），与 site_data.OFFICIAL_SOURCE 镜像
_OFFICIAL_SINGLE: Tuple[Tuple[str, str], ...] = (
    ("MiniMax", "minimax"),
    ("Qwen", "aliyun"),
    ("Doubao", "volcengine"),
    ("GPT", "openai"),
    ("Claude", "anthropic"),
    ("Gemini", "gemini"),
    ("Grok", "grok"),
)

# 官网 vs 渠道涨跌幅一致性容差（百分点）：同字段百分比差在此范围内视为「跟进」
_FOLLOW_TOL_PP = 10.0


def is_official_source(canonical: Any, source: Any) -> bool:
    """该 (模型, 来源) 是否为厂商官网原价（不分币种）。"""
    canon = str(canonical or "")
    src = str(source or "")
    for prefix, sources in _OFFICIAL_SOURCES_ANY.items():
        if canon.startswith(prefix) and src in sources:
            return True
    for prefix, src_id in _OFFICIAL_SINGLE:
        if canon.startswith(prefix) and src == src_id:
            return True
    return False


def _market_analysis(deltas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """官网基准行情分析：标注每条 delta 的市场语义。

    对每条官网源 delta，找该模型所有渠道源的变动做参照：
      - 渠道无同字段变动，或幅度与官网背离超容差 → 标 official_lead=True
        （渠道未跟进，价差扩大，属市场行情变化）
      - 存在渠道源与官网同幅变动 → 该渠道行标 follows_official=True
        （渠道已同步跟进官网新价，正常播报不额外报警）

    返回浅拷贝标注后的列表（不修改入参）。
    """
    # 索引：模型 → {field: [(source, pct), ...]}（仅渠道源变动）
    channel_moves: Dict[str, Dict[str, List[Tuple[str, float]]]] = {}
    for d in deltas:
        canon = str(d.get("canonical") or "")
        if is_official_source(canon, d.get("source")):
            continue
        p = _pct(d.get("old"), d.get("new"))
        if p is None:
            continue
        channel_moves.setdefault(canon, {}).setdefault(str(d.get("field")), []).append(
            (str(d.get("source")), p)
        )

    out: List[Dict[str, Any]] = []
    for d in deltas:
        nd = dict(d)
        canon = str(nd.get("canonical") or "")
        field = str(nd.get("field"))
        if is_official_source(canon, nd.get("source")):
            p = _pct(nd.get("old"), nd.get("new"))
            if p is None:
                out.append(nd)
                continue
            moves = channel_moves.get(canon, {}).get(field, [])
            # 官网行：存在任一渠道同幅变动 → 视为已被跟进，不发行情警报；
            # 渠道没动或幅度背离 → 官网领先，价差扩大，发市场行情提醒
            followed = any(abs(p - cp) <= _FOLLOW_TOL_PP for _, cp in moves)
            nd["official_lead"] = not followed
        else:
            p = _pct(nd.get("old"), nd.get("new"))
            # 渠道行：该模型该字段有官网变动且本渠道与之同幅 → 标记跟进
            _raw_ps = [
                _pct(x.get("old"), x.get("new"))
                for x in deltas
                if str(x.get("canonical")) == canon
                and str(x.get("field")) == field
                and is_official_source(canon, x.get("source"))
            ]
            official_ps: List[float] = [x for x in _raw_ps if x is not None]
            nd["follows_official"] = bool(
                p is not None and any(abs(p - op) <= _FOLLOW_TOL_PP for op in official_ps)
            )
        out.append(nd)
    return out


def _official_price_alerts(
    deltas: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """官方调价预警：厂商官网价格发生变动的所有条目（供人工跟进处理）。

    与 `_market_analysis` 的「市场行情」规则（仅渠道未跟进才报警）**职责不同**：
    这里无条件列出每一条官方调价——官方价是定价锚点，任何调整都需要人工确认
    是否同步更新内部比价口径、成本核算与采购决策。渠道是否同步跟进只作为
    附加状态展示，不决定是否提醒。

    返回按最大幅度降序的列表，每项：
        {
          "canonical": 模型名,
          "source": 官方源 id,
          "source_label": 官方源中文名,
          "condition": 计费口径,
          "max_pct": 该模型本次官方调价的最大绝对幅度（%），
          "items": [ {field, field_cn, old, new, pct, currency,
                      followed, followers}, ... ]  按字段序排列
        }

    followed：存在渠道源同字段、同幅度（≤_FOLLOW_TOL_PP）变动 → 已跟进；
    否则为 False（渠道未动或幅度背离；注意 deltas 只含变动记录，无法区分
    「渠道存在但未调价」与「该模型无此渠道」两种情况，故措辞为未见同步）。
    """
    # 索引：模型 → {field: [(source, pct), ...]}（仅非官方源变动）
    channel_moves: Dict[str, Dict[str, List[Tuple[str, float]]]] = {}
    for d in deltas:
        canon = str(d.get("canonical") or "")
        if is_official_source(canon, d.get("source")):
            continue
        p = _pct(d.get("old"), d.get("new"))
        if p is None:
            continue
        channel_moves.setdefault(canon, {}).setdefault(str(d.get("field")), []).append(
            (str(d.get("source")), p)
        )

    grouped: Dict[tuple, List[Dict[str, Any]]] = {}
    for d in deltas:
        canon = str(d.get("canonical") or "")
        src = str(d.get("source") or "")
        if not is_official_source(canon, d.get("source")):
            continue
        p = _pct(d.get("old"), d.get("new"))
        if p is None:
            continue  # 新增/下架等无幅度变动不属「调价」
        field = str(d.get("field"))
        moves = channel_moves.get(canon, {}).get(field, [])
        followers = sorted(
            SOURCE_LABELS.get(s, s) for s, cp in moves if abs(p - cp) <= _FOLLOW_TOL_PP
        )
        key = (canon, src, str(d.get("condition") or ""))
        grouped.setdefault(key, []).append(
            {
                "field": field,
                "field_cn": _FIELD_CN.get(field, field),
                "old": d.get("old"),
                "new": d.get("new"),
                "pct": p,
                "currency": str(d.get("currency") or ""),
                "followed": bool(followers),
                "followers": followers,
            }
        )

    out: List[Dict[str, Any]] = []
    for (canon, src, cond), items in grouped.items():
        items.sort(key=lambda x: _FIELD_ORDER.get(x["field"], 9))
        out.append(
            {
                "canonical": canon,
                "source": src,
                "source_label": SOURCE_LABELS.get(src, src),
                "condition": cond,
                "max_pct": max(abs(i["pct"]) for i in items),
                "items": items,
            }
        )
    out.sort(key=lambda x: (-x["max_pct"], x["canonical"]))
    return out


def _src_display(src: str, condition: Any) -> str:
    """「站点名 + 计费口径」，如：腾讯云国际·原厂·闲时 / 腾讯云国际·自建。"""
    site = SOURCE_LABELS.get(str(src), str(src))
    cond = _condition_label(condition)
    if not cond:
        return site
    return f"{site}·{cond}"


def _delta_cell(d: Dict[str, Any]) -> str:
    """单个字段变动单元格：`入 $10→$4 -60%`；刊例同调加「同调」标记。"""
    field = _FIELD_LABEL.get(d.get("field") or "", str(d.get("field")))
    cur = d.get("currency") or ""
    seg = f"{field} {_fmt_currency(d.get('old'), cur)}→{_fmt_currency(d.get('new'), cur)}"
    pct = _pct(d.get("old"), d.get("new"))
    if pct is not None and abs(pct) >= 1:
        arrow = "↑" if pct > 0 else "↓"
        seg += f" {arrow}{abs(pct):.0f}%"
    if d.get("tier_sync"):
        seg += "（刊例同调）"
    elif d.get("follows_official"):
        seg += "（跟进官网）"
    return seg


def _official_alert_lines(alerts: List[Dict[str, Any]]) -> List[str]:
    """官方调价预警 → 纯文本行（供 build_message 使用）。

    跟进状态按**字段**标注（同一模型可能输入价已同步、缓存写入价未同步），
    避免模型级笼统结论误导跟进判断：

        • GPT-5.6 Sol · OpenAI官网
          ├ 输入 $4→$5 ↑25%｜渠道同步：OpenRouter
          └ 缓存写入 $5→$6 ↑20%｜渠道同步：未见（比价口径需人工确认）
    """
    lines: List[str] = []
    for a in alerts:
        lines.append(f"• {a['canonical']} · {a['source_label']}")
        for idx, it in enumerate(a["items"]):
            arrow = "↑" if it["pct"] > 0 else "↓"
            branch = "└" if idx == len(a["items"]) - 1 else "├"
            follow = "、".join(it["followers"]) if it["followers"] else "未见（需人工确认）"
            lines.append(
                f"    {branch} {it['field_cn']} "
                f"{_fmt_currency(it['old'], it['currency'])}"
                f"→{_fmt_currency(it['new'], it['currency'])}"
                f" {arrow}{abs(it['pct']):.0f}%｜渠道同步：{follow}"
            )
    return lines


def _prepare_groups(deltas: List[Dict[str, Any]]) -> Dict[tuple, List[Dict[str, Any]]]:
    """归并分时档位后按 (模型, 来源, 口径) 分组。

    tier_sync 的代表行（如闲时档）来源显示会带上「刊例同调」语义；
    结构性调整的档位行打 tier_struct 标记供提醒规则使用；
    官网基准分析先行：official_lead / follows_official 标记随行携带。
    """
    deltas = _market_analysis(deltas)
    consolidated, structural = consolidate_tiers(deltas)
    struct_set = set(structural)
    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for d in consolidated:
        if d.get("canonical") in struct_set:
            d = dict(d)
            d["tier_struct"] = True
        groups.setdefault(_group_key(d), []).append(d)
    return groups


def _table_rows(groups: Dict[tuple, List[Dict[str, Any]]]) -> List[str]:
    """渲染等宽伪表格（飞书 text 无 markdown，用全角空格+竖线对齐）。

    列：模型｜来源｜变动
    """
    rows: List[str] = []
    for key in sorted(
        groups.keys(),
        key=lambda k: (
            -(max(abs(_pct(d.get("old"), d.get("new")) or 0) for d in groups[k])),
            k,
        ),
    ):
        canon, src, cond = key
        items = sorted(
            groups[key], key=lambda x: _FIELD_ORDER.get(x.get("field") or "", 9)
        )
        cells = "  ".join(_delta_cell(d) for d in items)
        disp = _src_display(str(src), cond)
        rows.append(f"{canon}｜{disp}｜{cells}")
    return rows


def _build_reminders(groups: Dict[tuple, List[Dict[str, Any]]]) -> List[str]:
    """基于规则的场景提醒（只陈述可从数据推出的事实，不臆测）。"""
    reminders: List[str] = []

    # 规则0a：官网调价而渠道未跟进 → 市场行情警报（官网是定价锚点）
    lead = sorted(
        {
            (k[0], k[1])
            for k, items in groups.items()
            if any(d.get("official_lead") for d in items)
        }
    )
    for canon, src in lead:
        site = SOURCE_LABELS.get(src, src)
        reminders.append(
            f"🚨 市场行情：{canon} 官网调价，渠道未跟进（{site} 报价或即将过期，注意比价）"
        )

    # 规则0：分时档位涨跌幅背离 / 单档变动 → 结构性调整
    struct = sorted({k[0] for k, items in groups.items() if any(d.get("tier_struct") for d in items)})
    if struct:
        reminders.append(
            "峰谷结构调整：" + "、".join(struct) + "（各时段价差变化，注意成本核算口径）"
        )

    # 规则1：同一模型同一来源出现同字段多条不同新价 → 峰谷双档
    peak: List[str] = []
    for key, items in groups.items():
        by_field: Dict[str, List[Any]] = {}
        for d in items:
            f = str(d.get("field"))
            by_field.setdefault(f, []).append(d.get("new"))
        for f, news in by_field.items():
            vals = {v for v in news if v is not None}
            if len(vals) > 1:
                peak.append(key[0])
                break
    if peak:
        reminders.append(
            "峰谷分时：" + "、".join(sorted(set(peak))) + "（注意调用时段）"
        )

    # 规则2：出现 ≥50% 的大幅调价 → 建议核实
    big = [
        k
        for k, items in groups.items()
        if any(abs(_pct(d.get("old"), d.get("new")) or 0) >= 50 for d in items)
    ]
    if big:
        names = "、".join(sorted({k[0] for k in big}))
        reminders.append(f"大幅调价（≥50%）：{names}，建议官网核实")

    # 规则3：全线降价 → 采购时机提示
    pcts = [
        _pct(d.get("old"), d.get("new"))
        for items in groups.values()
        for d in items
    ]
    valid = [p for p in pcts if p is not None]
    if len(valid) >= 3 and all(p < 0 for p in valid):
        reminders.append("全线降价，批量任务可考虑此窗口放量")

    return reminders


def build_message(
    deltas: List[Dict[str, Any]], snapshot_date: str, keyword: Optional[str] = None
) -> str:
    """构建精简表格化播报消息（纯文本，兼容飞书 msg_type=text）。

    版式：
      标题行 → 概览一行 → 变动表格（等宽对齐，按幅度降序）→ 提醒（单行短语）
      → 站点链接 + 关键词后缀（规避飞书 19024）
    """
    kw = keyword if keyword else os.environ.get("PRICE_KEYWORD", "官网价格")

    groups = _prepare_groups(deltas)
    consolidated: List[Dict[str, Any]] = [d for items in groups.values() for d in items]

    ups = sum(1 for d in consolidated if (_pct(d.get("old"), d.get("new")) or 0) > 0)
    downs = sum(1 for d in consolidated if (_pct(d.get("old"), d.get("new")) or 0) < 0)

    # 官方调价预警置顶：官方价是定价锚点，所有调整都必须人工跟进确认
    alerts = _official_price_alerts(deltas)

    lines = [
        f"📊 Token 定价日报 {snapshot_date}",
        f"变动 {len(groups)} 模型 / {len(consolidated)} 处｜涨 {ups} · 跌 {downs}",
        "",
    ]
    if alerts:
        lines.append(f"🏛️ 官方调价（{len(alerts)} 个模型，需跟进）")
        lines.extend(_official_alert_lines(alerts))
        lines.append("")
    lines.append("模型｜来源｜变动")
    lines.extend(_table_rows(groups))

    reminders = _build_reminders(groups)
    if reminders:
        lines.append("")
        lines.extend(f"💡 {r}" for r in reminders)

    lines.append("")
    lines.append(f"详情：{SITE_URL}")
    lines.append(f"[关键词：{kw}]")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 飞书消息卡片（msg_type=interactive）
#
# 合法类型之一；官方规则：自定义关键词对卡片内的文本值同样生效
# （title.content / markdown / plain_text 均会被扫描）。
# 因此卡片文案中必须出现 PRICE_KEYWORD 对应的关键词，否则仍会 19024。
# ---------------------------------------------------------------------------

_CARD_COL_WEIGHTS = (32, 28, 40)  # 模型 / 来源 / 变动 三栏宽度


def _md_cell(text: str, align: str = "left") -> Dict[str, Any]:
    return {"tag": "markdown", "content": text}


def _card_row(
    cells: List[Any],
    bg: str = "default",
    weights: Tuple[int, int, int] = _CARD_COL_WEIGHTS,
    center: bool = False,
) -> Dict[str, Any]:
    """一行多栏 column_set。cells 元素为 str（自动包 md）或已构造的 element dict。"""
    cols = []
    for i, item in enumerate(cells):
        els = [item] if isinstance(item, dict) else [_md_cell(str(item))]
        col: Dict[str, Any] = {
            "tag": "column",
            "width": "weighted",
            "weight": weights[i] if i < len(weights) else weights[-1],
            "vertical_align": "center",
            "elements": els,
        }
        if bg != "default":
            col["background_style"] = bg
        if center:
            col["horizontal_align"] = "center"
        cols.append(col)
    return {"tag": "column_set", "flex_mode": "stretch", "columns": cols}


def _stat_card(num: str, label: str, accent: str = "") -> Dict[str, Any]:
    """KPI 统计块的单元格内容：大号数字 + 小标签，居中。"""
    num_txt = f"**{accent}{num}**"
    return {
        "tag": "column",
        "width": "weighted",
        "weight": 1,
        "vertical_align": "center",
        "horizontal_align": "center",
        "background_style": "grey",
        "elements": [_md_cell(f"{num_txt}<br>{label}")],
    }


def build_card(
    deltas: List[Dict[str, Any]], snapshot_date: str, keyword: Optional[str] = None
) -> Dict[str, Any]:
    """构建飞书 interactive 卡片 payload。

    视觉设计（对齐飞书官方卡片设计规范）：
      1. 彩色头部：涨多红 / 跌多绿，标题含日期
      2. KPI 统计行：4 个灰底数据卡（模型数 / 条目数 / 涨 / 跌），居中大字
      3. 官方调价预警区（置顶）：🏛️ 每个官方源调价明细 + 渠道跟进状态
      4. 斑马纹三栏表格：表头灰底加粗，数据行灰白交替，按幅度降序
      5. 提醒区：💡 前缀单行短语
      6. 主按钮直达站点 + 灰色脚注（含关键词，规避 19024）
    """
    kw = keyword if keyword else os.environ.get("PRICE_KEYWORD", "官网价格")

    groups = _prepare_groups(deltas)
    consolidated: List[Dict[str, Any]] = [d for items in groups.values() for d in items]
    # 官方调价预警置顶：官方价是定价锚点，所有调整都必须人工跟进确认
    alerts = _official_price_alerts(deltas)

    ups = sum(1 for d in consolidated if (_pct(d.get("old"), d.get("new")) or 0) > 0)
    downs = sum(1 for d in consolidated if (_pct(d.get("old"), d.get("new")) or 0) < 0)

    def score(key: tuple) -> float:
        return max((abs(_pct(d.get("old"), d.get("new")) or 0) for d in groups[key]), default=0)

    ordered = sorted(groups.keys(), key=lambda k: (-score(k), k))

    # 中文市场惯例：涨红跌绿
    header_color = "red" if ups >= downs else "green"

    elements: List[Dict[str, Any]] = [
        # -- KPI 统计行 --
        {
            "tag": "column_set",
            "flex_mode": "stretch",
            "columns": [
                _stat_card(str(len(groups)), "变动模型"),
                _stat_card(str(len(consolidated)), "变动条目"),
                _stat_card(str(ups), "上涨", "🔺"),
                _stat_card(str(downs), "下跌", "🔻"),
            ],
        },
    ]

    # -- 官方调价预警区（置顶，KPI 之后、总表之前）--
    if alerts:
        elements.append({"tag": "hr"})
        alert_md = [f"**🏛️ 官方调价（{len(alerts)} 个模型，需跟进）**"]
        # 模型名顶格，明细行统一全角缩进（飞书 markdown 会吃掉 ASCII 前导空格）
        alert_md.extend(
            ln if ln.startswith("•") else f"　　{ln.lstrip()}"
            for ln in _official_alert_lines(alerts)
        )
        elements.append(
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "\n".join(alert_md)},
            }
        )

    # -- 表头 --
    elements.append({"tag": "hr"})
    elements.append(_card_row(["**模型**", "**来源**", "**变动（入 / 出）**"], bg="grey"))

    # -- 斑马纹数据行 --
    for idx, key in enumerate(ordered):
        canon, src, cond = key
        items = sorted(groups[key], key=lambda x: _FIELD_ORDER.get(x.get("field") or "", 9))
        cells_txt = "\n".join(_delta_cell(d) for d in items)
        disp = _src_display(str(src), cond)
        bg = "grey" if idx % 2 == 0 else "default"
        elements.append(_card_row([f"**{canon}**", disp, cells_txt], bg=bg))

    reminders = _build_reminders(groups)
    if reminders:
        elements.append({"tag": "hr"})
        elements.append(
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "\n".join(f"💡 {r}" for r in reminders)},
            }
        )

    elements.append({"tag": "hr"})
    elements.append(
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "📊 查看完整对比与趋势图"},
                    "type": "primary",
                    "url": SITE_URL,
                }
            ],
        }
    )
    elements.append(
        {
            "tag": "note",
            "elements": [
                {
                    "tag": "plain_text",
                    "content": (
                        f"{snapshot_date} · 数据仅供参考，以厂商官网价格为准 · [关键词：{kw}]"
                    ),
                }
            ],
        }
    )

    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": header_color,
                "title": {
                    "tag": "plain_text",
                    "content": f"📊 Token 定价日报 · {snapshot_date}",
                },
            },
            "elements": elements,
        },
    }


def _webhook_config() -> Optional[Tuple[str, str]]:
    """返回 (url, type)；type ∈ {feishu, wecom}。未配置返回 None。"""
    feishu = os.environ.get("FEISHU_WEBHOOK_URL")
    if feishu:
        return feishu, "feishu"
    wecom = os.environ.get("WECOM_WEBHOOK_URL")
    if wecom:
        return wecom, "wecom"
    generic = os.environ.get("PRICE_WEBHOOK_URL")
    if generic:
        wh_type = os.environ.get("PRICE_WEBHOOK_TYPE", "feishu")
        return generic, wh_type
    return None


def _payload(msg: str, wh_type: str) -> Dict[str, Any]:
    if wh_type == "wecom":
        return {"msgtype": "markdown", "markdown": {"content": msg}}
    # 飞书必须用合法 msg_type（text/post/image/share_chat/interactive）。
    # 关键坑：非标准 msg_type="markdown" 时，飞书的自定义关键词校验不扫描
    # content.text（官方文档：关键词只对 text/title 类文本参数值生效），
    # 会导致消息必带关键词仍返回 code:19024 Key Words Not Found。
    return {"msg_type": "text", "content": {"text": msg}}


def _post(url: str, data: bytes) -> Tuple[bool, str]:
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", "ignore")
        return True, body
    except Exception as exc:  # 网络/格式异常不应中断抓取主流程
        logger.warning("webhook 推送失败：%s", exc)
        return False, str(exc)


def _send_feishu(msg: str, url: str) -> bool:
    """飞书发送纯文本（msg_type=text）。"""
    ok, body = _post(url, json.dumps(_payload(msg, "feishu")).encode("utf-8"))
    if ok and '"code":0' in body.replace(" ", ""):
        logger.info("webhook 推送成功（feishu）：%s", body[:120])
        return True
    if '"code":19024' in body.replace(" ", ""):
        logger.warning(
            "飞书 webhook 被拒（code:19024 = 自定义关键词未命中）。"
            "请将机器人【安全设置-自定义关键词】设为消息中包含的词（如「官网价格」），"
            "或通过 PRICE_KEYWORD 环境变量配置。"
        )
    return False


def _send_feishu_card(card: Dict[str, Any], fallback_msg: str, url: str) -> bool:
    """飞书发送：优先 interactive 卡片，失败自动降级为纯文本兜底。"""
    ok, body = _post(url, json.dumps(card, ensure_ascii=False).encode("utf-8"))
    if ok and '"code":0' in body.replace(" ", ""):
        logger.info("webhook 推送成功（feishu card）：%s", body[:120])
        return True
    logger.warning("feishu 卡片推送未成功（%s），降级为纯文本", body[:120])
    return _send_feishu(fallback_msg, url)


def send_webhook(msg: str, url: str, wh_type: str) -> bool:
    """POST 消息到 webhook，返回是否成功。"""
    if wh_type == "feishu":
        return _send_feishu(msg, url)
    ok, body = _post(url, json.dumps(_payload(msg, wh_type)).encode("utf-8"))
    if ok:
        logger.info("webhook 推送成功（%s）：%s", wh_type, body[:120])
    return ok


def _channel_follow_message(
    results: List[Dict[str, Any]], snapshot_date: str
) -> str:
    """渠道跟进监督结果 → 纯文本消息。按状态分组，便于快速定位未跟进渠道。"""
    lines: List[str] = [f"【报价监督 · 渠道跟进】{snapshot_date}"]
    _MARK = {"已跟进": "✅", "幅度背离": "⚠️", "未跟进": "❌"}
    _ORDER = ["已跟进", "幅度背离", "未跟进"]
    for r in results:
        canon = str(r.get("canonical") or "")
        field_cn = str(r.get("field_cn") or r.get("field") or "")
        cur = str(r.get("currency") or "")
        old_v, new_v = r.get("official_old"), r.get("official_new")
        pct = r.get("official_pct")
        arrow = ""
        if pct is not None:
            arrow = "↑" if pct > 0 else "↓"
        seg = f"• {canon} · {field_cn} {old_v}→{new_v}{arrow}{abs(pct or 0):.0f}%"
        lines.append(seg)
        by_status: Dict[str, List[str]] = {}
        for c in r.get("channels") or []:
            by_status.setdefault(str(c.get("status") or "未跟进"), []).append(
                str(c.get("source") or "")
            )
        for status in _ORDER:
            srcs = by_status.get(status)
            if not srcs:
                continue
            names = "、".join(SOURCE_LABELS.get(s, s) for s in srcs)
            lines.append(f"  {_MARK[status]} {status}：{names}")
    return "\n".join(lines)


def notify_channel_follow(
    results: List[Dict[str, Any]], snapshot_date: str
) -> bool:
    """渠道跟进监督结果飞书推送入口。

    无结果或未配置 webhook 时静默返回 False，不阻断主流程。
    """
    if not results:
        return False
    cfg = _webhook_config()
    if not cfg:
        logger.info("未配置 webhook（FEISHU_WEBHOOK_URL/WECOM_WEBHOOK_URL），跳过渠道跟进监督推送")
        return False
    url, wh_type = cfg
    msg = _channel_follow_message(results, snapshot_date)
    return send_webhook(msg, url, wh_type)


def notify_price_changes(deltas: List[Dict[str, Any]], snapshot_date: str) -> bool:
    """入口：有变动且配置了 webhook 时推送；否则静默返回 False。

    Args:
        deltas: store.compare_previous 返回的变动项列表
        snapshot_date: 快照日期（YYYY-MM-DD）
    Returns:
        是否实际发送了推送。
    """
    if not deltas:
        return False
    cfg = _webhook_config()
    if not cfg:
        logger.info("未配置 webhook（FEISHU_WEBHOOK_URL/WECOM_WEBHOOK_URL），跳过价格变动推送")
        return False
    url, wh_type = cfg
    msg = build_message(deltas, snapshot_date)
    if wh_type == "feishu":
        card = build_card(deltas, snapshot_date)
        return _send_feishu_card(card, msg, url)
    return send_webhook(msg, url, wh_type)
