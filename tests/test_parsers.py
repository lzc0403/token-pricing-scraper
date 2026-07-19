"""Parser / 匹配 单元测试（离线，基于 tests/fixtures 已保存的真实 HTML）。

运行：
    pytest tests/test_parsers.py
"""

from __future__ import annotations

import os
import sys

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from main import _get_scraper_class  # noqa: E402
from core import currency, matcher  # noqa: E402
from scrapers.base import clean_price  # noqa: E402

FIX_DIR = os.path.join(ROOT, "tests", "fixtures")
SOURCES = {s["id"]: s for s in yaml.safe_load(open(os.path.join(ROOT, "config", "sources.yml")))}
MODELS_CFG = yaml.safe_load(open(os.path.join(ROOT, "config", "models.yml")))

# 每个源对应的 fixture 文件（kimi 为多 URL）
FIXTURE_MAP = {
    "aliyun": ["aliyun.html"],
    "volcengine": ["volcengine.html"],
    "tencent": ["tencent.html"],
    "bigmodel": ["bigmodel.html"],
    "deepseek": ["deepseek.html"],
    "minimax": ["minimax.html"],
    "kimi": ["kimi1.html", "kimi2.html", "kimi3.html"],
    "modelmesh": ["modelmesh.html"],
}


def _load(name: str) -> str:
    with open(os.path.join(FIX_DIR, name), "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _parse_source(sid: str):
    src = SOURCES[sid]
    cls = _get_scraper_class(src["parser"])
    inst = cls(src)
    recs = []
    for fn in FIXTURE_MAP[sid]:
        recs.extend(inst.parse(_load(fn)))
    return [r for r in recs if r and r.get("model_raw")]


def _all_records():
    recs = []
    for sid in FIXTURE_MAP:
        recs.extend(_parse_source(sid))
    return recs


def test_deepseek_parses_v4_models():
    recs = _parse_source("deepseek")
    models = {r["model_raw"] for r in recs}
    assert "deepseek-v4-flash" in models
    assert "deepseek-v4-pro" in models


def test_tencent_mainland_only():
    recs = _parse_source("tencent")
    assert recs, "tencent 应解析出记录"
    # 新加坡 / 海外区域不应出现（区域过滤）
    joined = " ".join(r["model_raw"] for r in recs)
    assert "新加坡" not in joined


def test_aliyun_qwen37_china_mainland():
    recs = _parse_source("aliyun")
    models = {r["model_raw"] for r in recs}
    assert models == {"Qwen3.7-Max", "Qwen3.7-Plus"}
    max_rec = next(r for r in recs if r["model_raw"] == "Qwen3.7-Max")
    # Hologres 托管模型：元/千 Token -> 元/百万 Token（×1000）
    assert max_rec["input"] == 14.4
    assert max_rec["output"] == 43.2
    # 缓存命中只取「隐式缓存命中」列（0.00288 元/千 -> 2.88 元/百万）
    assert max_rec["cache_hit"] == 2.88
    assert max_rec["currency"] == "CNY"
    plus_rec = next(r for r in recs if r["model_raw"] == "Qwen3.7-Plus")
    # Qwen3.7-Plus 取基础阶梯 ≤256K：0.00240/0.00960/0.00048 元/千 -> ×1000
    assert plus_rec["input"] == 2.4
    assert plus_rec["output"] == 9.6
    assert plus_rec["cache_hit"] == 0.48


def test_volcengine_doubao_rows():
    recs = _parse_source("volcengine")
    assert recs, "volcengine 应解析出记录"
    models = {r["model_raw"] for r in recs}
    assert any(m.lower().startswith("doubao") or "seedance" in m.lower() for m in models)


def test_bigmodel_glm():
    recs = _parse_source("bigmodel")
    models = {r["model_raw"] for r in recs}
    # 营销后缀「新品」必须被剥离，否则 matcher 精确匹配会失败
    assert "GLM-5.2" in models
    assert "GLM-5.2 新品" not in models
    assert "GLM-5.1" in models
    glm52 = next(r for r in recs if r["model_raw"] == "GLM-5.2")
    assert glm52["input"] == 8.0
    assert glm52["output"] == 28.0


def test_minimax_m27():
    recs = _parse_source("minimax")
    models = {r["model_raw"] for r in recs}
    assert "MiniMax-M2.7" in models
    # M3 系列（py-4 行）也应被抓取，且取折后实价
    assert "MiniMax-M3" in models
    m3 = [r for r in recs if r["model_raw"] == "MiniMax-M3"]
    # 基础档 ≤512K：输入 2.1 / 输出 8.4 / 缓存读 0.42（元/百万 tokens，折后实价）
    base = next(r for r in m3 if r["input"] == 2.1)
    assert base["output"] == 8.4
    assert base["cache_hit"] == 0.42


def test_kimi_k26():
    recs = _parse_source("kimi")
    models = {r["model_raw"] for r in recs}
    assert "kimi-k2.6" in models


def test_modelmesh_cards():
    recs = _parse_source("modelmesh")
    assert len(recs) > 10, "modelmesh 应解析出大量卡片"
    models = {r["model_raw"] for r in recs}
    for expected in ["DeepSeek-V4-Pro", "GLM-5.2", "Kimi K2.6", "MiniMax M2.7", "Qwen3.7-Max"]:
        assert expected in models, f"modelmesh 缺少 {expected}"


def test_watchlist_all_configured_targets_matched():
    recs = _all_records()
    # matcher-only synthetic record：验证配置目标覆盖，不伪装成官方 HTML fixture。
    recs.append({"model_raw": "seedance-2.0"})
    recs.append({"model_raw": "kimi-k3"})
    _, watch = matcher.build_watchlist(recs, MODELS_CFG)
    canons = {r["canonical"] for r in watch}
    targets = {m["canonical"] for m in MODELS_CFG["models"]}
    assert targets <= canons, f"未命中目标模型: {targets - canons}"


# --------------------------------------------------------------------------- #
# 边界与健壮性（需求 6）：价格含千分位、aliyun 回退、未知货币 / None / 非数字 context
# --------------------------------------------------------------------------- #
def test_clean_price_thousands_separator():
    """千分位逗号应被剔除，不报错。"""
    assert clean_price("1,234.5") == 1234.5
    assert clean_price("¥ 1,000 元") == 1000.0
    assert clean_price("2,000.00") == 2000.0


def test_aliyun_overseas_excluded_and_implicit_cache_only():
    """新加坡等海外区域不应出现；缓存命中只取隐式缓存命中，不含显式缓存。"""
    recs = _parse_source("aliyun")
    # 仅含中国内地模型
    assert {r["model_raw"] for r in recs} == {"Qwen3.7-Max", "Qwen3.7-Plus"}
    joined = " ".join(r["model_raw"] for r in recs)
    assert "新加坡" not in joined
    # 隐式缓存命中价已写入 cache_hit（元/百万 Token）
    max_rec = next(r for r in recs if r["model_raw"] == "Qwen3.7-Max")
    assert max_rec["cache_hit"] == 2.88
    # 显式缓存命中（0.00144 元/千 -> 1.44 元/百万）未被采用
    assert max_rec["cache_hit"] != 1.44


def test_get_rate_falls_back_on_empty_or_bad_env(monkeypatch):
    """GitHub 未配置 secret 时 USD_CNY_RATE 被求值为空字符串 ''，必须回退 7.2。"""
    # 空字符串（CI 未配 secret 的真实情况）
    monkeypatch.setenv("USD_CNY_RATE", "")
    assert currency.get_rate() == 7.2
    # 变量不存在
    monkeypatch.delenv("USD_CNY_RATE", raising=False)
    assert currency.get_rate() == 7.2
    # 非数字
    monkeypatch.setenv("USD_CNY_RATE", "not-a-number")
    assert currency.get_rate() == 7.2
    # 合法值应被采用
    monkeypatch.setenv("USD_CNY_RATE", "7.8")
    assert currency.get_rate() == 7.8

def test_robustness_unknown_currency_and_missing_fields():
    """未知货币 / cache_hit=None / context 非数字字符串 不应导致崩溃。"""
    # 货币换算对未知货币与 None 的健壮性（返回原值 / None，不抛异常）
    assert currency.to_rmb(5.0, "EUR", 7.2) == 5.0
    assert currency.to_rmb(None, "USD", 7.2) is None
    assert currency.get_rate() == 7.2  # 默认汇率 7.2

    # 构造一条异常记录，跑完整 enrich + store 流程确认不崩
    rec = {
        "source": "unit",
        "model_raw": "weird-model",
        "input": 1.5,
        "output": None,
        "cache_hit": None,
        "context": "not-a-number-256K",
        "condition": "x",
        "unit": "1M tokens",
        "currency": "EUR",  # 未知货币
    }
    currency.enrich([rec])
    assert rec["input_rmb"] == 1.5  # 未知货币原值
    assert rec["output_rmb"] is None
    # store 写出不应崩溃
    import tempfile
    import json
    from core import store

    td = tempfile.mkdtemp()
    paths = store.write_outputs([rec], td)
    written = json.load(open(paths["prices.json"], encoding="utf-8"))
    assert written[0]["context"] == "not-a-number-256K"


def test_matcher_no_false_positive_glm5():
    """非目标模型 GLM-5 不应被误匹配为 GLM-5.1（需求#3：非目标不进 watchlist）。"""
    assert matcher.match("GLM-5", MODELS_CFG) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("qwen3.7-max", "Qwen3.7 Max"),
        ("Qwen3.7-Plus", "Qwen3.7 Plus"),
        ("doubao-seed-2.1-pro", "Doubao Seed 2.1 Pro"),
        ("doubao-seed-2.1-turbo", "Doubao Seed 2.1 Turbo"),
        ("kimi-k2.7-code", "Kimi K2.7 Code"),
        ("MiniMax-M3", "MiniMax M3"),
        ("seedance-2.0", "Seedance 2.0"),
    ],
)
def test_matcher_safe_positive_matrix(raw, expected):
    assert matcher.match(raw, MODELS_CFG) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "doubao-seed-2.0-pro",
        "doubao-seed-2.0-code",
        "doubao-seed-2.1-turbo",
    ],
)
def test_doubao_text_never_matches_seedance(raw):
    assert matcher.match(raw, MODELS_CFG) != "Seedance 2.0"


def test_qwen_max_plus_are_distinct():
    assert matcher.match("qwen3.7-max", MODELS_CFG) != matcher.match("qwen3.7-plus", MODELS_CFG)
