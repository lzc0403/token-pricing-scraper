"""site 模板渲染层：HTML 小部件与页面组装。

由 site.py 拆出，职责单一：把 site_data 构建好的数据结构渲染为 HTML。
依赖 site_data 提供：SOURCE_LABELS/_is_official_* 等判定函数与常量。
"""
from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from jinja2 import Environment, FileSystemLoader, select_autoescape
from core import site_data as _sd
from core.site_data import (
    MAINSTREAM_SORT_ORDER,
    PEAK_SCHEDULES,
    SOURCE_LABELS,
    _CHANNEL_PEAK_SCHED,
    _build_site_data,
    _clean_ctx_label,
    _esc,
    _esc_attr,
    _fmt_num,
    _vendor_rank,
    clean_model_name,
    source_label,
)

# 前端资源（独立文件管理，build 时内联保持单 HTML 部署）
_SITE_DIR = os.path.dirname(os.path.abspath(__file__))
_ASSETS_ROOT = os.path.join(os.path.dirname(_SITE_DIR), "site", "assets")
_TEMPLATES_DIR = os.path.join(os.path.dirname(_SITE_DIR), "site", "templates")


def _load_asset(name: str) -> str:
    """读取 site/assets/ 下的前端资源文件。"""
    path = os.path.join(_ASSETS_ROOT, name)
    with open(path, encoding="utf-8") as f:
        return f.read()

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
    # 缓存命中价：峰谷计费行渲染「闲 X / 高 Y」双档（DeepSeek 官网缓存同样分忙闲时），
    # 非峰谷行保持单值。双档均取原币种（缓存列与 input/output 展示口径一致）。
    if r.get("peak_cache_low") is not None or r.get("peak_cache_high") is not None:
        cache = _peak_duo(r.get("peak_cache_low"), r.get("peak_cache_high"))
    else:
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
        # Gemini 缓存存储价（$/1M tokens/小时，取首档促销期值）：官方「缓存创建」
        # 类成本按小时计费，与按 token 的缓存命中分属不同维度，追加展示。
        store_val = ""
        if tiers and isinstance(tiers[0], dict):
            _sv = tiers[0].get("cache_storage_price")
            if isinstance(_sv, (int, float)):
                store_val = _fmt_num(_sv)
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
            if store_val:
                price_html += (
                    f'{sep}'
                    f'<span class="ms-pair"><span class="ms-plabel">缓存存储<span class="ms-unit">/时</span></span>'
                    f'<span class="ms-pval">{store_val}</span></span>'
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
        new_badge = '<span class="ms-new" title="新上架 / 新收录，自动置顶">🆕 新品</span>' if model.get("is_new") else ""
        availability = model.get("availability")
        is_pending = availability not in ("official", "preview")
        tracking_badge = '<span class="ms-tracking" title="官网定价尚未抓取，以下为渠道参考价">待补</span>' if is_pending else ""
        new_badge = new_badge if not is_pending else ""  # 待补模型不标新品（无官方价）

        all_cards.append(
            f'<article class="model-pick" data-canonical="{_esc_attr(canon)}" '
            f'data-context="{_esc_attr(ctx_tokens)}" data-source="{_esc_attr(vid)}" '
            f'data-region="{_esc_attr(region)}" '
            f'data-i="{idx}" style="--i:{idx}" '
            f'tabindex="0" role="button" aria-label="筛选 {_esc(display)}">'
            f'<span class="ms-vendor-stripe" data-vendor="{_esc_attr(vid)}" aria-hidden="true"></span>'
            f'<div class="ms-model-head">'
            f'<span class="ms-model-name">{_esc(display)}{hot_badge}{new_badge}{tracking_badge}</span>'
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


def _trend_section(history: Dict[str, Any], canons: List[str]) -> str:
    """历史价格趋势图区块：按模型×渠道展示输入/输出价随时间变化。"""
    dates = history.get("dates") or []
    series = history.get("series") or {}
    if len(dates) < 2:
        # 不足 2 个数据点：展示占位说明，引导用户等待数据累积
        return f"""
    <section class="block-card trend-card" aria-labelledby="trend-title">
      <div class="chart-head">
        <div>
          <h2 id="trend-title" class="block-title" style="margin:0">历史价格趋势</h2>
          <p class="block-desc" style="margin:4px 0 0">每日自动抓取累积 · 折线图展示各渠道报价随时间变化</p>
        </div>
      </div>
      <div class="trend-empty">
        <p>📈 历史趋势图需要至少 2 天的数据点。当前已累积 <b>{len(dates)}</b> 天快照。</p>
        <p class="trend-hint">每日抓取自动化已启用（每日 09:00 北京时间），数据将自动累积。预计 2-3 天后即可看到趋势线。</p>
      </div>
    </section>"""

    # 可选项：有快照的模型（按当前 canons 顺序优先）
    avail = [c for c in canons if c in series]
    if not avail:
        avail = list(series.keys())
    options = "".join(f'<option value="{_esc(c)}">{_esc(c)}</option>' for c in avail)
    return f"""
    <section class="block-card trend-card" aria-labelledby="trend-title">
      <div class="chart-head">
        <div>
          <h2 id="trend-title" class="block-title" style="margin:0">历史价格趋势</h2>
          <p class="block-desc" style="margin:4px 0 0">每日自动抓取累积 · {len(dates)} 天数据 · 折线图展示各渠道报价随时间变化</p>
        </div>
        <div class="chart-controls">
          <div class="seg" role="group" aria-label="价格维度">
            <button type="button" class="seg-btn is-active" data-trend-metric="input" aria-pressed="true">输入价</button>
            <button type="button" class="seg-btn" data-trend-metric="output" aria-pressed="false">输出价</button>
          </div>
          <select id="trendModelSelect" aria-label="选择模型">{options}</select>
        </div>
      </div>
      <div class="chart-wrap">
        <canvas id="trendChart" role="img" aria-label="历史价格趋势折线图"></canvas>
        <p id="trendLive" class="visually-hidden" aria-live="polite"></p>
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


def _price_alert_bar(changes: List[Dict[str, Any]], generated_at: Any) -> str:
    """官方调价提醒横幅（页面顶部）。有近期官方价调整才渲染；可手动关闭。"""
    if not changes:
        return ""
    items = []
    for ch in changes[:5]:
        canon = _esc(ch.get("canonical") or "")
        label = _esc(ch.get("source_label") or ch.get("source") or "")
        fld = _esc(ch.get("field_cn") or ch.get("field") or "")
        old_v = ch.get("old")
        new_v = ch.get("new")
        pct = ch.get("pct")
        pct_txt = ""
        if pct is not None:
            try:
                fp = float(pct)
                arrow = "↑" if fp > 0 else "↓"
                pct_txt = f" {arrow}{abs(fp):.0f}%"
            except (TypeError, ValueError):
                pass
        cur = _esc(ch.get("currency") or "")
        items.append(
            f'<span class="alert-item">{_esc(canon)} · {label} · {fld} '
            f'{old_v}→{new_v} {cur}{pct_txt}</span>'
        )
    date_txt = f"（{generated_at} 检测）" if generated_at else ""
    return (
        '<div class="price-alert" id="priceAlert" role="alert">'
        '<span class="alert-title">🚨 官方调价提醒</span>'
        + "".join(items)
        + f'<button type="button" class="alert-close" id="priceAlertClose" aria-label="关闭">×</button>'
        f'<div class="alert-foot">{date_txt} 以厂商官网最新报价为准，已同步更新本页</div>'
        '</div>'
    )


def _detail_panel_section() -> str:
    """模型详情面板（MODEL DETAIL）。

    默认空态提示；点击卡片后由前端 JS 从 SITE_DATA.model_details 取该模型
    4 维分档报价渲染（输入/输出/缓存创建/缓存读取，含多档与缓存存储）。
    """
    return """
    <section class="block-card block-detail" aria-labelledby="detail-title">
      <div class="block-head">
        <div>
          <div class="block-kicker">MODEL DETAIL</div>
          <h2 id="detail-title" class="block-title">模型详情 · 4 维分档报价</h2>
          <p class="block-desc">点击上方任一模型卡片，查看该模型的 输入 / 输出 / 缓存创建 / 缓存读取 分档报价与上下文、币种。官方价是定价锚点，渠道价仅作对照。</p>
        </div>
      </div>
      <div id="detailBody" class="detail-body">
        <div class="detail-empty" id="detailEmpty">👈 请选择上方一张模型卡片，查看它的完整 4 维分档报价</div>
      </div>
    </section>"""


def build_site(data_dir: str, out_path: Optional[str] = None) -> str:
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
    oc = data.get("official_changes") or {}
    detail_panel = _detail_panel_section()
    alert_bar = _price_alert_bar(oc.get("changes") or [], oc.get("generated_at"))
    official_block = _official_section(data.get("official_rows") or [], bool(data.get("has_official")))
    overseas_block = _overseas_section(data.get("overseas_rows") or [], bool(data.get("has_overseas")))
    channel_block = _channel_section(data)
    # 图表可选项只列「有对比数据」的模型（chart 的 key，已过滤掉仅 1 条数据的孤行），
    # 不能传全量 canons——否则下拉里会出现选中后图表空白的型号（如海外大模型、
    # 只有一家渠道的型号）。chart key 顺序即 canons 顺序，保持厂内旗舰优先。
    chart_canons = list((data.get("chart") or {}).keys())
    chart_block = _chart_section(chart_canons, bool(data.get("chart")))
    trend_block = _trend_section(data.get("history") or {}, canons)

    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    peak_json = json.dumps(
        {"schedules": PEAK_SCHEDULES, "channelSched": _CHANNEL_PEAK_SCHED},
        ensure_ascii=False,
    ).replace("</", "<\\/")
    js = _load_asset("app.js").replace("__SITE_DATA__", data_json).replace("__PEAK_DATA__", peak_json)
    css = _load_asset("style.css")

    # 页面骨架由 Jinja2 模板（site/templates/index.html.j2）驱动；
    # 各区块 HTML 仍由本模块的已测函数生成，经 | safe 注入，保证零回归。
    env = Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("index.html.j2")
    html = template.render(
        css=css,
        js=js,
        metrics_html=metrics_html,
        filter_block=filter_block,
        domestic_ms=domestic_ms,
        overseas_ms=overseas_ms,
        detail_panel=detail_panel,
        alert_bar=alert_bar,
        official_block=official_block,
        overseas_block=overseas_block,
        channel_block=channel_block,
        chart_block=chart_block,
        trend_block=trend_block,
        generated_at=data["generated_at"],
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return os.path.abspath(out_path)
