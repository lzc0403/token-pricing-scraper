"""Token 定价抓取器包。

每个数据源对应一个 parser 模块（scrapers/<name>.py），其中定义一个
继承自 `scrapers.base.BaseScraper` 的子类，并实现 `parse(html)` 方法。
"""

from scrapers.base import BaseScraper

__all__ = ["BaseScraper"]
