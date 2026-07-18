# 大模型 Token 定价自动抓取（token-pricing）

自动抓取多家主流大模型 **Token 定价**，结构化保存为 JSON / CSV，生成官网 / 渠道 / 海外主流 / OpenRouter 比价网页，并在周环比变动时开 GitHub Issue。

> 适用：选型成本对比、长期追踪价格变化。

---

## 功能特性

- **数据源**：阿里云、火山引擎、腾讯云、智谱、DeepSeek、MiniMax、Kimi、胜算云（ModelMesh）、**OpenRouter**
- **统一记录**：`source / model_raw / input / output / cache_hit / context / currency / unit`
- **汇率归一**：USD → CNY（运行时默认汇率可配置；网页端默认 **7.0** 可手动改）
- **watchlist 匹配**：`config/models.yml` 别名匹配 + OpenRouter 白名单强制 canonical
- **二次验证**：
  - 全源结构性 / 抽样核对 → `core/audit.py` → `data/audit_*`
  - OpenRouter 原始 JSON vs 解析价 → `core/openrouter_verify.py` → `data/openrouter_verify.*`
- **静态站点**：`core/site.py` 生成 `site/index.html`（筛选、Excel、国内/海外分页、新品雷达）
- **GitHub Action**：定期抓取并提交 `data/` + `site/`

---

## 目录结构

```
token 定价/
├── config/
│   ├── sources.yml              # 全部数据源（含 openrouter）
│   ├── models.yml               # 国内目标模型别名（安全匹配：exact + 显式 prefix）
│   ├── mainstream_models.yml    # 国内/海外主流模型官方目录（schema 校验）
│   ├── openrouter.yml           # OpenRouter 白名单 + top-weekly 规则
│   └── new_models.yml           # 新品主动跟进清单
├── scrapers/
│   ├── base.py
│   ├── openrouter.py            # Models API 下载缓存 + 解析
│   └── …                        # 各厂商 parser
├── core/
│   ├── site.py                  # 网页生成器（双专区 + 卡片筛选联动）
│   ├── mainstream_catalog.py    # 主流目录读取、schema 校验、可渲染过滤
│   ├── audit.py                 # 抓取后全源核对
│   ├── openrouter_verify.py     # OpenRouter 二次验证
│   ├── matcher.py / currency.py / store.py / report.py
├── data/
│   ├── prices.* / watchlist.*
│   ├── openrouter_raw.json      # 自动下载的原始 API
│   ├── openrouter_verify.*      # 二次验证产物
│   └── audit_* / REPORT.md
├── site/index.html
├── docs/                        # 接入 / 架构 / 运维说明
├── main.py
└── requirements.txt
```

---

## 快速运行

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m playwright install chromium   # JS 源需要

.venv\Scripts\python.exe main.py --dry-run
```

产物：

- `data/prices.json` 全量
- `data/watchlist.json` 目标模型 + OpenRouter 白名单
- `data/openrouter_raw.json` 原始 API 缓存
- `data/openrouter_verify.md` 二次验证报告
- `site/index.html` 比价站

---

## OpenRouter 规则（摘要）

详见 [docs/openrouter.md](docs/openrouter.md)。

1. 自动请求 `https://openrouter.ai/api/v1/models?sort=top-weekly`
2. 写入 `data/openrouter_raw.json`
3. 按 `config/openrouter.yml` 白名单收录热门（含 GPT-4o / GPT-5 / Claude / Gemini / MiniMax M3 / Kimi K3 等）
4. 再补 top-weekly 非免费文本模型
5. `openrouter_verify` 用 raw 价 ×1e6 与解析结果交叉验证

---

## 网页布局（site/）

1. 筛选与汇率（模型分类 + 渠道 + 仅国内/仅海外）
2. 国内主流大模型（六大厂商卡片：DeepSeek / 通义千问 / 智谱 GLM / Kimi / MiniMax / 豆包）
3. 海外主流大模型（OpenAI / Anthropic Claude / Google Gemini 卡片，含 **GPT-4o**）
4. 厂商官网原价（国内）
5. 新品主动跟进（MiniMax M3 / Kimi K3 / Claude 5…）
6. 渠道同类报价（含 **OpenRouter**，国内 CNY / 海外 USD 分页）
7. 图表 / Excel 导出

展示名：ModelMesh → **胜算云**；openrouter → **OpenRouter**。

主流目录由 `config/mainstream_models.yml` 驱动；证据不足的型号设为 `tracking`，不进入正式卡片。渠道先行型号不等于官方正式型号。

---

## 相关文档

- [docs/architecture.md](docs/architecture.md) — 数据流与模块
- [docs/openrouter.md](docs/openrouter.md) — OpenRouter 接入与验证
- [docs/runbook.md](docs/runbook.md) — 运维 / 排障
- [docs/handoff.md](docs/handoff.md) — 当前完成状态与待办

---

## 测试

```bash
.venv\Scripts\python.exe -m pytest tests/test_parsers.py
```

OpenRouter 冒烟（需网络）：

```bash
.venv\Scripts\python.exe -c "from scrapers.openrouter import OpenrouterScraper; import yaml; s=next(x for x in yaml.safe_load(open('config/sources.yml',encoding='utf-8')) if x['id']=='openrouter'); print(len(OpenrouterScraper(s).run()))"
```
