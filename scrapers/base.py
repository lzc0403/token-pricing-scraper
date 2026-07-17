"""抓取器基类：统一 HTTP 获取与解析流程。

所有数据源 parser 都继承 `BaseScraper`，只需实现 `parse(html)`：

    class AliyunScraper(BaseScraper):
        def parse(self, html: str) -> List[dict]:
            ...

`run()` 负责 抓取 + 解析，并过滤掉空记录，返回标准记录列表。
"""

from __future__ import annotations

import abc
import re
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_TIMEOUT = 20
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# 货币字段固定值，来自 config
DEFAULT_UNIT = "1M tokens"

_PRICE_STRIP = re.compile(r"[¥$\s元,，]")
_PRICE_NUM = re.compile(r"\d+(?:\.\d+)?")


def clean_price(text: Any, prefer_currency: Optional[str] = None) -> Optional[float]:
    """清洗价格字符串为 float。

    规则：去掉 ¥ $ 元 空格 逗号；无法解析返回 None。
    - 含「原价X元 限时Y折」时，返回折后价 X*Y/10。
    - prefer_currency="¥" 时（如 modelmesh 夹带 $ 换算），优先取 ¥ 后的数值。
    """
    if text is None:
        return None
    s = str(text)
    # 限时折扣：原价 N 元，限时 M 折 -> N * M / 10
    m_o = re.search(r"原价\s*(\d+(?:\.\d+)?)", s)
    m_z = re.search(r"(\d+(?:\.\d+)?)\s*折", s)
    if m_o and m_z:
        return round(float(m_o.group(1)) * float(m_z.group(1)) / 10, 6)
    if prefer_currency == "¥" and "¥" in s:
        m = re.search(r"¥\s*(\d+(?:\.\d+)?)", s)
        if m:
            return float(m.group(1))
    s2 = _PRICE_STRIP.sub("", s)
    m = _PRICE_NUM.search(s2)
    return float(m.group(0)) if m else None


class BaseScraper(abc.ABC):
    """单数据源抓取器基类。"""

    def __init__(self, source: Dict[str, Any]) -> None:
        """初始化。

        Args:
            source: config/sources.yml 中该源的配置 dict，至少包含
                    `id` / `parser` / `currency` 字段。
        """
        self.source = dict(source)
        self.source_id: str = str(source.get("id", ""))
        self.currency: str = str(source.get("currency", "CNY"))
        self.js: bool = bool(source.get("js", False))
        self.session: requests.Session = self._build_session()

    # ------------------------------------------------------------------ #
    # HTTP
    # ------------------------------------------------------------------ #
    @staticmethod
    def _build_session() -> requests.Session:
        """构造带重试策略的 Session。"""
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=frozenset(["GET", "HEAD"]),
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update({"User-Agent": DEFAULT_UA})
        return session

    def fetch_url(self, url: str) -> str:
        """抓取单个 URL，返回页面 HTML 文本。

        js:true 时使用 Playwright 无头浏览器渲染后取 page.content()；
        否则使用 requests.Session。

        Raises:
            requests.RequestException / RuntimeError: 抓取失败时向上抛出，由调用方捕获。
        """
        if self.js:
            return self._fetch_js(url)
        resp = self.session.get(url, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        # 尽量用正确编码解码
        resp.encoding = resp.apparent_encoding or resp.encoding
        return resp.text

    def _fetch_js(self, url: str) -> str:
        """使用 Playwright 无头浏览器渲染 JS 页面并返回 HTML。"""
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                ctx = browser.new_context(
                    user_agent=DEFAULT_UA,
                    viewport={"width": 1280, "height": 900},
                )
                page = ctx.new_page()
                page.goto(url, timeout=DEFAULT_TIMEOUT * 1000, wait_until="domcontentloaded")
                # 等待 SPA 渲染
                page.wait_for_timeout(5000)
                try:
                    page.wait_for_function(
                        "() => document.body && document.body.innerText.length > 500",
                        timeout=15000,
                    )
                except Exception:
                    pass
                return page.content()
            finally:
                browser.close()

    def fetch(self) -> str:
        """抓取主 URL（config 中的 `url` 字段）。"""
        return self.fetch_url(self.source["url"])

    # ------------------------------------------------------------------ #
    # 解析（子类实现）
    # ------------------------------------------------------------------ #
    @abc.abstractmethod
    def parse(self, html: str) -> List[Dict[str, Any]]:
        """解析页面 HTML，返回标准记录列表。"""
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    # 流程编排
    # ------------------------------------------------------------------ #
    def _empty_record(self) -> Dict[str, Any]:
        """生成一条空记录骨架，填充源信息。"""
        return {
            "source": self.source_id,
            "model_raw": None,
            "input": None,
            "output": None,
            "cache_hit": None,
            "context": None,
            "condition": None,
            "unit": DEFAULT_UNIT,
            "currency": self.currency,
        }

    def _rec(
        self,
        model_raw: Optional[str],
        input: Optional[float] = None,
        output: Optional[float] = None,
        cache_hit: Optional[float] = None,
        context: Optional[str] = None,
        condition: Optional[str] = None,
    ) -> Dict[str, Any]:
        """构造一条标准记录（自动填充 source / currency / unit）。"""
        return {
            "source": self.source_id,
            "model_raw": model_raw,
            "input": input,
            "output": output,
            "cache_hit": cache_hit,
            "context": context,
            "condition": condition,
            "unit": DEFAULT_UNIT,
            "currency": self.currency,
        }

    def run(self) -> List[Dict[str, Any]]:
        """抓取并解析，返回非空记录列表。

        多 URL 源（如 kimi 配置 `urls`）会依次抓取每个 URL 并合并。
        """
        records: List[Dict[str, Any]] = []
        urls = self.source.get("urls") or [self.source.get("url")]
        for url in urls:
            if not url:
                continue
            html = self.fetch_url(url)
            parsed = self.parse(html) or []
            records.extend(parsed)
        # 过滤空记录 / 无模型名的记录
        cleaned = [r for r in records if r and r.get("model_raw")]
        return cleaned
