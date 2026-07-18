"""大模型 Token 定价自动抓取 —— 命令行入口与编排。

流程：
  1. 读取 config/sources.yml 与 config/models.yml
  2. 逐源抓取 + 解析（失败仅记录状态，不中断）
  3. 汇率换算（input_rmb / output_rmb）
  4. 模型匹配标注 canonical，写出全量 / watchlist 的 JSON/CSV
  5. 与历史（仓库已提交）data/prices.json 对比，生成周环比变动
  6. 生成 REPORT.md / issue_body.md
  7. 输出 changed 标志（CI 写入 $GITHUB_OUTPUT，供 workflow 开 Issue）

用法：
  python main.py [--dry-run]
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import os
import shutil
import sys
from typing import Any, Dict, List

import yaml

# 以 main.py 所在目录为项目根，保证无论从何处运行都能定位 config/data
ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(ROOT, "config")
DATA_DIR = os.path.join(ROOT, "data")

sys.path.insert(0, ROOT)

from scrapers.base import BaseScraper  # noqa: E402
from core import audit, currency, matcher, report, store, site  # noqa: E402
from core import openrouter_verify  # noqa: E402


def _load_yaml(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_scraper_class(parser_name: str) -> type:
    """动态导入 scrapers/<parser_name>.py 并返回 BaseScraper 子类。"""
    module = importlib.import_module(f"scrapers.{parser_name}")
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, BaseScraper) and obj is not BaseScraper:
            return obj
    raise RuntimeError(f"parser '{parser_name}' 未找到 BaseScraper 子类")


def run_sources(sources: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """抓取所有源，返回 (全部记录, 抓取状态)。"""
    records: List[Dict[str, Any]] = []
    scrape_status: Dict[str, Dict[str, Any]] = {}
    for src in sources:
        sid = src.get("id", "?")
        try:
            scraper_cls = _get_scraper_class(src["parser"])
            recs = scraper_cls(src).run()
            records.extend(recs)
            scrape_status[sid] = {"ok": True, "count": len(recs), "error": None}
            print(f"  [ok]   {sid}: {len(recs)} 条")
        except Exception as exc:  # 单源失败不中断整体
            scrape_status[sid] = {"ok": False, "count": 0, "error": str(exc)}
            print(f"  [FAIL] {sid}: {exc}")
    return records, scrape_status


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LLM Token 定价抓取器")
    parser.add_argument("--dry-run", action="store_true",
                        help="照常抓取并写 data/，仅额外打印摘要（不写 $GITHUB_OUTPUT）")
    args = parser.parse_args(argv)

    print("== 读取配置 ==")
    sources = _load_yaml(os.path.join(CONFIG_DIR, "sources.yml")) or []
    models_cfg = _load_yaml(os.path.join(CONFIG_DIR, "models.yml")) or {"models": []}
    print(f"  源数量: {len(sources)}，目标模型: {len(models_cfg.get('models', []))}")

    print("== 抓取各源 ==")
    records, scrape_status = run_sources(sources)

    print("== 汇率换算 / 模型匹配 ==")
    currency.enrich(records)

    # OpenRouter 白名单模型强制 canonical（热门主力即使不在 models.yml 也要进页面）
    try:
        or_rules = _load_yaml(os.path.join(CONFIG_DIR, "openrouter.yml")) or {}
        id_to_canon = {
            w.get("id"): w.get("model")
            for w in (or_rules.get("whitelist") or [])
            if w.get("id") and w.get("model")
        }
        for r in records:
            if r.get("source") == "openrouter" and r.get("openrouter_id") in id_to_canon:
                r["canonical"] = id_to_canon[r["openrouter_id"]]
    except Exception as _exc:
        print(f"  [warn] openrouter whitelist canonical: {_exc}")

    annotated, watchlist = matcher.build_watchlist(records, models_cfg)
    # 合并：matcher 命中 + openrouter 白名单已写 canonical 的记录
    seen = {(r.get("source"), r.get("model_raw"), r.get("input"), r.get("output")) for r in watchlist}
    for r in annotated:
        if r.get("source") == "openrouter" and r.get("canonical"):
            key = (r.get("source"), r.get("model_raw"), r.get("input"), r.get("output"))
            if key not in seen:
                watchlist.append(r)
                seen.add(key)

    print(f"  全量记录: {len(annotated)}，命中目标模型: {len(watchlist)}")

    print("== 写出 data/ ==")
    # 先备份已提交的 prices.json 用于对比，再覆盖
    committed = os.path.join(DATA_DIR, "prices.json")
    prev_tmp = os.path.join(DATA_DIR, ".prices.prev.json")
    has_prev = os.path.exists(committed)
    if has_prev:
        shutil.copyfile(committed, prev_tmp)
    store.write_outputs(annotated, DATA_DIR)
    if has_prev:
        deltas = store.compare_previous(os.path.join(DATA_DIR, "prices.json"), prev_tmp)
        os.remove(prev_tmp)
    else:
        deltas = []

    print("== 生成报告 ==")
    from datetime import datetime
    report_md, issue_body_md = report.build_report(
        watchlist, deltas, scrape_status, generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    report.write_outputs(DATA_DIR, report_md, issue_body_md)

    print("== 数据核对（防幻觉自我检查）==")
    audit_res = audit.run(DATA_DIR, sources_cfg=sources)
    astats = audit_res["stats"]
    print(f"  可疑项 {astats['suspects']}（high {astats['high']} / med {astats['med']} / low {astats['low']}）")

    print("== OpenRouter 二次验证 ==")
    or_recs = [r for r in annotated if r.get("source") == "openrouter"]
    or_verify = openrouter_verify.verify(DATA_DIR, records=or_recs)
    os_ = or_verify.get("stats") or {}
    print(f"  OpenRouter parsed={os_.get('parsed',0)} ok={or_verify.get('ok')} suspects={os_.get('suspects',0)} high={os_.get('high',0)}")

    print("== 生成美化网页 ==")
    # 主流模型目录校验：非法目录不得静默通过
    from core import mainstream_catalog
    catalog_path = os.path.join(CONFIG_DIR, "mainstream_models.yml")
    try:
        catalog = mainstream_catalog.load_catalog(catalog_path)
        print(
            "  主流目录:",
            len(mainstream_catalog.catalog_canons(catalog, "domestic")),
            "国内 /",
            len(mainstream_catalog.catalog_canons(catalog, "overseas")),
            "海外",
        )
    except (OSError, ValueError) as exc:
        print(f"  [error] 主流目录校验失败: {exc}")
        return 2

    # 在 changed 标志写入之前生成，保证 site/index.html 一定存在（供 workflow git add site/）
    site_path = site.build_site(DATA_DIR)
    print(f"  site -> {site_path}")

    changed = len(deltas) > 0
    print(f"== 完成 == 记录总数 {len(annotated)}，命中 {len(watchlist)}，变动 {len(deltas)}")
    print(f"changed={'true' if changed else 'false'}")

    if not args.dry_run:
        github_output = os.environ.get("GITHUB_OUTPUT", "")
        if github_output:
            with open(github_output, "a", encoding="utf-8") as f:
                f.write(f"changed={'true' if changed else 'false'}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
