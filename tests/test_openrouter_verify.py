"""OpenRouter 二次验证模块单元测试（core/openrouter_verify.py）。"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict, List

import pytest

from core.openrouter_verify import _per_m, verify


class TestPerM:
    def test_basic_conversion(self) -> None:
        # 0.0000882 USD/token → 88.2 USD/1M tokens
        assert _per_m(0.0000882) == pytest.approx(88.2)

    def test_none_input(self) -> None:
        assert _per_m(None) is None

    def test_empty_string(self) -> None:
        assert _per_m("") is None

    def test_zero(self) -> None:
        assert _per_m(0) == 0.0

    def test_string_input(self) -> None:
        assert _per_m("0.000005") == pytest.approx(5.0)

    def test_invalid_string(self) -> None:
        assert _per_m("abc") is None


class TestVerify:
    @pytest.fixture
    def temp_dir(self) -> str:
        with tempfile.TemporaryDirectory() as d:
            yield d

    def _write_cache(self, dir_path: str, models: List[Dict[str, Any]]) -> str:
        path = os.path.join(dir_path, "openrouter_raw.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "fetched_at": "2026-08-20T10:00:00",
                    "url": "https://api.test",
                    "body": {"data": models},
                },
                f,
            )
        return path

    def test_perfect_match(self, temp_dir) -> None:
        """所有记录与缓存价格一致，应无 high 可疑项。"""
        self._write_cache(
            temp_dir,
            [
                {
                    "id": "test/model1",
                    "pricing": {"prompt": 0.000005, "completion": 0.000015},
                }
            ],
        )
        records = [
            {
                "source": "openrouter",
                "openrouter_id": "test/model1",
                "input": 5.0,
                "output": 15.0,
                "model_raw": "model1",
            }
        ]
        result = verify(data_dir=temp_dir, records=records)
        assert result["ok"] is True
        high = sum(1 for s in result["suspects"] if s.get("severity") == "high")
        assert high == 0

    def test_price_mismatch(self, temp_dir) -> None:
        """价格换算不一致应标记 OR_PRICE_MISMATCH（high）。"""
        self._write_cache(
            temp_dir,
            [
                {
                    "id": "test/model2",
                    "pricing": {"prompt": 0.000005, "completion": 0.000015},
                }
            ],
        )
        records = [
            {
                "source": "openrouter",
                "openrouter_id": "test/model2",
                "input": 10.0,  # 应为 5.0，故意写错
                "output": 15.0,
                "model_raw": "model2",
            }
        ]
        result = verify(data_dir=temp_dir, records=records)
        codes = [s["code"] for s in result["suspects"]]
        assert "OR_PRICE_MISMATCH" in codes

    def test_id_missing(self, temp_dir) -> None:
        """记录 openrouter_id 在缓存中不存在应标记 OR_ID_MISSING（high）。"""
        self._write_cache(
            temp_dir,
            [
                {
                    "id": "test/model3",
                    "pricing": {"prompt": 0.000005, "completion": 0.000015},
                }
            ],
        )
        records = [
            {
                "source": "openrouter",
                "openrouter_id": "test/nonexistent",
                "input": 5.0,
                "output": 15.0,
                "model_raw": "nonexistent",
            }
        ]
        result = verify(data_dir=temp_dir, records=records)
        codes = [s["code"] for s in result["suspects"]]
        assert "OR_ID_MISSING" in codes

    def test_no_cache_file(self, temp_dir) -> None:
        """缓存文件不存在时返回 ok=False & error=missing_cache。"""
        result = verify(data_dir=temp_dir)
        assert result["ok"] is False
        assert result.get("error") == "missing_cache"

    def test_bad_cache_structure(self, temp_dir) -> None:
        """缓存 JSON 结构无效（无 data 列表）时返回 error=bad_cache。"""
        path = os.path.join(temp_dir, "openrouter_raw.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"fetched_at": "x", "body": {"data": "not-a-list"}}, f)
        result = verify(data_dir=temp_dir)
        assert result["ok"] is False
        assert result.get("error") == "bad_cache"

    def test_old_cache_format(self, temp_dir) -> None:
        """兼容旧格式：direct body（无 wrapper）。"""
        path = os.path.join(temp_dir, "openrouter_raw.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {"data": [{"id": "test/old", "pricing": {"prompt": 0.0001, "completion": 0.0002}}]},
                f,
            )
        records = [
            {
                "source": "openrouter",
                "openrouter_id": "test/old",
                "input": 100.0,
                "output": 200.0,
                "model_raw": "old",
            }
        ]
        result = verify(data_dir=temp_dir, records=records)
        assert result["ok"] is True

    def test_writes_reports(self, temp_dir) -> None:
        """验证过程应写出 openrouter_verify.json 与 .md。"""
        self._write_cache(temp_dir, [])
        verify(data_dir=temp_dir, records=[])
        assert os.path.exists(os.path.join(temp_dir, "openrouter_verify.json"))
        assert os.path.exists(os.path.join(temp_dir, "openrouter_verify.md"))
