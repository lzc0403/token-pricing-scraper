"""生成美化静态网页：读取 data/ 中的定价数据，输出自包含 site/index.html。

设计目标：
  - 自包含：数据以 JSON 嵌入 <script>，双击 file:// 即可打开，无需服务器。
  - 配色严格套用 boc-scraper 模板（见 _BOC_CSS 中的 :root 变量）。
  - 结构：Hero(渐变 mesh + 4 metric) / 跨源比价表 / Chart.js 柱状图 / Footer。
  - 健壮性：watchlist.json 缺失或为空时仍生成页面（空态提示），
    site/index.html 一定被写出（保证 workflow `git add site/` 不缺文件）。

涨跌约定与 boc 一致：升=红(--red)，降=绿(--green)；本页用绿色高亮最低价。
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# 复用汇率换算模块（含空环境变量回退 7.2 的逻辑）
from core import currency  # noqa: F401  (确保 core 包已导入)


# --------------------------------------------------------------------------- #
# 读取辅助
# --------------------------------------------------------------------------- #
def _load_json(path: str) -> Optional[Any]:
    """安全读取 JSON，文件缺失 / 解析失败返回 None。"""
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (ValueError, OSError):
        return None


# --------------------------------------------------------------------------- #
# 格式化辅助
# --------------------------------------------------------------------------- #
def _fmt_num(v: Any) -> str:
    """数字格式化：None -> —；float 去除多余小数位。"""
    if v is None:
        return "—"
    if isinstance(v, float):
        if v == int(v):
            return str(int(v))
        return "%g" % v
    return str(v)


def _raw_cell(inp: Any, out: Any, cur: str) -> str:
    """原始价列：以原币种展示 输入 / 输出，缺失为 —。"""
    a = (f"{_fmt_num(inp)} {cur}".strip()) if inp is not None else "—"
    b = (f"{_fmt_num(out)} {cur}".strip()) if out is not None else "—"
    return f"{a} / {b}"


def _esc(s: Any) -> str:
    """HTML 转义。"""
    if s is None:
        return "—"
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# --------------------------------------------------------------------------- #
# 数据装配
# --------------------------------------------------------------------------- #
def _build_site_data(data_dir: str) -> Dict[str, Any]:
    """读取 data/ 并装配页面所需的聚合结构。"""
    watchlist: List[Dict[str, Any]] = _load_json(os.path.join(data_dir, "watchlist.json")) or []
    if not isinstance(watchlist, list):
        watchlist = []

    # 目标模型顺序（首次出现的 canonical 顺序）
    canons: List[str] = []
    for r in watchlist:
        c = r.get("canonical")
        if c and c not in canons:
            canons.append(c)

    sources = sorted({r.get("source") for r in watchlist if r.get("source")})

    rate = currency.get_rate()
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str = generated_at.split(" ")[0]

    # 按 canonical 分组，标注每组内输入¥最低行
    by_canon: Dict[str, List[Dict[str, Any]]] = {}
    for r in watchlist:
        c = r.get("canonical")
        if not c:
            continue
        by_canon.setdefault(c, []).append(r)

    groups: List[Dict[str, Any]] = []
    chart: Dict[str, List[Dict[str, Any]]] = {}
    for c in canons:
        rows = by_canon.get(c, [])
        inputs = [r.get("input_rmb") for r in rows if r.get("input_rmb") is not None]
        min_in = min(inputs) if inputs else None
        sorted_rows = sorted(rows, key=lambda x: (str(x.get("source") or "")))
        row_data: List[Dict[str, Any]] = []
        for r in sorted_rows:
            in_rmb = r.get("input_rmb")
            is_low = (
                in_rmb is not None and min_in is not None and in_rmb == min_in
            )
            row_data.append(
                {
                    "model_raw": r.get("model_raw") or "—",
                    "source": r.get("source") or "—",
                    "input_rmb": in_rmb,
                    "output_rmb": r.get("output_rmb"),
                    "cache_hit": r.get("cache_hit"),
                    "input": r.get("input"),
                    "output": r.get("output"),
                    "currency": r.get("currency") or "",
                    "context": r.get("context"),
                    "is_lowest": is_low,
                }
            )
        groups.append({"canonical": c, "rows": row_data})
        # 图表数据：仅含非空 input_rmb（chart.js 对 null 自动留空）
        chart[c] = [
            {"source": r.get("source"), "input_rmb": r.get("input_rmb")}
            for r in sorted_rows
        ]

    return {
        "generated_at": generated_at,
        "rate": rate,
        "metrics": {
            "models": len(canons),
            "sources": len(sources),
            "updated": date_str,
            "rate": rate,
        },
        "groups": groups,
        "chart": chart,
        "has_data": bool(watchlist),
    }


# --------------------------------------------------------------------------- #
# HTML 片段渲染
# --------------------------------------------------------------------------- #
def _stat_card(label: str, value: str, unit: str = "") -> str:
    unit_html = f'<small>{unit}</small>' if unit else ""
    return (
        f'<div class="stat-card">'
        f'<div class="label">{_esc(label)}</div>'
        f'<div class="value">{value}{unit_html}</div>'
        f"</div>"
    )


def _row_html(r: Dict[str, Any]) -> str:
    cls = ' class="lowest"' if r["is_lowest"] else ""
    cur = r["currency"]
    raw = _raw_cell(r["input"], r["output"], cur)
    ctx = r["context"] if r["context"] else "—"
    return (
        f"<tr{cls}>"
        f"<td>{_esc(r['model_raw'])}</td>"
        f"<td><span class='pill'>{_esc(r['source'])}</span></td>"
        f"<td class='num'>{_fmt_num(r['input_rmb'])}</td>"
        f"<td class='num'>{_fmt_num(r['output_rmb'])}</td>"
        f"<td class='num'>{_fmt_num(r['cache_hit'])}</td>"
        f"<td class='num muted'>{_esc(raw)}</td>"
        f"<td class='muted'>{_esc(ctx)}</td>"
        f"<td>{_esc(cur) or '—'}</td>"
        f"</tr>"
    )


def _group_card(g: Dict[str, Any]) -> str:
    has_best = any(r["is_lowest"] for r in g["rows"])
    badge = '<span class="badge-best">★ 最低输入价</span>' if has_best else ""
    rows_html = "".join(_row_html(r) for r in g["rows"])
    return f"""
    <div class="table-card">
      <div class="card-head"><h3>{_esc(g['canonical'])}</h3>{badge}</div>
      <div style="overflow-x:auto">
      <table>
        <thead><tr>
          <th>模型</th><th>源</th><th class="num">输入价(¥)</th>
          <th class="num">输出价(¥)</th><th class="num">缓存命中</th>
          <th class="num">原始价</th><th>上下文</th><th>货币</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
      </div>
    </div>"""


def _comparison_section(groups: List[Dict[str, Any]], has_data: bool) -> str:
    if not has_data or not groups:
        return """
        <div class="empty">
          <div class="big">暂无定价数据</div>
          <div>尚未抓取到目标模型的报价，运行 <code>python main.py</code> 刷新 data/ 后将自动生成比价表。</div>
        </div>"""
    return "".join(_group_card(g) for g in groups)


def _chart_section(canons: List[str], has_data: bool) -> str:
    if not has_data or not canons:
        return ""
    options = "".join(
        f'<option value="{_esc(c)}">{_esc(c)}</option>' for c in canons
    )
    return f"""
    <div class="chart-card">
      <div class="chart-head">
        <div>
          <div class="section-title" style="margin:0">各源输入价对比</div>
          <div class="section-sub" style="margin:4px 0 0">单位：¥ / 1M tokens · 绿色柱为最低价</div>
        </div>
        <select id="modelSelect" aria-label="选择模型">{options}</select>
      </div>
      <div style="position:relative;height:360px">
        <canvas id="priceChart"></canvas>
      </div>
    </div>"""


# --------------------------------------------------------------------------- #
# 静态资源（CSS / JS）—— 严格套用 boc-scraper 配色
# --------------------------------------------------------------------------- #
_BOC_CSS = """
:root{
  --primary:#533afd; --primary-deep:#4434d4; --primary-press:#2e2b8c;
  --primary-soft:#665efd; --primary-subdued:#b9b9f9; --brand-dark:#1c1e54;
  --green:#0ca678; --green-bg:#e6fcf5; --red:#e03131; --red-bg:#fff5f5;
  --canvas:#ffffff; --canvas-soft:#f6f9fc; --hairline:#e3e8ee;
  --ink:#0d253d; --ink-secondary:#273951; --ink-mute:#64748d;
  --on-primary:#ffffff;
  --shadow-1:0 1px 3px rgba(0,55,112,.08);
  --shadow-2:0 8px 24px rgba(0,55,112,.08),0 2px 6px rgba(0,55,112,.04);
}
*{box-sizing:border-box;}
body{margin:0;font-family:'Inter','Noto Sans SC',system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
  background:var(--canvas-soft);color:var(--ink);-webkit-font-smoothing:antialiased;line-height:1.5;}
a{color:var(--primary);}
code{background:var(--canvas-soft);padding:2px 6px;border-radius:6px;font-size:.9em;}

/* Hero + mesh */
.hero{position:relative;overflow:hidden;background:linear-gradient(135deg,#1c1e54,#4434d4);}
.hero .mesh{position:absolute;inset:0;
  background:
    radial-gradient(42% 52% at 14% 18%, rgba(102,94,253,.55), transparent 60%),
    radial-gradient(46% 56% at 86% 8%, rgba(83,58,253,.45), transparent 60%),
    radial-gradient(50% 60% at 72% 96%, rgba(179,185,249,.35), transparent 60%);
  filter:blur(8px);opacity:.92;}
.hero-inner{position:relative;z-index:1;max-width:1120px;margin:0 auto;padding:64px 24px 52px;}
.eyebrow{display:inline-block;font-size:12.5px;letter-spacing:.12em;text-transform:uppercase;
  color:var(--primary-subdued);background:rgba(255,255,255,.08);
  border:1px solid rgba(255,255,255,.18);padding:6px 14px;border-radius:999px;}
.hero h1{color:#fff;font-size:40px;line-height:1.15;margin:18px 0 8px;font-weight:800;letter-spacing:-.01em;}
.hero p.sub{color:rgba(255,255,255,.75);font-size:16px;margin:0;}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-top:32px;}
.stat-card{background:rgba(255,255,255,.97);border-radius:16px;padding:18px 20px;box-shadow:var(--shadow-2);}
.stat-card .label{color:var(--ink-mute);font-size:13px;margin-bottom:6px;}
.stat-card .value{color:var(--primary-deep);font-size:28px;font-weight:800;line-height:1.1;}
.stat-card .value small{font-size:14px;color:var(--ink-mute);font-weight:600;margin-left:4px;}

/* Layout */
.container{max-width:1120px;margin:0 auto;padding:40px 24px 56px;}
.section-title{font-size:24px;font-weight:800;color:var(--ink);margin:8px 0 6px;}
.section-sub{color:var(--ink-mute);font-size:14px;margin-bottom:20px;}

/* Table cards */
.table-card{background:var(--canvas);border:1px solid var(--hairline);border-radius:16px;
  box-shadow:var(--shadow-1);margin-bottom:24px;overflow:hidden;}
.table-card .card-head{display:flex;align-items:center;justify-content:space-between;gap:12px;
  padding:16px 20px;border-bottom:1px solid var(--hairline);background:var(--canvas-soft);}
.table-card .card-head h3{margin:0;font-size:17px;color:var(--ink);font-weight:700;}
.badge-best{font-size:12px;color:var(--green);background:var(--green-bg);
  padding:4px 10px;border-radius:999px;font-weight:700;white-space:nowrap;}
table{width:100%;border-collapse:collapse;}
th,td{padding:12px 16px;text-align:left;font-size:14px;border-bottom:1px solid var(--hairline);}
th{color:var(--ink-mute);font-weight:600;background:var(--canvas-soft);font-size:12.5px;
  text-transform:uppercase;letter-spacing:.03em;}
td.num{text-align:right;font-variant-numeric:tabular-nums;font-weight:600;}
td.muted{color:var(--ink-mute);font-weight:500;}
tbody tr:last-child td{border-bottom:none;}
tr.lowest td{border-left:3px solid var(--green);background:var(--green-bg);}
.pill{border-radius:999px;padding:3px 10px;font-size:12px;font-weight:600;
  background:var(--brand-dark);color:#fff;}

/* Chart card */
.chart-card{background:var(--canvas);border:1px solid var(--hairline);border-radius:16px;
  box-shadow:var(--shadow-1);padding:24px;margin-bottom:8px;}
.chart-head{display:flex;align-items:center;justify-content:space-between;gap:16px;
  margin-bottom:16px;flex-wrap:wrap;}
select{font:inherit;padding:10px 14px;border-radius:12px;border:1px solid var(--hairline);
  background:var(--canvas);color:var(--ink);font-size:14px;min-width:240px;box-shadow:var(--shadow-1);cursor:pointer;}

/* Empty state */
.empty{padding:64px 24px;text-align:center;color:var(--ink-mute);
  background:var(--canvas);border:1px dashed var(--hairline);border-radius:16px;}
.empty .big{font-size:18px;color:var(--ink-secondary);font-weight:700;margin-bottom:8px;}

/* Footer */
footer{background:var(--brand-dark);color:rgba(255,255,255,.7);padding:28px 24px;
  text-align:center;font-size:13px;line-height:1.6;margin-top:24px;}
footer .note{max-width:780px;margin:0 auto 8px;}
footer .note strong{color:var(--primary-subdued);}
footer .disc{color:var(--primary-subdued);}

@media (max-width:760px){
  .metrics{grid-template-columns:repeat(2,1fr);}
  .hero h1{font-size:30px;}
}
"""

_CHART_JS = """
const SITE_DATA = __SITE_DATA__;
(function(){
  if (typeof Chart === 'undefined') return;            // 离线无 CDN 时静默跳过
  const COLORS = { primary: '#533afd', green: '#0ca678' };
  const sel = document.getElementById('modelSelect');
  const canvas = document.getElementById('priceChart');
  if (!sel || !canvas) return;
  const ctx = canvas.getContext('2d');
  let chart = null;
  function draw(canon){
    const rows = (SITE_DATA.chart && SITE_DATA.chart[canon]) || [];
    const vals = rows.map(r => (r.input_rmb == null ? null : r.input_rmb));
    const nums = vals.filter(v => v != null);
    const min = nums.length ? Math.min.apply(null, nums) : null;
    const colors = vals.map(v => (v != null && min != null && v === min) ? COLORS.green : COLORS.primary);
    if (chart) chart.destroy();
    chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: rows.map(r => r.source),
        datasets: [{ label: '输入价 (¥)', data: vals, backgroundColor: colors, borderRadius: 8, maxBarThickness: 56 }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: c => (c.parsed.y == null ? '无数据' : '¥ ' + c.parsed.y) } }
        },
        scales: {
          y: { beginAtZero: true, ticks: { callback: v => '¥' + v }, grid: { color: '#eef2f7' } },
          x: { grid: { display: false } }
        }
      }
    });
  }
  sel.addEventListener('change', e => draw(e.target.value));
  draw(sel.value);
})();
"""


# --------------------------------------------------------------------------- #
# 主入口
# --------------------------------------------------------------------------- #
def build_site(data_dir: str, out_path: str = None) -> str:
    """读取 data/watchlist.json + data/prices.json，生成自包含静态网页 site/index.html。

    Args:
        data_dir: data/ 目录（含 watchlist.json / prices.json）。
        out_path: 输出 HTML 路径；默认 {data_dir 的上级}/site/index.html。

    Returns:
        写出文件的绝对路径。
    """
    if out_path is None:
        out_path = os.path.join(
            os.path.dirname(os.path.abspath(data_dir)), "site", "index.html"
        )
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    data = _build_site_data(data_dir)
    m = data["metrics"]
    canons = [g["canonical"] for g in data["groups"]]

    # Hero 指标卡
    metrics_html = "".join(
        [
            _stat_card("追踪模型数", str(m["models"]), "个"),
            _stat_card("数据源数", str(m["sources"]), "个"),
            _stat_card("最近更新", _esc(m["updated"])),
            _stat_card("汇率 USD→CNY", _fmt_num(m["rate"]), "¥/$"),
        ]
    )

    comparison = _comparison_section(data["groups"], data["has_data"])
    chart_block = _chart_section(canons, data["has_data"])

    # 数据以 JSON 嵌入；转义 </ 防止提前闭合 script
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    js = _CHART_JS.replace("__SITE_DATA__", data_json)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>大模型 Token 定价追踪</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
<style>{_BOC_CSS}</style>
</head>
<body>
  <header class="hero">
    <div class="mesh"></div>
    <div class="hero-inner">
      <span class="eyebrow">官网报价 · 每周自动更新</span>
      <h1>大模型 Token 定价追踪</h1>
      <p class="sub">跨 10 个官方渠道，自动比对主流大模型输入 / 输出价格（人民币计价）。</p>
      <div class="metrics">{metrics_html}</div>
    </div>
  </header>

  <main class="container">
    <div class="section-title">跨源比价表</div>
    <div class="section-sub">按模型分组；绿色高亮行为该模型「输入价最低」的渠道。</div>
    {comparison}
    {chart_block}
  </main>

  <footer>
    <div class="note">数据来源：各模型官网公开定价（阿里云百炼、火山方舟、腾讯云<strong>仅取中国大陆区域</strong>、智谱 BigModel、DeepSeek、MiniMax、Kimi、ModelMesh 等 10 个官方渠道），由 GitHub Action 每周自动抓取。</div>
    <div class="disc">⚠️ 数据仅供参考，请以各官网实时报价为准。最近更新：{_esc(data['generated_at'])}</div>
  </footer>

  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <script>{js}</script>
</body>
</html>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return os.path.abspath(out_path)
