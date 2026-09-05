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
  python main.py --verify-only   # 纯只读验证：不抓取、不写 data/
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import logging
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

import yaml

logger = logging.getLogger("tps")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)

# 以 main.py 所在目录为项目根，保证无论从何处运行都能定位 config/data
ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(ROOT, "config")
DATA_DIR = os.path.join(ROOT, "data")

sys.path.insert(0, ROOT)

from scrapers.base import BaseScraper  # noqa: E402
from core import audit, currency, matcher, report, store, site, notifier  # noqa: E402
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


def _run_one(src: Dict[str, Any]) -> tuple[str, List[Dict[str, Any]], str | None]:
    """抓取单个源，返回 (sid, records, error)。"""
    sid = src.get("id", "?")
    try:
        scraper_cls = _get_scraper_class(src["parser"])
        scraper = scraper_cls(src)
        recs = scraper.run()
        return sid, recs, None
    except Exception as exc:  # 单源失败不中断整体
        return sid, [], str(exc)


def run_sources(sources: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """抓取所有源，返回 (全部记录, 抓取状态)。

    并行策略：非 Playwright 源（js: false，requests/JSON API）用线程池并行，
    每个 scraper 独立 session，线程安全；Playwright 源（js: true）浏览器实例
    资源竞争大，保持顺序执行。CI 总耗时约从 8min 降到 3-4min。
    """
    records: List[Dict[str, Any]] = []
    scrape_status: Dict[str, Dict[str, Any]] = {}

    fast = [s for s in sources if not s.get("js")]
    slow = [s for s in sources if s.get("js")]

    # 并行快源
    if fast:
        with ThreadPoolExecutor(max_workers=min(6, len(fast))) as pool:
            futures = {pool.submit(_run_one, src): src.get("id", "?") for src in fast}
            for fut in as_completed(futures):
                sid, recs, err = fut.result()
                records.extend(recs)
                scrape_status[sid] = {"ok": err is None, "count": len(recs), "error": err}
                if err:
                    logger.warning("源 %s 失败: %s", sid, err)
                else:
                    logger.info("源 %s: %d 条", sid, len(recs))

    # 顺序跑慢源（Playwright SPA）
    for src in slow:
        sid, recs, err = _run_one(src)
        records.extend(recs)
        scrape_status[sid] = {"ok": err is None, "count": len(recs), "error": err}
        if err:
            logger.warning("源 %s 失败: %s", sid, err)
        else:
            logger.info("源 %s: %d 条", sid, len(recs))

    return records, scrape_status


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LLM Token 定价抓取器")
    parser.add_argument("--dry-run", action="store_true",
                        help="照常抓取并写 data/，仅额外打印摘要（不写 $GITHUB_OUTPUT）")
    parser.add_argument("--verify-only", action="store_true",
                        help="纯只读验证：不抓取、不写 data/，仅对磁盘现有 data/ 跑审计门禁 + OpenRouter 二次验证")
    args = parser.parse_args(argv)

    # ⛔ 纯只读验证入口：供本机 cron / 巡检使用，避免与本机抓取 write data/ 造成云端竞争。
    # 只校验云端已提交的 data/（git pull 后），零写入、零网络抓取，天然幂等。
    if args.verify_only:
        return _verify_existing(DATA_DIR)

    print("== 读取配置 ==")
    sources = _load_yaml(os.path.join(CONFIG_DIR, "sources.yml")) or []
    models_cfg = _load_yaml(os.path.join(CONFIG_DIR, "models.yml")) or {"models": []}
    logger.info("源数量: %d，目标模型: %d", len(sources), len(models_cfg.get("models", [])))

    print("== 抓取各源 ==")
    records, scrape_status = run_sources(sources)

    print("== 汇率换算 / 模型匹配 ==")
    currency.enrich(records)

    # OpenRouter / 海外厂商官网白名单模型强制 canonical（热门主力即使不在 models.yml 也要进页面）
    # 海外官网源（openai/anthropic/gemini/grok）的记录自带 openrouter_id，复用同一白名单映射。
    _WHITELIST_SOURCES = ("openrouter", "openai", "anthropic", "gemini", "grok")
    try:
        or_rules = _load_yaml(os.path.join(CONFIG_DIR, "openrouter.yml")) or {}
        id_to_canon = {
            w.get("id"): w.get("model")
            for w in (or_rules.get("whitelist") or [])
            if w.get("id") and w.get("model")
        }
        for r in records:
            if r.get("source") in _WHITELIST_SOURCES and r.get("openrouter_id") in id_to_canon:
                r["canonical"] = id_to_canon[r["openrouter_id"]]
    except Exception as _exc:
        print(f"  [warn] openrouter whitelist canonical: {_exc}")

    annotated, watchlist = matcher.build_watchlist(records, models_cfg)
    # 合并：matcher 命中 + 白名单已写 canonical 的记录
    seen = {(r.get("source"), r.get("model_raw"), r.get("input"), r.get("output")) for r in watchlist}
    for r in annotated:
        if r.get("source") in _WHITELIST_SOURCES and r.get("canonical"):
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

    # 每日快照归档（供历史趋势图使用）
    snap = store.archive_snapshot(DATA_DIR)
    if snap:
        logger.info("归档快照: %s", snap)
    # 官方源价格调价 + 新模型检测（驱动页面顶部横幅与新品角标）
    from datetime import date as _d
    _today_iso = _d.today().isoformat()
    oc = store.build_official_changes(DATA_DIR, lookback_days=7, today_iso=_today_iso)
    try:
        import json as _json
        _oc_path = os.path.join(DATA_DIR, "official_changes.json")
        with open(_oc_path, "w", encoding="utf-8") as _f:
            _json.dump(oc, _f, ensure_ascii=False, indent=2)
        # 调价事件逐日回填落盘（price_change_log.json，append-only，与历史快照对应）
        _pl = store.backfill_official_change_log(DATA_DIR)
        if oc.get("changes") or oc.get("new_models"):
            logger.info("官方变动: 调价 %d 条 / 新增 %d 条 / 事件日志累计 %d 条",
                        len(oc.get("changes") or []), len(oc.get("new_models") or []),
                        _pl.get("total") or 0)
    except OSError as e:
        logger.warning("写官方变动检测失败: %s", e)
    if has_prev:
        deltas = store.compare_previous(os.path.join(DATA_DIR, "prices.json"), prev_tmp)
        # 临时备份删除失败（如沙箱回收站不可用）不应中断主流程；残留文件由 .gitignore 兜底
        try:
            os.remove(prev_tmp)
        except OSError:
            print(f"  [warn] 临时备份 {prev_tmp} 清理失败（已忽略，不影响结果）")
    else:
        deltas = []

    print("== 生成报告 ==")
    from datetime import datetime
    report_md, issue_body_md = report.build_report(
        watchlist, deltas, scrape_status, generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    report.write_outputs(DATA_DIR, report_md, issue_body_md)

    # 价格变动推送（飞书/企微 webhook；未配置则静默跳过，不阻断主流程）
    from datetime import date as _today

    notifier.notify_price_changes(deltas, _today.today().strftime("%Y-%m-%d"))

    print("== 数据核对（防幻觉自我检查）==")
    audit_res = audit.run(DATA_DIR, sources_cfg=sources)
    astats = audit_res["stats"]
    print(f"  可疑项 {astats['suspects']}（high {astats['high']} / med {astats['med']} / low {astats['low']}）")

    # ⛔ 数据门禁：Tier1 high 级结构性错误（缓存>输入、关键模型缺输入价等）直接阻断上线。
    # 只拦 Tier1（纯数据校验，无网络依赖、无误报）；Tier2 源页面核对有 SPA/API 误报，
    # 保留为报告级提示。dry-run 模式下仅警告，不阻断（便于调试）。
    tier1_high = [
        s for s in audit_res["suspects"]
        if s.get("tier") == 1 and s.get("severity") == "high"
    ]
    if tier1_high:
        print("  ⛔ 门禁拦截：检测到 Tier1 high 级结构性数据错误，拒绝生成网页/上线")
        for s in tier1_high:
            print(f"    [{s['code']}] {s.get('source')} | {s.get('canonical')} | {s.get('msg')}")
        if args.dry_run:
            print("  [dry-run] 门禁仅警告，不阻断")
        else:
            return 2

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


def _verify_existing(data_dir: str) -> int:
    """纯只读验证磁盘上已有的 data/ 数据。（供本机 cron / 巡检消费云端提交的数据）

    零写入、零抓取——只跑审计门禁 + OpenRouter 二次验证，判断远端数据是否健康。
    返回 0 = 数据健康（Tier1 high = 0）；返回 2 = 检测到 Tier1 high 级结构性错误。
    """
    print("== 只读验证磁盘数据 ==")
    if not os.path.isdir(data_dir):
        print(f"  [error] 数据目录不存在: {data_dir}（请先 git pull 云端提交）")
        return 2

    sources = _load_yaml(os.path.join(CONFIG_DIR, "sources.yml")) or []

    print("== 数据核对（防幻觉自我检查）==")
    audit_res = audit.run(data_dir, sources_cfg=sources, write_audit=False)
    astats = audit_res["stats"]
    print(f"  可疑项 {astats['suspects']}（high {astats['high']} / med {astats['med']} / low {astats['low']}）")

    tier1_high = [
        s for s in audit_res["suspects"]
        if s.get("tier") == 1 and s.get("severity") == "high"
    ]
    if tier1_high:
        print("  ⛔ 门禁拦截：检测到 Tier1 high 级结构性数据错误")
        for s in tier1_high:
            print(f"    [{s['code']}] {s.get('source')} | {s.get('canonical')} | {s.get('msg')}")
        return 2

    print("== OpenRouter 二次验证 ==")
    or_verify = openrouter_verify.verify(data_dir, write_audit=False)
    os_ = or_verify.get("stats") or {}
    print(f"  OpenRouter parsed={os_.get('parsed',0)} ok={or_verify.get('ok')} suspects={os_.get('suspects',0)} high={os_.get('high',0)}")

    print("== 只读验证通过：云端数据健康 ==")
    return 0


if __name__ == "__main__":
    sys.exit(main())
