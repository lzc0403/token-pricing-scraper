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

_FIELD_LABEL = {"input": "入", "output": "出", "cache": "缓存"}
_CUR_SYMBOL = {"USD": "$", "CNY": "¥", "USDT": "$"}
_FIELD_ORDER = {"input": 0, "output": 1, "cache": 2}

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
    "openrouter": "OpenRouter",
    "atlascloud": "AtlasCloud",
    "modelmesh": "胜算云",
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


def _src_display(src: str, condition: Any) -> str:
    """「站点名 + 计费口径」，如：腾讯云国际·原厂·闲时 / 腾讯云国际·自建。"""
    site = SOURCE_LABELS.get(str(src), str(src))
    cond = _condition_label(condition)
    if not cond:
        return site
    return f"{site}·{cond}"


def _delta_cell(d: Dict[str, Any]) -> str:
    """单个字段变动单元格：`入 $10→$4 -60%`。"""
    field = _FIELD_LABEL.get(d.get("field") or "", str(d.get("field")))
    cur = d.get("currency") or ""
    seg = f"{field} {_fmt_currency(d.get('old'), cur)}→{_fmt_currency(d.get('new'), cur)}"
    pct = _pct(d.get("old"), d.get("new"))
    if pct is not None and abs(pct) >= 1:
        arrow = "↑" if pct > 0 else "↓"
        seg += f" {arrow}{abs(pct):.0f}%"
    return seg


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

    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for d in deltas:
        groups.setdefault(_group_key(d), []).append(d)

    ups = sum(1 for d in deltas if (_pct(d.get("old"), d.get("new")) or 0) > 0)
    downs = sum(1 for d in deltas if (_pct(d.get("old"), d.get("new")) or 0) < 0)

    lines = [
        f"📊 Token 定价日报 {snapshot_date}",
        f"变动 {len(groups)} 模型 / {len(deltas)} 处｜涨 {ups} · 跌 {downs}",
        "",
        "模型｜来源｜变动",
    ]
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
      3. 斑马纹三栏表格：表头灰底加粗，数据行灰白交替，按幅度降序
      4. 提醒区：💡 前缀单行短语
      5. 主按钮直达站点 + 灰色脚注（含关键词，规避 19024）
    """
    kw = keyword if keyword else os.environ.get("PRICE_KEYWORD", "官网价格")

    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for d in deltas:
        groups.setdefault(_group_key(d), []).append(d)

    ups = sum(1 for d in deltas if (_pct(d.get("old"), d.get("new")) or 0) > 0)
    downs = sum(1 for d in deltas if (_pct(d.get("old"), d.get("new")) or 0) < 0)

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
                _stat_card(str(len(deltas)), "变动条目"),
                _stat_card(str(ups), "上涨", "🔺"),
                _stat_card(str(downs), "下跌", "🔻"),
            ],
        },
        {"tag": "hr"},
        # -- 表头 --
        _card_row(["**模型**", "**来源**", "**变动（入 / 出）**"], bg="grey"),
    ]

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
