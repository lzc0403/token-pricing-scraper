"""汇率换算模块单元测试（core/currency.py）。"""

from __future__ import annotations

import os

import pytest

from core.currency import DEFAULT_RATE, enrich, get_rate, to_rmb


class TestToRmb:
    def test_usd_conversion(self) -> None:
        assert to_rmb(10.0, "USD", 7.0) == 70.0

    def test_cny_passthrough(self) -> None:
        assert to_rmb(10.0, "CNY", 7.0) == 10.0

    def test_none_input(self) -> None:
        assert to_rmb(None, "USD", 7.0) is None

    def test_unknown_currency(self) -> None:
        # 未知币种按非 USD 处理：原值透传
        assert to_rmb(5.0, "EUR", 7.0) == 5.0

    def test_rounding(self) -> None:
        assert to_rmb(1.2345678, "USD", 7.0) == 8.641975


class TestEnrich:
    def test_basic_enrich(self) -> None:
        records = [{"input": 10.0, "output": 20.0, "currency": "USD"}]
        result = enrich(records, rate=7.0)
        assert result[0]["input_rmb"] == 70.0
        assert result[0]["output_rmb"] == 140.0

    def test_cny_no_conversion(self) -> None:
        records = [{"input": 10.0, "output": 20.0, "currency": "CNY"}]
        result = enrich(records, rate=7.0)
        assert result[0]["input_rmb"] == 10.0
        assert result[0]["output_rmb"] == 20.0

    def test_none_fields(self) -> None:
        records = [{"input": None, "output": 20.0, "currency": "USD"}]
        result = enrich(records, rate=7.0)
        assert result[0]["input_rmb"] is None
        assert result[0]["output_rmb"] == 140.0

    def test_peak_fields(self) -> None:
        records = [
            {
                "input": 10.0,
                "output": 20.0,
                "currency": "USD",
                "peak_input_low": 5.0,
                "peak_input_high": 15.0,
            }
        ]
        result = enrich(records, rate=7.0)
        assert result[0]["peak_input_rmb_low"] == 35.0
        assert result[0]["peak_input_rmb_high"] == 105.0

    def test_inplace_mutation(self) -> None:
        """enrich 应就地修改原 records（并返回同一列表）。"""
        records = [{"input": 1.0, "currency": "USD"}]
        result = enrich(records, rate=7.0)
        assert result is records
        assert records[0]["input_rmb"] == 7.0


class TestGetRate:
    def test_default_rate_when_unset(self, monkeypatch) -> None:
        monkeypatch.delenv("USD_CNY_RATE", raising=False)
        assert get_rate() == DEFAULT_RATE

    def test_custom_rate(self, monkeypatch) -> None:
        monkeypatch.setenv("USD_CNY_RATE", "7.15")
        assert get_rate() == 7.15

    def test_invalid_env_falls_back(self, monkeypatch) -> None:
        monkeypatch.setenv("USD_CNY_RATE", "abc")
        assert get_rate() == DEFAULT_RATE

    def test_empty_env_falls_back(self, monkeypatch) -> None:
        monkeypatch.setenv("USD_CNY_RATE", "")
        assert get_rate() == DEFAULT_RATE
