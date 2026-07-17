"""报告生成：REPORT.md（跨源对照 + 周环比 + 抓取状态）与 issue_body.md（变动明细）。"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def _fmt(v: Any, currency: str = "") -> str:
    if v is None:
        return "-"
    if isinstance(v, str):
        # 上下文等字符串字段直接原样返回（可附带货币说明）
        return f"{v} {currency}".strip() if currency else v
    if currency:
        return f"{v:g} {currency}"
    return f"{v:g}"


def _build_watchlist_table(watchlist: List[Dict[str, Any]]) -> str:
    rows = ["| 模型 | 源 | 输入¥ | 输出¥ | 缓存命中 | 货币 | 原始价(输入/输出) | 上下文 |",
            "| --- | --- | ---: | ---: | ---: | --- | --- | --- |"]
    if not watchlist:
        rows.append("| _无命中记录_ | - | - | - | - | - | - | - |")
        return "\n".join(rows)
    for r in sorted(watchlist, key=lambda x: (x.get("canonical", ""), x.get("source", ""))):
        cur = r.get("currency", "")
        raw = f"{_fmt(r.get('input'), cur)} / {_fmt(r.get('output'), cur)}"
        rows.append(
            "| {canonical} | {source} | {in_rmb} | {out_rmb} | {cache} | {cur} | {raw} | {ctx} |".format(
                canonical=r.get("canonical", ""),
                source=r.get("source", ""),
                in_rmb=_fmt(r.get("input_rmb"), "¥"),
                out_rmb=_fmt(r.get("output_rmb"), "¥"),
                cache=_fmt(r.get("cache_hit"), cur),
                cur=cur,
                raw=raw,
                ctx=_fmt(r.get("context") or None) if r.get("context") else "-",
            )
        )
    return "\n".join(rows)


def _build_delta_table(deltas: List[Dict[str, Any]]) -> str:
    if not deltas:
        return "本周无变动。"
    rows = ["| 模型 | 源 | 字段 | 旧值 | 新值 | 货币 |",
            "| --- | --- | --- | ---: | ---: | --- |"]
    for d in deltas:
        field_cn = "输入" if d["field"] == "input" else "输出"
        rows.append(
            "| {canonical} | {source} | {field} | {old} | {new} | {cur} |".format(
                canonical=d.get("canonical", ""),
                source=d.get("source", ""),
                field=field_cn,
                old=_fmt(d.get("old")),
                new=_fmt(d.get("new")),
                cur=d.get("currency", ""),
            )
        )
    return "\n".join(rows)


def _build_status_section(scrape_status: Dict[str, Dict[str, Any]]) -> str:
    rows = ["| 源 | 状态 | 记录数 | 说明 |",
            "| --- | --- | ---: | --- |"]
    for sid, st in scrape_status.items():
        ok = st.get("ok", False)
        status = "成功" if ok else "失败"
        note = st.get("error") or ("抓取 %d 条" % st.get("count", 0))
        rows.append("| {sid} | {status} | {count} | {note} |".format(
            sid=sid, status=status, count=st.get("count", 0), note=note or "-"))
    return "\n".join(rows)


def build_report(
    watchlist: List[Dict[str, Any]],
    deltas: List[Dict[str, Any]],
    scrape_status: Dict[str, Dict[str, Any]],
    generated_at: Optional[str] = None,
) -> Tuple[str, str]:
    """构造 (REPORT.md, issue_body.md)。

    Args:
        watchlist: 命中的目标模型记录（含 rmb 字段）。
        deltas: 价格变动项（来自 store.compare_previous）。
        scrape_status: 各源抓取状态 {source: {ok, count, error}}。
        generated_at: 可选的时间戳字符串。
    """
    if generated_at is None:
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = []
    report.append("# 大模型 Token 定价周报\n")
    report.append(f"> 生成时间：{generated_at}\n")
    report.append("## 一、目标模型跨源对照（已换算人民币）\n")
    report.append(_build_watchlist_table(watchlist))
    report.append("\n## 二、周环比变动\n")
    report.append(_build_delta_table(deltas))
    report.append("\n## 三、抓取状态\n")
    report.append(_build_status_section(scrape_status))
    report_md = "\n".join(report)

    # issue body：仅变动明细
    if deltas:
        issue = []
        issue.append("## 🔔 Token 定价变动（%s）\n" % generated_at)
        issue.append(_build_delta_table(deltas))
        issue_body_md = "\n".join(issue)
    else:
        issue_body_md = "本周无 Token 定价变动。"

    return report_md, issue_body_md


def write_outputs(out_dir: str, report_md: str, issue_body_md: str) -> Dict[str, str]:
    """将 REPORT.md 与 issue_body.md 写入 out_dir。"""
    os.makedirs(out_dir, exist_ok=True)
    report_path = os.path.join(out_dir, "REPORT.md")
    issue_path = os.path.join(out_dir, "issue_body.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    with open(issue_path, "w", encoding="utf-8") as f:
        f.write(issue_body_md)
    return {"REPORT.md": report_path, "issue_body.md": issue_path}
