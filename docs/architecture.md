# Architecture

## 数据流

```
config/sources.yml
      │
      ▼
main.py run_sources()
      │  动态加载 scrapers.<parser>
      ▼
List[record]  ──currency.enrich──►  input_rmb / output_rmb
      │
      ├─ openrouter whitelist 强制 canonical
      ▼
matcher.build_watchlist  ──► annotated + watchlist
      │
      ├─ store.write_outputs → data/prices.* watchlist.*
      ├─ report → REPORT.md / issue_body.md
      ├─ audit.run → audit.json / audit_report.md
      ├─ openrouter_verify.verify → openrouter_verify.*
      └─ site.build_site → site/index.html
```

## 源类型

| 类型 | 示例 | 抓取方式 |
|------|------|----------|
| 静态 HTML | deepseek | requests |
| SPA 文档 | aliyun / tencent / bigmodel… | Playwright |
| **JSON API** | **openrouter** | requests + 磁盘缓存 |

## 页面数据分区（core/site.py）

| 区块 | 数据 | 货币 |
|------|------|------|
| 厂商官网原价 | OFFICIAL_SOURCE 映射的国内源 | CNY 优先 |
| 海外主流 | `OVERSEAS_OFFICIAL` 热门旗舰 | USD + 汇率约价 |
| 新品跟进 | `config/new_models.yml` | 状态卡片 |
| 渠道报价 | 非官网 + **OpenRouter** | 国内 CNY / 海外 USD 分页 |

## 二次验证

1. **Tier1/2 全源**（`core/audit.py`）：空值、离谱价、汇率一致性、页面抽样
2. **OpenRouter 专用**（`core/openrouter_verify.py`）：
   - 缓存 `data/openrouter_raw.json` 必须存在
   - 每条 `openrouter_id` 可回查
   - `input/output ≈ pricing.* * 1e6`（容差见 openrouter.yml）
   - 白名单缺失计数

## 关键展示约定

- ModelMesh → 胜算云
- 海外只保留热门主力（含 GPT-4o），不堆 mini/nano/lite
- 网页汇率默认 7.0，可交互修改
