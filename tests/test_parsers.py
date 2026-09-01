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
    "kimi_ai": ["kimi_ai.html"],
    "modelmesh": ["modelmesh.html"],
    "tencent_cn": ["tencent_cn.html"],
    "aliyun_bailian": ["aliyun_bailian.json"],
    "volcengine_intl": ["volcengine_intl.html"],
    "zai": ["zai.html"],
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


def test_deepseek_cache_peak_dual():
    """DeepSeek 官网改版后：缓存命中与输入/输出一样分「空闲/高峰」双档。"""
    recs = _parse_source("deepseek")
    flash = next(r for r in recs if r["model_raw"] == "deepseek-v4-flash")
    assert flash.get("condition") == "峰谷计费"
    # 输入：空闲 1.5 / 高峰 3.0（元/百万tokens，flash 档）
    assert flash["peak_input_low"] == 1.5
    assert flash["peak_input_high"] == 3.0
    # 缓存命中同样双档：空闲 0.05 / 高峰 0.10
    assert flash["peak_cache_low"] == 0.05
    assert flash["peak_cache_high"] == 0.10
    assert flash["cache_hit"] == 0.1  # 主字段 = 高峰档（官网基准价）


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


def test_kimi_ai_english_header():
    """kimi_ai（国际站 USD）：英文表头（Model / Input Price (Cache Hit) 等）须正确解析。"""
    recs = _parse_source("kimi_ai")
    assert recs, "kimi_ai 应解析出记录"
    by_model = {r["model_raw"]: r for r in recs}
    k3 = by_model.get("kimi-k3")
    assert k3, "kimi-k3 应被解析"
    # USD 定价：缓存命中 $0.30 / 未命中 $3.00 / 输出 $15.00
    assert k3["cache_hit"] == 0.3
    assert k3["input"] == 3.0
    assert k3["output"] == 15.0
    assert k3["context"] == "1,048,576 tokens"


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
    recs.append({"model_raw": "qwen3.8-max"})
    recs.append({"model_raw": "GLM-5.3"})
    recs.append({"model_raw": "GLM-5.3-Flash"})
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
    """GitHub 未配置 secret 时 USD_CNY_RATE 被求值为空字符串 ''，必须回退 7.0。"""
    # 空字符串（CI 未配 secret 的真实情况）
    monkeypatch.setenv("USD_CNY_RATE", "")
    assert currency.get_rate() == 7.0
    # 变量不存在
    monkeypatch.delenv("USD_CNY_RATE", raising=False)
    assert currency.get_rate() == 7.0
    # 非数字
    monkeypatch.setenv("USD_CNY_RATE", "not-a-number")
    assert currency.get_rate() == 7.0
    # 合法值应被采用
    monkeypatch.setenv("USD_CNY_RATE", "7.8")
    assert currency.get_rate() == 7.8

def test_robustness_unknown_currency_and_missing_fields():
    """未知货币 / cache_hit=None / context 非数字字符串 不应导致崩溃。"""
    # 货币换算对未知货币与 None 的健壮性（返回原值 / None，不抛异常）
    assert currency.to_rmb(5.0, "EUR", 7.0) == 5.0
    assert currency.to_rmb(None, "USD", 7.0) is None
    assert currency.get_rate() == 7.0  # 默认汇率 7.0

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


def test_tencent_cn_complete_table_overrides_overview():
    """腾讯云国内站应取完整定价表（table #1），避免概览表低价覆盖。"""
    recs = _parse_source("tencent_cn")
    glm52 = next(r for r in recs if r["model_raw"] == "GLM-5.2")
    assert glm52["input"] == 10.254
    assert glm52["output"] == 32.2282
    assert glm52["cache_hit"] == 1.9044
    k3 = next(r for r in recs if r["model_raw"] == "Kimi K3")
    assert k3["input"] == 21.974
    assert k3["output"] == 109.869
    assert k3["cache_hit"] == 2.197


def test_tencent_cn_conditions_for_deepseek():
    """DeepSeek 应同时解析出「原厂直供」与「腾讯云自建」两档。"""
    recs = _parse_source("tencent_cn")
    flash = [r for r in recs if r["model_raw"] == "DeepSeek-V4-Flash"]
    assert len(flash) == 2
    conds = {r["condition"]: r for r in flash}
    assert "原厂直供" in conds
    assert "腾讯云自建" in conds
    assert conds["原厂直供"]["cache_hit"] == 0.02
    assert conds["腾讯云自建"]["cache_hit"] == 0.2
    pro = [r for r in recs if r["model_raw"] == "DeepSeek-V4-Pro"]
    assert len(pro) == 2
    pro_cond = {r["condition"]: r for r in pro}
    assert pro_cond["原厂直供"]["input"] == 3.0
    assert pro_cond["腾讯云自建"]["input"] == 12.0


def test_tencent_cn_multiword_model_name_preserved():
    """「Kimi K3」等多词模型名不可被截断为「Kimi」。"""
    recs = _parse_source("tencent_cn")
    models = {r["model_raw"] for r in recs}
    assert "Kimi K3" in models
    assert "Kimi K2.7 Code" in models
    assert "Kimi" not in models


def test_bailian_cache_hit_is_20pct_of_input():
    """百炼缓存命中价按输入单价 ×20% 计算。"""
    recs = _parse_source("aliyun_bailian")
    flash = next(r for r in recs if r["model_raw"] == "deepseek-v4-flash")
    assert flash["input"] == 1.0
    assert flash["cache_hit"] == 0.2
    k3 = next(r for r in recs if r["model_raw"] == "kimi-k3")
    assert k3["input"] == 20.0
    assert k3["cache_hit"] == 4.0


def test_bailian_excludes_overseas_regions():
    """百炼应跳过「国际 / 美国 / 日本」等区域行。"""
    recs = _parse_source("aliyun_bailian")
    joined = " ".join(r.get("model_raw", "") for r in recs)
    assert "-us" not in joined
    # 没有显式的区域名残留，进一步断言目标模型存在
    assert any(r["model_raw"] == "deepseek-v4-pro" for r in recs)


def test_bailian_target_models_parsed():
    """百炼应命中目标模型家族：deepseek / glm / kimi / minimax。"""
    recs = _parse_source("aliyun_bailian")
    models = {r["model_raw"] for r in recs}
    for expected in ["deepseek-v4-flash", "deepseek-v4-pro", "deepseek-v3.2",
                     "kimi-k3", "kimi-k2.6", "kimi-k2.7-code",
                     "glm-5.2", "glm-5.1", "minimax-m3", "minimax-m2.7"]:
        assert expected in models, f"aliyun_bailian 缺少 {expected}"


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


def test_volcengine_intl_deepseek_glm_only():
    """火山云海外只收录 DeepSeek + GLM 系列。"""
    recs = _parse_source("volcengine_intl")
    assert recs, "volcengine_intl 应解析出记录"
    models = {r["model_raw"] for r in recs}
    # 目标模型全部命中
    for expected in ["deepseek-v4-pro", "deepseek-v4-flash", "deepseek-v3.2",
                     "glm-5.2", "glm-4.7"]:
        assert expected in models, f"volcengine_intl 缺少 {expected}"
    # 非 DeepSeek/GLM 模型被过滤
    assert not any(m.startswith("seed") for m in models), "seed 系列不应出现"
    assert not any(m.startswith("dola") for m in models), "dola 系列不应出现"
    assert not any(m.startswith("gpt-oss") for m in models), "gpt-oss 不应出现"


def test_volcengine_intl_date_suffix_stripped():
    """日期快照后缀（-260425/-251201/-260617/-251222）应被剥离归一。"""
    recs = _parse_source("volcengine_intl")
    models = {r["model_raw"] for r in recs}
    # 归一后不应含日期后缀
    assert "deepseek-v4-pro-260425" not in models
    assert "deepseek-v4-flash-260425" not in models
    assert "deepseek-v3-2-251201" not in models
    assert "glm-5-2-260617" not in models
    assert "glm-4-7-251222" not in models
    # 应为无后缀基准名（版本号「-」已转「.」）
    assert "deepseek-v4-pro" in models
    assert "deepseek-v3.2" in models
    assert "glm-5.2" in models
    assert "glm-4.7" in models


def test_volcengine_intl_ga_suffix_dedup():
    """GA 日期后缀（-ga-260731）应剥离，并与普通快照归一到同一基准名。"""
    recs = _parse_source("volcengine_intl")
    models = {r["model_raw"] for r in recs}
    # GA 版与普通快照都归一到 deepseek-v4-flash（去重后仅一条）
    assert "deepseek-v4-flash-ga" not in models, "GA 后缀未剥离"
    assert "deepseek-v4-flash-ga-260731" not in models
    flash = [r for r in recs if r["model_raw"] == "deepseek-v4-flash"]
    assert len(flash) == 1, f"flash 应去重为 1 条，实为 {len(flash)}"
    assert flash[0]["input"] == 0.14 and flash[0]["output"] == 0.28


def test_volcengine_intl_deepseek_condition():
    """DeepSeek 行应标「火山引擎自部署」condition。"""
    recs = _parse_source("volcengine_intl")
    for r in recs:
        if r["model_raw"].startswith("deepseek"):
            assert r["condition"] == "火山引擎自部署", \
                f"DeepSeek 行 condition 应为「火山引擎自部署」，实为 {r['condition']}"
    # GLM 行 condition 应为 None
    for r in recs:
        if r["model_raw"].startswith("glm"):
            assert r["condition"] is None, \
                f"GLM 行 condition 应为 None，实为 {r['condition']}"


def test_volcengine_intl_currency_usd():
    """火山云海外为 USD 结算。"""
    recs = _parse_source("volcengine_intl")
    assert all(r["currency"] == "USD" for r in recs)


def test_volcengine_intl_tier_dedup_first_row():
    """分层定价的模型（如 deepseek-v3-2）只保留首行（基准档）。"""
    recs = _parse_source("volcengine_intl")
    v32 = [r for r in recs if r["model_raw"] == "deepseek-v3.2"]
    assert len(v32) == 1, f"deepseek-v3.2 应只保留首行，实有 {len(v32)} 条"
    # 首行 = [0, 32] 档：输入 0.28 / 输出 0.42 / 缓存 0.056
    assert v32[0]["input"] == 0.28
    assert v32[0]["output"] == 0.42
    assert v32[0]["cache_hit"] == 0.056


def test_volcengine_intl_skips_batch_and_video_tables():
    """应跳过「批量推理」表和「视频生成」表，只取在线推理标准表。"""
    recs = _parse_source("volcengine_intl")
    # 批量推理表的 glm-4-7 价是 0.3/1.1，在线表是 0.6/2.2；应取在线表
    glm47 = next(r for r in recs if r["model_raw"] == "glm-4.7")
    assert glm47["input"] == 0.6
    assert glm47["output"] == 2.2
    # 视频表（dreamina-seedance / seedance）不应出现
    assert not any("seedance" in r["model_raw"].lower() for r in recs)


# --------------------------------------------------------------------------- #
# 智谱 Z.ai 海外站（USD）
# --------------------------------------------------------------------------- #
def test_zai_text_models_parsed():
    """Z.ai 应解析出 GLM 文本模型系列（USD）。"""
    recs = _parse_source("zai")
    assert recs, "zai 应解析出记录"
    models = {r["model_raw"] for r in recs}
    for expected in ["GLM-5.2", "GLM-5.1", "GLM-5", "GLM-5-Turbo",
                     "GLM-4.7", "GLM-4.6", "GLM-4.5", "GLM-4.5-Air"]:
        assert expected in models, f"zai 缺少 {expected}"


def test_zai_vision_models_excluded():
    """GLM-5V / GLM-4.6V / GLM-OCR 等视觉模型应被过滤。"""
    recs = _parse_source("zai")
    models = {r["model_raw"] for r in recs}
    assert not any("V-Turbo" in m or "4.6V" in m or "4.5V" in m for m in models), \
        "视觉模型不应出现"
    assert not any("ocr" in m.lower() for m in models), "OCR 模型不应出现"


def test_zai_currency_usd():
    """Z.ai 全站 USD 结算。"""
    recs = _parse_source("zai")
    assert recs
    assert all(r["currency"] == "USD" for r in recs)


def test_zai_glm52_pricing():
    """GLM-5.2 定价应为 $1.4/$4.4，缓存 $0.26。"""
    recs = _parse_source("zai")
    glm52 = next(r for r in recs if r["model_raw"] == "GLM-5.2")
    assert glm52["input"] == 1.4
    assert glm52["output"] == 4.4
    assert glm52["cache_hit"] == 0.26


def test_zai_condition_none():
    """Z.ai 是智谱官方国际站原价，无来源类型区分，condition 应为 None。"""
    recs = _parse_source("zai")
    for r in recs:
        assert r["condition"] is None, f"{r['model_raw']} condition 应为 None"
