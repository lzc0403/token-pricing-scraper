"""站点生成（入口）：site_data（数据层） + site_tpl（渲染层） 的薄包装。

历史：site.py 曾是 2870+ 行单体（数据构建 + HTML 渲染 + 内嵌 CSS/JS）。
2026-08-22 重构为三部分，保持 `from core import site` 兼容：
  - core/site_data.py   数据组装：watchlist.json → 站点数据结构
  - core/site_tpl.py    模板渲染：数据结构 → HTML 小部件与页面组装
  - core/site.py        本文件：re-export 公开 API（source_label/clean_model_name/build_site）

对外接口不变（tests 与 main.py 不需改动）：
  site.build_site(data_dir, out_path)
  site.source_label(source_id)
  site.clean_model_name(name)
"""

from __future__ import annotations

from core.site_data import (  # noqa: F401
    OFFICIAL_SOURCE,
    SOURCE_LABELS,
    _build_mainstream_sections,
    _build_site_data,
    _hydrate_catalog_prices,
    _is_official_any_currency,
    _is_official_row,
    _load_new_model_tracking,
    _merge_peak_rows,
    _normalize_row,
    _overseas_official_rows,
    _sort_canons,
    _vendor_rank,
    clean_model_name,
    source_label,
)
from core.site_tpl import build_site  # noqa: F401

__all__ = [
    "build_site",
    "source_label",
    "clean_model_name",
    "SOURCE_LABELS",
    "OFFICIAL_SOURCE",
]
