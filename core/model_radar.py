"""新模型雷达：自动发现「官网/渠道新上架、但站点还没收录」的疑似主力模型。

背景教训：``config/new_models.yml`` 是**手工登记**清单，不是自动发现。2026-09-03
发布的 GPT-6 Astra 因无人登记，整整漏抓 6 天（2026-09-09 才人工补齐）。
本模块把「发现」这一半自动化，把「登记」这一半留给人工拍板。

工作原理
--------
1. 读 ``data/openrouter_raw.json`` —— OpenRouter ``/api/v1/models`` 的**全量**
   原始缓存（``body.data`` 含所有模型，不受 ``openrouter.yml`` 白名单限制）。
   雷达只读该文件：**零额外网络请求、不抓取、不写权威数据**。
2. 与「已登记集合」做差集：openrouter.yml 白名单 id、mainstream_models.yml 的
   openrouter_id、new_models.yml / models.yml 的别名、以及 data/prices.json 里
   已抓到过的 openrouter_id 与 canonical。
3. 过滤噪声：非文本模态、免费模型、mini/nano/lite 等次级型号、上架超过
   ``lookback_days`` 天的老模型。
4. 同厂商内按输入价排序，``>= 最高价 × flagship_ratio`` 判为「疑似旗舰」。
5. 产出 ``data/new_model_candidates.json`` + 报告段落 + webhook 告警。

⛔ 不自动改 ``config/``：是否收录属决策（收录范围、展示名、厂商归属都需要判断），
雷达只给结论 + 可直接粘贴的 ``new_models.yml`` 片段，人工确认后再登记。
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Pattern, Set

DEFAULT_LOOKBACK_DAYS = 60
DEFAULT_FLAGSHIP_RATIO = 0.8
DEFAULT_MIN_INPUT_USD = 0.1

_DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "lookback_days": DEFAULT_LOOKBACK_DAYS,
    "flagship_ratio": DEFAULT_FLAGSHIP_RATIO,
    "min_input_usd": DEFAULT_MIN_INPUT_USD,
    "providers": [],
    "families": {},
    "domestic_providers": [],
    "noise_patterns": [],
}


# --------------------------------------------------------------------- #
# 配置
# --------------------------------------------------------------------- #
def _load_cfg(config_dir: Optional[str] = None) -> Dict[str, Any]:
    """读取 config/model_radar.yml，缺失字段用默认值兜底。"""
    cfg = dict(_DEFAULTS)
    if not config_dir:
        return cfg
    path = os.path.join(config_dir, "model_radar.yml")
    if not os.path.exists(path):
        return cfg
    try:
        import yaml

        with open(path, encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        if isinstance(loaded, dict):
            cfg.update({k: v for k, v in loaded.items() if v is not None})
    except Exception:  # 配置损坏不阻断主流程，退化为默认配置
        return cfg
    return cfg


# --------------------------------------------------------------------- #
# 已登记集合
# --------------------------------------------------------------------- #
def _norm(s: Any) -> str:
    """归一化：小写 + 只保留字母数字（用于 id / 名称比对）。"""
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def _clean_name(name: Any) -> str:
    """剥离 OpenRouter 的「OpenAI: 」类厂商前缀。"""
    s = str(name or "").strip()
    s = re.sub(r"^[A-Za-z0-9 .+-]+:\s*", "", s)
    return s.strip() or str(name or "")


# 日期/快照后缀：-0731、-20260812 等（OpenRouter 给快照版模型加的后缀）
_DATE_SUFFIX_RE = re.compile(r"-\d{3,8}$")


def _variants(mid: str) -> List[str]:
    """同一模型的 id 变体集合（用于「是否已登记」比对）。

    OpenRouter 会给同一模型挂出 ``:batch`` / ``:free`` 等变体条目，也会给快照版
    加 ``-0731`` 日期后缀——这些都不算新模型。比对已登记集合时必须一并归一，
    否则雷达会拿 ``z-ai/glm-5.3:batch``、``deepseek/deepseek-v4-flash-0731``
    这类已收录模型的变体刷屏。
    """
    out = [mid]
    base = mid.split(":", 1)[0]
    if base != mid:
        out.append(base)
    for cur in list(out):
        stripped = _DATE_SUFFIX_RE.sub("", cur)
        if stripped != cur:
            out.append(stripped)
    return out


def load_known(config_dir: Optional[str], data_dir: str) -> Set[str]:
    """汇总「已登记」的归一化 id / 名称集合。"""
    known: Set[str] = set()

    def add(v: Any) -> None:
        n = _norm(v)
        if n:
            known.add(n)

    if config_dir:
        try:
            import yaml

            def _yload(name: str) -> Any:
                p = os.path.join(config_dir, name)
                if not os.path.exists(p):
                    return None
                with open(p, encoding="utf-8") as f:
                    return yaml.safe_load(f)

            # 1) openrouter.yml 白名单 id + 展示名
            or_rules = _yload("openrouter.yml") or {}
            for w in (or_rules.get("whitelist") or []):
                add(w.get("id"))
                add(w.get("model"))

            # 2) mainstream_models.yml 的 openrouter_id / canonical
            cat = _yload("mainstream_models.yml") or {}
            for region in ("domestic", "overseas"):
                for vendor in ((cat.get(region) or {}).get("vendors") or []):
                    for m in (vendor.get("models") or []):
                        add(m.get("openrouter_id"))
                        add(m.get("canonical"))

            # 3) new_models.yml / models.yml 的 canonical 与别名
            nm = _yload("new_models.yml") or {}
            for m in (nm.get("models") or []):
                add(m.get("canonical"))
                for a in (m.get("aliases") or []):
                    add(a)
            mm = _yload("models.yml") or {}
            for m in (mm.get("models") or []):
                add(m.get("canonical"))
                for a in (m.get("aliases") or []):
                    add(a)
        except Exception:
            pass

    # 4) data/prices.json 里已抓到过的 openrouter_id / canonical / model_raw
    try:
        with open(os.path.join(data_dir, "prices.json"), encoding="utf-8") as f:
            prices = json.load(f)
        for r in prices if isinstance(prices, list) else []:
            add(r.get("openrouter_id"))
            add(r.get("canonical"))
            add(r.get("model_raw"))
    except (OSError, ValueError):
        pass

    return known


# --------------------------------------------------------------------- #
# 原始缓存读取
# --------------------------------------------------------------------- #
def _read_raw_models(data_dir: str) -> List[Dict[str, Any]]:
    """读取 OpenRouter 全量原始缓存的模型列表。

    兼容两种结构：``{"body": {"data": [...]}}``（scrapers/openrouter.py 落盘格式）
    与直接的 ``{"data": [...]}``（测试 fixture / 手工数据）。
    """
    path = os.path.join(data_dir, "openrouter_raw.json")
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return []
    if not isinstance(raw, dict):
        return []
    body = raw.get("body") if isinstance(raw.get("body"), dict) else raw
    items = body.get("data") if isinstance(body, dict) else None
    if not isinstance(items, list):
        return []
    return [m for m in items if isinstance(m, dict)]


# --------------------------------------------------------------------- #
# 工具
# --------------------------------------------------------------------- #
def _per_m(v: Any) -> Optional[float]:
    """USD/token → USD / 1M tokens。"""
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f <= 0:
        return None
    return round(f * 1_000_000, 6)


def _age_days(created: Any, today: Optional[datetime] = None) -> Optional[int]:
    """OpenRouter created（unix 秒，也可能是毫秒）→ 距今天数。无法判定返回 None。"""
    try:
        ts = float(created)
    except (TypeError, ValueError):
        return None
    if ts <= 0:
        return None
    if ts > 1e12:  # 毫秒时间戳
        ts = ts / 1000.0
    base = today or datetime.now(timezone.utc)
    try:
        born = datetime.fromtimestamp(ts, tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None
    return max(0, int((base - born).total_seconds() // 86400))


def _compile_noise(patterns: Any) -> List[Pattern[str]]:
    out: List[Pattern[str]] = []
    for p in patterns or []:
        try:
            out.append(re.compile(re.escape(str(p)), re.I))
        except re.error:
            continue
    return out


def _fmt_ctx(n: Any) -> Optional[str]:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return None
    if n >= 1_000_000:
        return f"{n / 1_000_000:g}M"
    if n >= 1000:
        return f"{n // 1000}K"
    return str(n)


# --------------------------------------------------------------------- #
# 主扫描
# --------------------------------------------------------------------- #
def scan(
    data_dir: str,
    config_dir: Optional[str] = None,
    today: Optional[datetime] = None,
) -> Dict[str, Any]:
    """扫描 OpenRouter 全量模型，返回未登记的疑似新模型候选。

    Args:
        data_dir: data/ 目录（读 openrouter_raw.json / prices.json）。
        config_dir: config/ 目录（读 model_radar.yml 及已登记集合）。
        today: 基准时间（测试注入用），默认当前 UTC。

    Returns:
        ``{generated_at, enabled, lookback_days, scanned, known_count,
           candidates, flagship_count}``
    """
    cfg = _load_cfg(config_dir)
    base = today or datetime.now(timezone.utc)
    res: Dict[str, Any] = {
        "generated_at": base.strftime("%Y-%m-%d %H:%M:%S"),
        "enabled": bool(cfg.get("enabled", True)),
        "lookback_days": int(cfg.get("lookback_days") or DEFAULT_LOOKBACK_DAYS),
        "scanned": 0,
        "known_count": 0,
        "candidates": [],
        "flagship_count": 0,
    }
    if not res["enabled"]:
        return res

    models = _read_raw_models(data_dir)
    res["scanned"] = len(models)
    if not models:
        return res

    known = load_known(config_dir, data_dir)
    res["known_count"] = len(known)

    providers = {str(p).lower() for p in (cfg.get("providers") or [])}
    families: Dict[str, str] = {str(k).lower(): str(v) for k, v in (cfg.get("families") or {}).items()}
    domestic = {str(p).lower() for p in (cfg.get("domestic_providers") or [])}
    noise = _compile_noise(cfg.get("noise_patterns"))
    lookback = int(cfg.get("lookback_days") or DEFAULT_LOOKBACK_DAYS)
    ratio = float(cfg.get("flagship_ratio") or DEFAULT_FLAGSHIP_RATIO)
    min_in = float(cfg.get("min_input_usd") or DEFAULT_MIN_INPUT_USD)

    cands: List[Dict[str, Any]] = []
    for m in models:
        mid = str(m.get("id") or "")
        if "/" not in mid:
            continue
        vendor = mid.split("/", 1)[0].lower()
        if providers and vendor not in providers:
            continue
        name = _clean_name(m.get("name"))
        # `:` 变体条目（:batch / :free / :extended…）是计费通道变体，不是新模型
        if ":" in mid:
            continue
        # 已登记（id 及其变体、或展示名命中）→ 跳过
        if any(_norm(v) in known for v in _variants(mid)) or _norm(name) in known:
            continue

        # 只要文本输出模态
        arch = m.get("architecture") or {}
        outs = {str(x).lower() for x in (arch.get("output_modalities") or ["text"])}
        if "text" not in outs:
            continue

        pricing = m.get("pricing") or {}
        inp = _per_m(pricing.get("prompt"))
        out = _per_m(pricing.get("completion"))
        if inp is None and out is None:
            continue  # 免费模型 / 无报价
        if inp is not None and inp < min_in:
            continue

        age = _age_days(m.get("created"), base)
        if age is None or age > lookback:
            continue  # 上架时间不可判定或过老 → 视为噪声

        if any(rx.search(mid) or rx.search(name) for rx in noise):
            continue

        created_iso = ""
        try:
            ts = float(m.get("created") or 0)
            if ts > 1e12:
                ts /= 1000.0
            created_iso = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        except (TypeError, ValueError, OSError, OverflowError):
            created_iso = ""

        cands.append({
            "id": mid,
            "name": name,
            "provider": vendor,
            "family": families.get(vendor, vendor),
            "region": "domestic" if vendor in domestic else "overseas",
            "created": created_iso,
            "age_days": age,
            "input_usd_per_m": inp,
            "output_usd_per_m": out,
            "context": _fmt_ctx(m.get("context_length")),
            "flagship": False,
            "registered": False,
        })

    # 同厂商内按输入价判定疑似旗舰（旗舰通常是最贵的主力档）
    by_vendor: Dict[str, List[Dict[str, Any]]] = {}
    for c in cands:
        by_vendor.setdefault(str(c["provider"]), []).append(c)
    for _v, items in by_vendor.items():
        prices = [float(i.get("input_usd_per_m") or 0) for i in items]
        mx = max(prices) if prices else 0.0
        for i in items:
            cur = float(i.get("input_usd_per_m") or 0)
            if mx > 0 and cur >= mx * ratio:
                i["flagship"] = True
                i["reason"] = f"新上架 {i['age_days']} 天 · {i['family']} 系候选最高价档"
            else:
                i["reason"] = f"新上架 {i['age_days']} 天 · {i['family']} 系新增次级档"

    cands.sort(key=lambda c: (
        0 if c.get("flagship") else 1,
        int(c.get("age_days") or 0),
        str(c.get("id") or ""),
    ))
    res["candidates"] = cands
    res["flagship_count"] = sum(1 for c in cands if c.get("flagship"))
    return res


def flagships(res: Dict[str, Any]) -> List[Dict[str, Any]]:
    """取候选里的疑似旗舰（告警/推送只报这一类）。"""
    return [c for c in (res.get("candidates") or []) if c.get("flagship")]


# --------------------------------------------------------------------- #
# 输出
# --------------------------------------------------------------------- #
def write_output(data_dir: str, res: Dict[str, Any]) -> Optional[str]:
    """写 data/new_model_candidates.json，返回路径；失败返回 None。"""
    path = os.path.join(data_dir, "new_model_candidates.json")
    try:
        os.makedirs(data_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        return path
    except OSError:
        return None


def suggested_yaml(res: Dict[str, Any], only_flagship: bool = True) -> str:
    """生成可直接粘贴进 config/new_models.yml 的登记片段（待人工确认）。"""
    items = flagships(res) if only_flagship else (res.get("candidates") or [])
    if not items:
        return ""
    lines: List[str] = ["models:"]
    for c in items:
        inp = c.get("input_usd_per_m")
        out = c.get("output_usd_per_m")
        price_txt = ""
        if inp is not None and out is not None:
            price_txt = f"${inp:g}/${out:g}"
        lines.extend([
            f"  - canonical: {c.get('name')}",
            f"    family: {c.get('family') or c.get('provider')}",
            f"    region: {c.get('region') or 'overseas'}",
            "    status: tracking",
            "    priority: high",
            f"    aliases: [{c.get('name')}, {str(c.get('id') or '').split('/')[-1]}, {c.get('id')}]",
            "    note: 雷达自动发现"
            + (f"（OpenRouter {c.get('created') or '?'} 上架" + (f"，{price_txt}" if price_txt else "") + "）")
            + "；确认后补官网抓取/白名单并转 active",
        ])
    return "\n".join(lines)


def report_section(res: Dict[str, Any], title: str = "四、新模型雷达（待人工登记）") -> str:
    """报告段落：候选表格 + 待登记 YAML（折叠）。"""
    scanned = res.get("scanned", 0)
    cands = res.get("candidates") or []
    lookback = res.get("lookback_days")
    lines: List[str] = [f"\n## {title}\n"]
    if not cands:
        lines.append(
            f"扫描 OpenRouter 全量 {scanned} 个模型：近 {lookback} 天内**没有**未登记的新候选。\n"
        )
        return "\n".join(lines)

    lines.append(
        f"扫描 OpenRouter 全量 {scanned} 个模型，发现 **{len(cands)}** 个未登记候选"
        f"（疑似旗舰 **{res.get('flagship_count', 0)}** 个）：\n"
    )
    lines.append("| 模型 | 厂商 | 上架 | 距今 | 输入 $/1M | 输出 $/1M | 判定 |")
    lines.append("|---|---|---|---|---|---|---|")
    for c in cands:
        inp = c.get("input_usd_per_m")
        out = c.get("output_usd_per_m")
        lines.append(
            "| `{id}`（{name}） | {fam} | {created} | {age} 天 | {inp} | {out} | {tag} |".format(
                id=c.get("id"),
                name=c.get("name"),
                fam=c.get("family") or c.get("provider"),
                created=c.get("created") or "—",
                age=c.get("age_days") if c.get("age_days") is not None else "—",
                inp=f"${inp:g}" if inp is not None else "—",
                out=f"${out:g}" if out is not None else "—",
                tag="疑似旗舰" if c.get("flagship") else "新增档位",
            )
        )
    yml = suggested_yaml(res)
    if yml:
        lines.append(
            "\n<details><summary>待登记 YAML（粘贴到 <code>config/new_models.yml</code>）</summary>\n"
        )
        lines.append("```yaml")
        lines.append(yml)
        lines.append("```\n")
        lines.append("</details>\n")
    return "\n".join(lines)
