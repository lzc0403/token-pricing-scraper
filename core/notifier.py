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


def _fmt_currency(v: Any, cur: str) -> str:
    if v is None:
        return "—"
    return f"{v}{cur}" if cur else str(v)


def _fmt_delta(d: Dict[str, Any]) -> str:
    canon = d.get("canonical") or "?"
    src = d.get("source") or "?"
    field = "输入" if d.get("field") == "input" else "输出"
    cur = d.get("currency") or ""
    old_s = _fmt_currency(d.get("old"), cur)
    new_s = _fmt_currency(d.get("new"), cur)
    return f"- {canon} [{src}] {field}：{old_s} → {new_s}"


def build_message(deltas: List[Dict[str, Any]], snapshot_date: str) -> str:
    """构建纯文本播报消息。"""
    lines = [
        f"📊 Token 定价变动播报（{snapshot_date}）",
        f"共 **{len(deltas)}** 处价格变动：",
        "",
    ]
    lines.extend(_fmt_delta(d) for d in deltas)
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
    # 飞书 markdown
    return {"msg_type": "markdown", "content": {"text": msg}}


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
