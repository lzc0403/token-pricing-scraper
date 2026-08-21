"""存储模块单元测试（core/store.py）：compare_previous / _mark_lowest / write_outputs。"""

from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, List

import pytest

from core.store import _mark_lowest, compare_previous, write_outputs


def _write_prices(dir_path: str, records: List[Dict[str, Any]], name: str = "prices.json") -> str:
    import json

    path = os.path.join(dir_path, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f)
    return path


class TestComparePrevious:
    def test_no_previous_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            current = _write_prices(d, [{"canonical": "A", "source": "s1", "input": 1, "output": 2}])
            deltas = compare_previous(current, os.path.join(d, "nonexistent.json"))
            assert deltas == []

    def test_no_change(self) -> None:
        records = [{"canonical": "A", "source": "s1", "input": 1.0, "output": 2.0, "model_raw": "a"}]
        with tempfile.TemporaryDirectory() as d:
            prev = _write_prices(d, records)
            curr = _write_prices(d, records)
            deltas = compare_previous(curr, prev)
            assert deltas == []

    def test_price_change(self) -> None:
        previous = [{"canonical": "A", "source": "s1", "input": 1.0, "output": 2.0, "model_raw": "a"}]
        current = [{"canonical": "A", "source": "s1", "input": 1.5, "output": 2.0, "model_raw": "a"}]
        with tempfile.TemporaryDirectory() as d:
            prev = _write_prices(d, previous, "prev.json")
            curr = _write_prices(d, current, "curr.json")
            deltas = compare_previous(curr, prev)
            assert len(deltas) == 1
            assert deltas[0]["field"] == "input"
            assert deltas[0]["old"] == 1.0
            assert deltas[0]["new"] == 1.5
            assert deltas[0]["canonical"] == "A"
            assert deltas[0]["source"] == "s1"

    def test_new_model_not_in_delta(self) -> None:
        """新出现的模型不在历史中，不应出现在 delta 中。"""
        previous = [{"canonical": "A", "source": "s1", "input": 1.0, "output": 2.0, "model_raw": "a"}]
        current = [
            {"canonical": "A", "source": "s1", "input": 1.0, "output": 2.0, "model_raw": "a"},
            {"canonical": "B", "source": "s2", "input": 3.0, "output": 4.0, "model_raw": "b"},
        ]
        with tempfile.TemporaryDirectory() as d:
            prev = _write_prices(d, previous)
            curr = _write_prices(d, current)
            deltas = compare_previous(curr, prev)
            assert len(deltas) == 0

    def test_output_change_only(self) -> None:
        previous = [{"canonical": "A", "source": "s1", "input": 1.0, "output": 2.0, "model_raw": "a"}]
        current = [{"canonical": "A", "source": "s1", "input": 1.0, "output": 2.5, "model_raw": "a"}]
        with tempfile.TemporaryDirectory() as d:
            prev = _write_prices(d, previous, "prev.json")
            curr = _write_prices(d, current, "curr.json")
            deltas = compare_previous(curr, prev)
            assert len(deltas) == 1
            assert deltas[0]["field"] == "output"


class TestMarkLowest:
    def test_single_source(self) -> None:
        records = [{"canonical": "A", "source": "s1", "input_rmb": 10.0}]
        result = _mark_lowest(records)
        assert result[0]["is_lowest_input"] == "yes"

    def test_multiple_sources(self) -> None:
        records = [
            {"canonical": "A", "source": "s1", "input_rmb": 10.0},
            {"canonical": "A", "source": "s2", "input_rmb": 5.0},
        ]
        result = _mark_lowest(records)
        assert result[0]["is_lowest_input"] == "no"
        assert result[1]["is_lowest_input"] == "yes"

    def test_none_input_rmb(self) -> None:
        records = [{"canonical": "A", "source": "s1", "input_rmb": None}]
        result = _mark_lowest(records)
        assert result[0]["is_lowest_input"] == "no"

    def test_tie_marks_all(self) -> None:
        """并列最低时全部标记为 yes（当前实现语义）。"""
        records = [
            {"canonical": "A", "source": "s1", "input_rmb": 5.0},
            {"canonical": "A", "source": "s2", "input_rmb": 5.0},
        ]
        result = _mark_lowest(records)
        assert all(r["is_lowest_input"] == "yes" for r in result)


class TestWriteOutputs:
    def test_basic_write(self) -> None:
        records = [
            {
                "source": "s1",
                "canonical": "A",
                "input": 1.0,
                "output": 2.0,
                "model_raw": "a",
                "currency": "CNY",
                "unit": "1M tokens",
                "input_rmb": 1.0,
                "output_rmb": 2.0,
            }
        ]
        with tempfile.TemporaryDirectory() as d:
            paths = write_outputs(records, d)
            assert "prices.json" in paths
            assert "watchlist.json" in paths
            assert "prices.csv" in paths
            assert "watchlist.csv" in paths
            for p in paths.values():
                assert os.path.exists(p)

    def test_empty_records(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            paths = write_outputs([], d)
            assert os.path.exists(paths["prices.json"])
            assert os.path.exists(paths["watchlist.json"])
