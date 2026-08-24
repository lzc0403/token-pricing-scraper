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

_FIELD_LABEL = {"input": "输入", "output": "输出", "cache": "缓存"}
_CUR_SYMBOL = {"USD": "$", "CNY": "¥", "USDT": "$"}

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
        "空闲时段 | 原厂直供": "原厂直供·闲时价",
        "高峰时段 | 原厂直供": "原厂直供·高峰价",
        "原厂直供": "原厂直供",
        "腾讯云自建": "腾讯云自建",
        "阿里云自部署": "阿里云自部署",
        "火山引擎自部署": "火山引擎自部署",
        "峰谷计费": "峰谷计费",
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
    """「站点名 + 计费口径」，如：腾讯云国际·原厂直供·闲时价 / 腾讯云国际·腾讯云自建。"""
    site = SOURCE_LABELS.get(str(src), str(src))
    cond = _condition_label(condition)
    if not cond:
        return site
    return f"{site}·{cond}"


def _render_group(key: tuple, items: List[Dict[str, Any]], major: bool) -> List[str]:
    """渲染单个模型的变动块。major=True 用多行块，False 折叠为单行。"""
    canon, src, _cond = key
    out: List[str] = []
    parts: List[str] = []
    for d in sorted(items, key=lambda x: x.get("field") or ""):
        field = _FIELD_LABEL.get(d.get("field") or "", str(d.get("field")))
        cur = d.get("currency") or ""
        old_s = _fmt_currency(d.get("old"), cur)
        new_s = _fmt_currency(d.get("new"), cur)
        seg = f"{field} {old_s}→{new_s}"
        pct = _pct(d.get("old"), d.get("new"))
        if pct is not None and abs(pct) >= 1:
            seg += f" {_fmt_pct(pct)}"
        parts.append(seg)
    disp = _src_display(str(src), key[2])
    if major:
        out.append(f"■ {canon}｜{disp}")
        out.extend(f"   {p}" for p in parts)
    else:
        out.append(f"· {canon}｜{disp}：{'；'.join(parts)}")
    return out


def _build_reminders(groups: Dict[tuple, List[Dict[str, Any]]]) -> List[str]:
    """基于规则的场景提醒（只陈述可从数据推出的事实，不臆测）。"""
    reminders: List[str] = []

    # 规则1：同一模型同一来源出现同字段多条不同新价 → 峰谷双档
    for key, items in groups.items():
        by_field: Dict[str, List[Any]] = {}
        for d in items:
            f = str(d.get("field"))
            by_field.setdefault(f, []).append(d.get("new"))
        for f, news in by_field.items():
            vals = {v for v in news if v is not None}
            if len(vals) > 1:
                label = _FIELD_LABEL.get(f, f)
                reminders.append(
                    f"{key[0]}（{_src_display(str(key[1]), key[2])}）{label}存在多个价位，"
                    "疑似峰谷分时计费，注意调用时段"
                )
                break

    # 规则2：出现 ≥50% 的大幅调价 → 建议核实
    big = [
        k
        for k, items in groups.items()
        if any(abs(_pct(d.get("old"), d.get("new")) or 0) >= 50 for d in items)
    ]
    if big:
        names = "、".join(sorted({k[0] for k in big}))
        reminders.append(
            f"{names} 出现 ≥50% 大幅调价，建议到厂商官网核实是否长期生效"
        )

    # 规则3：全线降价 → 采购时机提示
    pcts = [
        _pct(d.get("old"), d.get("new"))
        for items in groups.values()
        for d in items
    ]
    valid = [p for p in pcts if p is not None]
    if len(valid) >= 3 and all(p < 0 for p in valid):
        reminders.append("本期监测源全线降价，成本敏感的批量任务可考虑此窗口放量")

    return reminders


def build_message(
    deltas: List[Dict[str, Any]], snapshot_date: str, keyword: Optional[str] = None
) -> str:
    """构建结构化播报消息（纯文本，兼容飞书 msg_type=text）。

    版式：
      1. 标题行（日期）
      2. 今日概览：模型数 / 条目数 / 涨跌统计 / 最大变动
      3. 重点变动：|涨跌幅| ≥ MAJOR_PCT% 的模型，逐字段多行展示
      4. 其他变动：小幅变动折叠为单行
      5. 场景提醒：峰谷双档识别 / 大幅调价核实 / 采购窗口等规则化提示
      6. 站点链接 + 免责声明 + 关键词后缀（规避飞书 19024）
    """
    kw = keyword if keyword else os.environ.get("PRICE_KEYWORD", "官网价格")

    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for d in deltas:
        groups.setdefault(_group_key(d), []).append(d)

    def score(key: tuple) -> float:
        return max(
            (abs(_pct(d.get("old"), d.get("new")) or 0) for d in groups[key]),
            default=0,
        )

    ordered = sorted(groups.keys(), key=lambda k: (-score(k), k))

    # ---- 概览 ----
    ups = sum(
        1 for d in deltas if (_pct(d.get("old"), d.get("new")) or 0) > 0
    )
    downs = sum(
        1 for d in deltas if (_pct(d.get("old"), d.get("new")) or 0) < 0
    )
    top_key = ordered[0] if ordered else None
    top_line = ""
    if top_key:
        td = max(groups[top_key], key=lambda x: abs(_pct(x.get("old"), x.get("new")) or 0))
        tp = _pct(td.get("old"), td.get("new"))
        field = _FIELD_LABEL.get(td.get("field") or "", str(td.get("field")))
        top_line = (
            f"· 最大变动：{top_key[0]}（{_src_display(str(top_key[1]), top_key[2])}）{field} "
            f"{_fmt_currency(td.get('old'), td.get('currency') or '')}"
            f"→{_fmt_currency(td.get('new'), td.get('currency') or '')} {_fmt_pct(tp)}"
        )

    lines = [
        f"📊 Token 定价日报（{snapshot_date}）",
        "",
        "【今日概览】",
        f"· 变动模型 {len(groups)} 个 / 变动条目 {len(deltas)} 处"
        f"（涨价 {ups} · 降价 {downs}）",
    ]
    if top_line:
        lines.append(top_line)
    lines.append("")

    # ---- 重点 / 其他变动 ----
    major_groups = [k for k in ordered if score(k) >= MAJOR_PCT]
    minor_groups = [k for k in ordered if score(k) < MAJOR_PCT]

    if major_groups:
        lines.append(f"【🔥 重点变动】（幅度 ≥{MAJOR_PCT:.0f}%，{len(major_groups)} 个模型）")
        for k in major_groups:
            lines.extend(_render_group(k, groups[k], major=True))
        lines.append("")
    if minor_groups:
        lines.append(f"【其他变动】（{len(minor_groups)} 个模型）")
        for k in minor_groups:
            lines.extend(_render_group(k, groups[k], major=False))
        lines.append("")

    # ---- 场景提醒 ----
    reminders = _build_reminders(groups)
    if reminders:
        lines.append("【💡 行动提醒】")
        lines.extend(f"· {r}" for r in reminders)
        lines.append("")

    lines.append(f"完整对比与历史趋势：{SITE_URL}")
    lines.append("— 定价数据仅供参考，具体以厂商官网为准 —")
    lines.append(f"[关键词：{kw}]")
    return "\n".join(lines)


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
    # 飞书必须用 msg_type="text"（合法类型仅 text/post/image/share_chat/interactive）。
    # 关键坑：非标准 msg_type="markdown" 时，飞书的自定义关键词校验不扫描
    # content.text（官方文档：关键词只对 text/title 类文本参数值生效），
    # 会导致消息必带关键词仍返回 code:19024 Key Words Not Found。
    return {"msg_type": "text", "content": {"text": msg}}


def send_webhook(msg: str, url: str, wh_type: str) -> bool:
    """POST markdown 消息到 webhook，返回是否成功。"""
    data = json.dumps(_payload(msg, wh_type)).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", "ignore")
        logger.info("webhook 推送成功（%s）：%s", wh_type, body[:120])
        # 飞书 19024 = 自定义关键词未命中，需在机器人安全设置中补充关键词
        if wh_type == "feishu" and '"code":19024' in body.replace(" ", ""):
            logger.warning(
                "飞书 webhook 被拒（code:19024 = 自定义关键词未命中）。"
                "请将机器人【安全设置-自定义关键词】设为消息中包含的词（如「官网价格」/「Token」），"
                "或通过 PRICE_KEYWORD 环境变量在消息末尾追加关键词。"
            )
        return True
    except Exception as exc:  # 网络/格式异常不应中断抓取主流程
        logger.warning("webhook 推送失败（%s）：%s", wh_type, exc)
        return False


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
    return send_webhook(msg, url, wh_type)
