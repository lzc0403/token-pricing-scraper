"""新模型雷达测试（纯 fixture，不读真实 data/、不发网络请求）。

铁律：数据依赖型测试必须自造数据，读真实 data/ 在 CI 干净环境会 flaky。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

from core import model_radar

NOW = datetime(2026, 9, 9, tzinfo=timezone.utc)


def _ts(days_ago: int) -> int:
    return int((NOW - timedelta(days=days_ago)).timestamp())


def _model(mid, name, *, days_ago=5, prompt="0.00001", completion="0.00003",
           modalities=None, created=None):
    return {
        "id": mid,
        "name": name,
        "created": created if created is not None else _ts(days_ago),
        "context_length": 1048576,
        "architecture": {"output_modalities": modalities or ["text"]},
        "pricing": {
            "prompt": prompt,
            "completion": completion,
            "input_cache_read": "0.000001",
        },
    }


def _write_raw(tmp_path, models):
    raw = {
        "fetched_at": NOW.isoformat(),
        "url": "https://openrouter.ai/api/v1/models",
        "body": {"data": models},
    }
    p = tmp_path / "openrouter_raw.json"
    p.write_text(json.dumps(raw), encoding="utf-8")
    return str(tmp_path)


def _write_cfg(tmp_path, text):
    (tmp_path / "model_radar.yml").write_text(text, encoding="utf-8")


BASE_CFG = """
enabled: true
lookback_days: 60
flagship_ratio: 0.8
min_input_usd: 0.1
providers: [openai, anthropic, deepseek, moonshotai, z-ai]
families:
  openai: OpenAI
  anthropic: Anthropic
  deepseek: DeepSeek
  moonshotai: Kimi
  z-ai: GLM
domestic_providers: [deepseek, moonshotai, z-ai]
noise_patterns: [mini, nano, lite, free, distill, embed, vision, preview, beta, exp]
"""


def test_new_flagship_is_reported(tmp_path):
    """未登记的新旗舰：必须进候选且判为 flagship。"""
    data = _write_raw(tmp_path, [
        _model("openai/gpt-6-astra", "OpenAI: GPT-6 Astra", days_ago=6,
               prompt="0.00001", completion="0.00005"),
        _model("openai/gpt-5", "OpenAI: GPT-5", days_ago=900,
               prompt="0.00000125", completion="0.00001"),
    ])
    _write_cfg(tmp_path, BASE_CFG)
    res = model_radar.scan(data, str(tmp_path), today=NOW)

    ids = [c["id"] for c in res["candidates"]]
    assert "openai/gpt-6-astra" in ids
    astra = next(c for c in res["candidates"] if c["id"] == "openai/gpt-6-astra")
    assert astra["flagship"] is True
    assert astra["input_usd_per_m"] == 10.0
    assert astra["family"] == "OpenAI"
    assert astra["region"] == "overseas"
    assert astra["created"] == "2026-09-03"
    assert res["flagship_count"] == 1


def test_registered_model_not_reported(tmp_path):
    """已登记（写进 prices.json / 白名单）的不再报。"""
    data = _write_raw(tmp_path, [
        _model("openai/gpt-6-astra", "OpenAI: GPT-6 Astra", days_ago=6),
    ])
    (tmp_path / "prices.json").write_text(json.dumps([
        {"openrouter_id": "openai/gpt-6-astra", "canonical": "GPT-6 Astra", "source": "openai"},
    ]), encoding="utf-8")
    _write_cfg(tmp_path, BASE_CFG)
    res = model_radar.scan(data, str(tmp_path), today=NOW)
    assert res["candidates"] == []


def test_noise_and_free_and_old_are_filtered(tmp_path):
    """mini/nano/lite、免费、过期、非文本模型一律不进候选。"""
    data = _write_raw(tmp_path, [
        _model("openai/gpt-6-astra-mini", "OpenAI: GPT-6 Astra Mini", days_ago=3),
        _model("openai/gpt-6-astra-free", "OpenAI: GPT-6 Astra (free)", days_ago=3),
        _model("openai/gpt-6-old", "OpenAI: GPT-6 Old", days_ago=400),
        _model("openai/gpt-6-vision", "OpenAI: GPT-6 Vision", days_ago=3,
               modalities=["image"]),
        _model("openai/gpt-6-astra", "OpenAI: GPT-6 Astra", days_ago=3),
    ])
    _write_cfg(tmp_path, BASE_CFG)
    res = model_radar.scan(data, str(tmp_path), today=NOW)
    assert [c["id"] for c in res["candidates"]] == ["openai/gpt-6-astra"]


def test_variant_entries_of_known_models_are_skipped(tmp_path):
    """已收录模型的 `:batch` 变体与 `-0731` 日期快照版不算新模型。"""
    data = _write_raw(tmp_path, [
        _model("z-ai/glm-5.3:batch", "Z.AI: GLM-5.3 (batch)", days_ago=3),
        _model("deepseek/deepseek-v4-flash-0731", "DeepSeek: DeepSeek V4 Flash 0731", days_ago=3),
        _model("openai/gpt-6-astra", "OpenAI: GPT-6 Astra", days_ago=3),
    ])
    (tmp_path / "prices.json").write_text(json.dumps([
        {"openrouter_id": "z-ai/glm-5.3", "canonical": "GLM-5.3", "source": "openrouter"},
        {"openrouter_id": "deepseek/deepseek-v4-flash", "canonical": "DeepSeek V4 Flash",
         "source": "openrouter"},
    ]), encoding="utf-8")
    _write_cfg(tmp_path, BASE_CFG)
    res = model_radar.scan(data, str(tmp_path), today=NOW)
    assert [c["id"] for c in res["candidates"]] == ["openai/gpt-6-astra"]


def test_secondary_tier_not_flagship(tmp_path):
    """同厂商新上的低价档：进候选但判为「新增档位」，不是旗舰。"""
    data = _write_raw(tmp_path, [
        _model("anthropic/claude-opus-5.5", "Anthropic: Claude Opus 5.5", days_ago=4,
               prompt="0.00001", completion="0.00005"),
        _model("anthropic/claude-opus-5.5-lite", "Anthropic: Claude Opus 5.5 Lite", days_ago=4),
        _model("anthropic/claude-haiku-5.5", "Anthropic: Claude Haiku 5.5", days_ago=4,
               prompt="0.000001", completion="0.000005"),
    ])
    _write_cfg(tmp_path, BASE_CFG)
    res = model_radar.scan(data, str(tmp_path), today=NOW)
    got = {c["id"]: c["flagship"] for c in res["candidates"]}
    assert got["anthropic/claude-opus-5.5"] is True
    assert got["anthropic/claude-haiku-5.5"] is False
    assert model_radar.flagships(res)[0]["id"] == "anthropic/claude-opus-5.5"


def test_disabled_returns_empty(tmp_path):
    data = _write_raw(tmp_path, [_model("openai/gpt-6-astra", "OpenAI: GPT-6 Astra")])
    _write_cfg(tmp_path, "enabled: false\n")
    res = model_radar.scan(data, str(tmp_path), today=NOW)
    assert res["enabled"] is False
    assert res["candidates"] == []


def test_unknown_provider_ignored(tmp_path):
    """不在关注厂商列表里的 provider 不报。"""
    data = _write_raw(tmp_path, [_model("acme/super-llm", "Acme: Super LLM", days_ago=2)])
    _write_cfg(tmp_path, BASE_CFG)
    res = model_radar.scan(data, str(tmp_path), today=NOW)
    assert res["candidates"] == []


def test_missing_raw_file_is_safe(tmp_path):
    """原始缓存缺失（源失败）时雷达不炸，返回空结果。"""
    _write_cfg(tmp_path, BASE_CFG)
    res = model_radar.scan(str(tmp_path), str(tmp_path), today=NOW)
    assert res["scanned"] == 0
    assert res["candidates"] == []


def test_write_output_and_yaml_snippet(tmp_path):
    """候选能落盘，且生成可直接粘贴的 new_models.yml 片段。"""
    data = _write_raw(tmp_path, [
        _model("deepseek/deepseek-v5", "DeepSeek: DeepSeek V5", days_ago=2,
               prompt="0.000004", completion="0.000012"),
    ])
    _write_cfg(tmp_path, BASE_CFG)
    res = model_radar.scan(data, str(tmp_path), today=NOW)
    path = model_radar.write_output(data, res)
    assert path and os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        saved = json.load(f)
    assert saved["flagship_count"] == 1

    yml = model_radar.suggested_yaml(res)
    assert "- canonical: DeepSeek V5" in yml
    assert "region: domestic" in yml          # deepseek 属国内厂商
    assert "deepseek/deepseek-v5" in yml      # 别名里带 OpenRouter id
    assert "status: tracking" in yml          # 待人工确认，不自动 active


def test_report_build_includes_radar_section(tmp_path):
    """main.py 接线守门：雷达结果必须同时进 REPORT.md 与 issue_body.md。"""
    from core import report

    data = _write_raw(tmp_path, [
        _model("openai/gpt-6-astra", "OpenAI: GPT-6 Astra", days_ago=6,
               prompt="0.00001", completion="0.00005"),
    ])
    _write_cfg(tmp_path, BASE_CFG)
    radar = model_radar.scan(data, str(tmp_path), today=NOW)

    md, issue = report.build_report([], [], {}, generated_at="2026-09-09 00:00:00", radar=radar)
    assert "新模型雷达" in md
    assert "openai/gpt-6-astra" in md
    assert "新模型雷达" in issue          # 无价格变动也要能触发告警 issue
    assert "待登记 YAML" in issue


def test_report_section_has_table_and_yaml(tmp_path):
    data = _write_raw(tmp_path, [
        _model("openai/gpt-6-astra", "OpenAI: GPT-6 Astra", days_ago=6,
               prompt="0.00001", completion="0.00005"),
    ])
    _write_cfg(tmp_path, BASE_CFG)
    res = model_radar.scan(data, str(tmp_path), today=NOW)
    md = model_radar.report_section(res)
    assert "新模型雷达" in md
    assert "openai/gpt-6-astra" in md
    assert "疑似旗舰" in md
    assert "```yaml" in md

    empty = model_radar.report_section({"scanned": 100, "lookback_days": 60, "candidates": []})
    assert "没有" in empty
