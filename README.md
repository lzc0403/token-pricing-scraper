# 大模型 Token 定价自动抓取（token-pricing）

自动抓取多家主流大模型服务商的 **Token 定价**，结构化保存为 JSON / CSV，生成
**9 个重点关注模型（watchlist）** 的横向比价视图，并在**价格周环比变动**时自动
开 GitHub Issue 提醒。

> 适用场景：个人 / 团队做模型选型时的成本对比，或长期追踪各家价格变化。

---

## 功能特性

- **10 个数据源**：阿里云百炼、火山引擎方舟、腾讯云 TokenHub、智谱 BigModel、
  DeepSeek、MiniMax、Kimi、ModelMesh，以及多页抓取的 Kimi（3 个定价页）。
- **统一数据模型**：每个 parser 输出 `parse(html) -> List[dict]`，字段统一为
  `source / model_raw / input / output / cache_hit / context / condition / unit / currency`。
- **汇率归一**：美元价格按 `USD_CNY_RATE`（默认 7.2）折算为人民币 `input_rmb / output_rmb`，
  便于跨源比价与「最低价」标注。
- **watchlist 匹配**：`config/models.yml` 定义 9 个目标模型及别名，按归一化（小写、
  去空格 / `-` / `_`）后**精确 + 包含**匹配，自动标注 `canonical`。
- **变更检测**：每次运行与已提交的 `data/prices.json` 对比，输出变动清单并生成
  `REPORT.md` 与 GitHub Issue 正文。
- **GitHub Action**：每周日 18:00 UTC 自动运行，提交 `data/` 并在有变动时开 Issue。

---

## 目录结构

```
token 定价/
├── config/
│   ├── sources.yml        # 10 个数据源配置（URL / parser / 货币 / 是否 JS / 区域）
│   └── models.yml         # 9 个目标模型及别名
├── scrapers/
│   ├── base.py            # BaseScraper：HTTP 获取（含 Playwright JS 渲染）+ clean_price
│   ├── aliyun.py         # 阿里云百炼（主 URL 失效自动回退 fallback）
│   ├── volcengine.py     # 火山引擎方舟
│   ├── tencent.py        # 腾讯云 TokenHub（仅取广州/中国大陆区域）
│   ├── bigmodel.py       # 智谱 BigModel
│   ├── deepseek.py       # DeepSeek
│   ├── minimax.py        # MiniMax
│   ├── kimi.py           # Kimi（多页）
│   └── modelmesh.py      # ModelMesh 模型中心
├── core/
│   ├── matcher.py        # 模型名归一化与 watchlist 匹配
│   ├── currency.py       # USD->CNY 汇率换算
│   ├── store.py          # 写出 JSON/CSV + 历史对比
│   └── report.py         # 生成 REPORT.md / issue_body.md
├── tests/
│   ├── fixtures/         # 已保存的真实页面 HTML（离线测试用）
│   └── test_parsers.py   # parser / 匹配单元测试
├── data/                 # 运行产物（自动生成，提交到仓库）
│   ├── prices.json / prices.csv        # 全量抓取结果
│   ├── watchlist.json / watchlist.csv  # 9 个目标模型比价视图
│   ├── REPORT.md                       # 周报
│   └── issue_body.md                  # Issue 正文（变动时）
├── main.py               # 命令行入口与编排
├── requirements.txt
└── .github/workflows/scrape.yml
```

---

## 环境准备

```bash
# 使用受管 Python 创建虚拟环境（示例路径，请按需调整）
python -m venv .venv
.venv\Scripts\python.exe -m pip install -U pip
.venv\Scripts\python.exe -m pip install requests parsel pyyaml pytest

# 需要浏览器渲染的源（aliyun / volcengine / bigmodel / minimax / kimi / modelmesh）
.venv\Scripts\python.exe -m pip install playwright
.venv\Scripts\python.exe -m playwright install chromium
```

---

## 本地运行

```bash
# 完整抓取并写 data/（会写 $GITHUB_OUTPUT，仅当在 Action 环境中生效）
.venv\Scripts\python.exe main.py

# 预览模式：照常抓取写盘，但不写 GITHUB_OUTPUT
.venv\Scripts\python.exe main.py --dry-run
```

运行流程：

1. 读取 `config/sources.yml` 与 `config/models.yml`；
2. 逐源抓取（失败仅记录，不中断整体）；
3. 汇率换算、模型匹配标注 `canonical`；
4. 写出 `data/prices.*` 与 `data/watchlist.*`；
5. 与已提交的 `data/prices.json` 对比，生成周环比变动；
6. 生成 `REPORT.md` / `issue_body.md`，并在有变动时输出 `changed=true`。

---

## 测试

```bash
.venv\Scripts\python.exe -m pytest tests/test_parsers.py
```

测试基于 `tests/fixtures/` 中保存的真实页面 HTML，离线验证：
各 parser 能正确解析、关键模型（如 `qwen3.7-max` 折后价 6.0/18.0）数值正确、
腾讯云仅取中国大陆区域、以及 **9 个目标模型全部能被匹配**。

---

## 关键设计说明

- **数据模型字段**：`input / output / cache_hit` 为每百万 tokens 价格；`unit` 默认
  `"1M tokens"`；`currency` 取自各源配置（CNY / USD）。
- **价格清洗**：`clean_price` 去除 `¥ $ 元 空格 逗号`；识别「原价 N 元 限时 M 折」
  折算为折后价；对 ModelMesh 这类夹带 `$ (¥)` 的源，可用 `prefer_currency="¥"`
  优先取人民币等价。
- **区域过滤**：腾讯云文档用 tab 切换区域，本工具仅取「广州 / 中国大陆」面板；
  阿里云仅保留「中国内地」部署范围的行。
- **健壮性**：单源抓取异常不影响其他源；parser 通过 `importlib` 动态加载，新增源
  只需在 `config/sources.yml` 增加一项并实现对应 `scrapers/<parser>.py`。
