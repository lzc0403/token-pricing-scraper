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
| 国内主流大模型 | `config/mainstream_models.yml` → `mainstream_catalog.renderable_sections("domestic")` | CNY |
| 海外主流大模型 | `config/mainstream_models.yml` → `mainstream_catalog.renderable_sections("overseas")` | USD |
| 厂商官网原价 | OFFICIAL_SOURCE 映射的国内源 | CNY 优先 |
| 新品跟进 | `config/new_models.yml` | 状态卡片 |
| 渠道报价 | 非官网 + **OpenRouter** | 国内 CNY / 海外 USD 分页 |

## 主流模型目录（core/mainstream_catalog.py）

- `config/mainstream_models.yml` 是国内/海外主流专区的唯一型号来源
- `load_catalog()` 读取并校验 schema：必填字段、枚举、价格非负、来源 URL、时区核验时间
- `renderable_sections()` 只返回 `availability ∈ {official, preview}` 且 `modality = text` 的型号
- `tracking` / `invite_only` 型号不进入正式卡片，但保留在目录中供监听
- Claude official 型号必须有准确 `api_id`（Fable 5 / Opus 4.8 / Sonnet 5 / Haiku 4.5）
- 卡片点击触发 `selectOnlyModel(canonical)`，联动下方渠道筛选

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
