# 项目长期记忆 · token 定价

更新：2026-08-22

## 核心决策

- 站点由 `core/site_*.py` 生成，**禁止手改 `site/index.html` 后指望保留**。`core/site.py` 已是薄入口（51行 re-export），实际逻辑在 `core/site_data.py`（数据组装层）+ `core/site_tpl.py`（模板渲染层）；CSS/JS 外提至 `site/assets/style.css`+`app.js`，`build_site` 运行时读取后内联（单 HTML 部署不变）。
- 展示：ModelMesh→胜算云；网页汇率交互默认 7.0；html{zoom:1.1}+overflow-x:clip。
- 海外：仅热门主力，含 GPT-4o；新品用 `config/new_models.yml` 监听。
- **视觉设计令牌**（2026-08-08）：`--sp-*` 间距、`--r-*` 圆角、`--sh-*` 阴影三级；body 背景 `--canvas` 浅灰、卡片 `#fff` 浮起；主色 `#2BAE85`；价格单元格 `px-val`/`px-cur`/`js-rmb-hint` 三层结构。JS 依赖类名（`js-cny-main`/`js-rmb-hint`/`js-row` 等）不可变。
- **官方行标识**：白底 + 左侧 2px 品牌绿内阴影线（非整行黄底）；`.tag-official` 品牌绿软底；hover `#f8fafb`。
- **CI 门禁（2026-08-22 启用）**：`.github/workflows/ci.yml` push 触发 ruff + pytest（代码变更路径才跑）。ruff 配置 `select=["F","E9","W292"]` + `ignore=["F401","F841"]`——**存量代码大量 typing.Dict/List 风格债（UP006×365），全量启用会卡死所有 push**，故先只启用抓真 bug 的规则，风格债逐步偿还。pytest 需 `playwright install --with-deps chromium`（SPA scraper 测试真实渲染）。
- **audit.py CACHE_RATIO_ANOMALY 基准=中位数**（2026-08-22）：跨源缓存/输入比率偏离中位数 >15% 才告警。**不能用均值**——少数偏离源会把均值拉偏导致多数派误报（功能验证抓出的设计缺陷）。
- **audit.py OPENAI_LONG_DEV**（2026-08-22 修正）：openai 硬编码长上下文价 vs OpenRouter 同模型比对。**区分语义**：仅当 OpenRouter 匹配记录也带长文本/长上下文档（同规格对价）且偏差 >15% 才标 high（疑似硬编码价过期，阻断）；若 OpenRouter 只有标准档（无长档），偏差属渠道定价差异，降为 med（code `OPENAI_LONG_DEV_CH`）不阻断。原规则误把"OR 标准档 vs OAI 长档"的差异当过期，导致每日 automation 误拦（terra 4/18 vs OR 2/12、luna 0.4/1.8 vs OR 0.2/1.2）。硬编码值(mem: sol 10/45、terra 4/18、luna 0.4/1.8)经核与官网真实长档价一致，未过期。

## 数据源铁律

- **OpenRouter 价格铁律**：一律用 `openrouter.ai/api/v1/models` 真实价；禁止 `openrouter.yml` 写 `input_price/output_price` override 套用第三方转售商报价。
- **DeepSeek 来源类型 condition 标注铁律**：未标注「原厂直供」即云厂商自部署。腾讯云两站识别后缀→`原厂直供`/`腾讯云自建`；阿里云国际站/百炼→`阿里云自部署`；火山云海外→`火山引擎自部署`。
- **condition 清理**（2026-08-11）：atlascloud/openrouter 所有行 condition 置 None；aliyun_intl 非 DeepSeek 行置 None。
- **百炼缓存命中价**：按输入单价 × 20% 计算（`CACHE_HIT_RATIO = 0.2`，2026-08-22 已标注为「估算值，非页面明确数据」）。
- **OpenAI 长上下文价格（2026-08-22 调研结论：保留硬编码）**：`scrapers/openai.py` `_LONG_CONTEXT_PRICES` 硬编码 GPT-5.6 Sol/Terra/Luna（有 TODO）。动态抓取调研：真实页面 `TextTokenPricingTables` props 每行仅 4 列（短文本档），长文本档由前端 JS 运行时注入，**静态抓取拿不到**；强行 Playwright 读 DOM 成本高且脆。实测硬编码值与页面真实长档价一致（sol 10/45、terra 4/18、luna 0.4/1.8），靠 audit OPENAI_LONG_DEV 交叉校验兜底即可。中期 #5 标记为「暂缓」。

## 测试铁律（2026-08-22 新增）

- **新增 3 个核心模块测试**：test_currency（13）/ test_openrouter_verify（10）/ test_store（11），共 38 例，补上 openrouter_verify/report/currency 无测试缺口。
- **数据依赖型测试必须用 fixture，不要读真实 data/**：`test_official_rows_vendor_grouped_with_qwen_cache` 原读 data/watchlist.json，aliyun 源线上 0 条时 flaky（CI 干净环境必挂），已改 tmp_path 合成 watchlist 注入。

## SOURCE_LABELS 与双币种官方识别

- 简化标签：`tencent`→腾讯云国际、`tencent_cn`→腾讯云CN、`aliyun_intl`→阿里云国际（全去括号）。
- **`_is_official_any_currency` 双币种铁律**：厂商国内站(CNY)+海外站(USD)均为官方原价。当前支持 DeepSeek（deepseek + deepseek_us）与 GLM（bigmodel + zai）。新增多站厂商在此函数加 `if str(canon).startswith("<前缀>") and src in ("<国内id>", "<海外id>")` 分支。
- site.py:668 去重逻辑 `if x["source"] == "deepseek_us" or not already_cny` 用 source id 硬编码，新增 USD 官方源需检查此处。

## 峰谷定价

- **DeepSeek 官网峰谷**（2026-08-17 改版）：`api-docs.deepseek.com` 中英文站从单档改为峰谷双档。`scrapers/deepseek.py` 状态机式解析（`last_field` 承接高峰行类别），输出 6 字段 + `condition="峰谷计费"`。主字段取闲时价。
- **峰谷动态比价**（2026-08-20 commit 905ac89）：`PEAK_SCHEDULES` 常量 + `channelSched` 映射；`_build_site_data` 附加 `official_off/peak_in`/`channel_off/peak_in`/`peak_sched`；`_table_row` 注入 `data-sched`/`data-ch-*`/`data-of-*`；渠道区块 `peak-clock` banner 按北京时间实时判档每 60s 刷新；`_JS` 注入 `recomputePeak()` IIFE。两套窗口：DeepSeek 高峰 09-12/14-18 全价闲时减半；阿里云国际站闲时 22-08。错峰时段 08-09/12-14/18-22。
- **溢价基准 = 官网价**（2026-08-20 commit 228758e）：`base_in = min(该模型官网行 input_rmb)`，非渠道间互比。`_normalize_row` 新增 `base_in` 参数。
- **峰谷默认闲时优先**：`_merge_peak_rows` 主价字段取闲时（`mrow = dict(low)`）；`_peak_duo` 渲染闲X/高Y；`.px-peak-lo` 主色、`.px-peak-hi` 弱化。
- **OpenRouter overrides**：`scrapers/openrouter.py` `_parse_overrides` 从 `pricing.overrides` 提取峰谷（UTC HHMM→北京时间）。

## 渠道源

- **阿里云国际站**：`aliyun_intl`（USD SPA）→ `scrapers/aliyun_intl.py`，Qwen/DeepSeek/Kimi/GLM 9 模型。峰谷表 Time Period 列→列偏移 col_in=4/col_out=5/col_cache=6/col_peak=3。
- **AtlasCloud**：JSON API `console.atlascloud.ai/api/v1/models`，仅 `type=="Text"`。审计发现 `fetched_at` 为空字符串（低修复项）。
- **腾讯云国内站**：`tencent_cn`（CNY SPA），取含「原厂直供」完整表，多表 last-wins。`_base_name` 剥离正式版/原厂直供/腾讯云自建/HighSpeed/Preview。
- **阿里云百炼**：`aliyun_bailian`（CNY JSON API `help.aliyun.com/help/json/document_detail.json`），DeepSeek/GLM/Kimi/MiniMax；跳过海外区域。
- **Z.ai 智谱海外官方**：`zai`（USD），只取文本模型表（表头含 Model+Input+Output），`_is_vision` 排除 GLM-*V/OCR。zai 不在 CHANNEL_SOURCES，是官方 USD 源。
- **BytePlus 火山云海外**：`volcengine_intl`（USD SPA），`_SUFFIX_RE`/`_GA_SUFFIX_RE`/`_VERSION_DASH_RE` 归一化；分层取首行。
- **厂商价格查询入口**（portal 区块）：footer 上方 17 厂商链接卡片，CNY 绿 ¥ / USD 蓝 $ 双色标签。

## 新模型收录

- GLM-5.3（Z.ai 定价页无，Coding Plan 订阅专属；mainstream_models.yml 已补）
- Claude Opus 5（$5/$25，Fast $10/$50）
- Gemini 3.7 Flash（限时 $0.75/$3.75，之后 $1.50/$7.50）
- Grok 4.6（$2/$6，缓存 $0.50）
- Qwen3.8 Max（mainstream_models.yml 已补，12/36 CNY）

## 部署

- **永久地址**：https://lzc0403.github.io/token-pricing-scraper/ （GitHub Pages，每周日 18:00 UTC CI 抓取+发布，workflow_dispatch 可手动触发）
- CI 数据提交模式：scrape.yml 自动 push data/site 到 origin/main，本地 main 会落后于远程 → 推送前先 `git fetch` + `git merge origin/main`
- **每日抓取缺口**（2026-08-17 确认）：仅 GitHub Actions 每周日跑，用户期望每日抓取但未配置 automation。需新建 automation 或 self-hosted runner cron。

## git 仓库损坏修复铁律

- `.git` 对象库已损坏 ≥3 次（2026-08-16/18/20），均由 stash + rebase 中断触发。
- **铁律：直接 reclone + 替换 .git，不要再试 `git gc`/`read-tree` 等修补**，修补不彻底会复发。
- 步骤：备份工作树 → `git clone --depth 5 origin D:/tmp/tps-restore`（中文 temp 路径失败，用 D:/tmp）→ `mv .git .git-corrupted-YYYYMMDD` + `cp -r tps-restore/.git .git` → `git add -A && git commit && git push`。
- **.gitignore**：`.workbuddy/skills/`/`.workbuddy/redbox-screenshot.png`/`.workbuddy/sessions/`/`.workbuddy/mcp.json`/`.workbuddy/settings.json` 不入库。

## 模型清单排除项

腾讯云国际站 Model Studio 不收录：GLM-5、GLM-5V-Turbo/GLM-5-Turbo、kimi-k2.5、Kimi K2.7 Code HighSpeed、Phi4Max-M3、MiniMax-M2.5、Hy-MT2-Plus、Hy3、DeepSeek-v3.2（重复/价不一致）。（Kimi K3 必须收录。）

## 已知线上抓取问题

- **aliyun 源线上 0 条**（2026-08-16）：`help.aliyun.com` 可能改版/限流。测试通过从 HEAD watchlist.json 恢复 aliyun 记录绕过。

## 代码审计结论（2026-08-20）

- 全量审阅 8,478+ 行（core/scrapers/tests/config），输出 `code-audit-report.html`。
- **0 致命 / 2 高 / 6 中 / 5 低**。无致命：项目可正常运行，数据有多层审计保障。
- 高：①site.py 2870 行单体（CSS/JS/Python 混杂）②openai.py 硬编码长上下文价格。
- 中：bailian 缓存 0.2 假设 / 17 源顺序执行 / CSS/JS 内嵌字符串 / 无前置输入校验 / 3 核心模块无测试（openrouter_verify/report/currency）/ atlascloud fetched_at 空。
- 低：类型注解不全 / 正则静默失败 / 魔术数字 / 错误处理不一致 / 无 CI lint。
- 改进三阶段：短期止血（atlascloud 时间戳+CI lint+百炼标注+补测试）→ 中期架构解耦（site.py 前端外提+并行抓取+模块拆分）→ 长期产品化（Jinja2+每日抓取+历史趋势图+价格推送）。
- **短期 5 项 + 中期 5 项已全部落地并推送**（2026-08-22）：commit `62cbbce`..`5e7f087`，CI 全绿。仅中期 #5（OpenAI 动态抓取）经调研暂缓。
- **长期计划全部完成（2026-08-22）**：三阶段（短期/中期/长期）全落地并推送。
  - ✅ **每日抓取 automation**：`automation-1787338740315`。**方案 A（2026-08-22 定稿）：云端唯一数据源**——GitHub Action（scrape.yml，UTC 17:00 = 北京时间 01:00）是唯一权威抓取源；本机 cron 每日 10:40 只负责 `git pull` + `python main.py --verify-only` 只读校验（不抓取、不写 data/、不 push），异常才上报。
  - ✅ **历史价格趋势图**：`data/history/YYYY-MM-DD.json` 每日快照归档（`core/store.py:archive_snapshot`）+ `_load_history()` + `_trend_section()` Chart.js 折线图。数据从 2026-08-22 起累积。
  - ✅ **价格变动推送**：`core/notifier.py`，对比上一日快照生成飞书/企微 markdown 播报，配置驱动（FEISHU_WEBHOOK_URL/WECOM_WEBHOOK_URL 未设则静默跳过），main.py 生成报告后调用。tests/test_notifier.py 6 例。
  - ✅ **mypy 类型检查 + CI 门禁**：pyproject `[tool.mypy]`，修复 21 处真实类型隐患（Any|None 参与数值比较、setdefault、重复 _load_asset、隐式 Optional、yaml stub），scrape.yml 新增 mypy 步骤，.mypy_cache 入 gitignore。
  - ✅ **Jinja2 模板引擎**：`site/templates/index.html.j2` 承载页面骨架，`core/site_tpl.py:build_site` 改用 Jinja2 Environment 渲染（区块字符串仍由已测函数生成经 | safe 注入）。等价性验证：与迁移前基线归一化后仅时间戳不同，零回归。
  - 全部 commit 见 `74ca634`（价格推送+mypy+Jinja2 三合一）。中期 #5（OpenAI 动态抓取）仍暂缓（页面 JS 注入长上下文价，无法静态解析）。

## 文档

见 README + docs/{architecture,openrouter,runbook,handoff}.md + AGENTS.md
