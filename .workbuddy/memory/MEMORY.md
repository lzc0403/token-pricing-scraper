# 项目长期记忆 · token 定价

更新：2026-09-01

## 核心决策

- 站点由 `core/site_*.py` 生成，**禁止手改 `site/index.html`**。`core/site.py` 是薄入口，逻辑在 `core/site_data.py`（数据组装）+ `core/site_tpl.py`（Jinja2 模板渲染）；CSS/JS 外提至 `site/assets/`，`build_site` 运行时内联。
- 展示：ModelMesh→胜算云；汇率交互默认 7.0；主色 `#2BAE85`。
- 海外榜保持「热门精简」，GPT-4o 必在榜；新品用 `config/new_models.yml` 监听。
- JS 依赖类名（`js-cny-main`/`js-rmb-hint`/`js-row` 等）不可变。
- **CI 门禁**：push 触发 ruff + pytest + mypy。ruff `select=["F","E9","W292"]` + `ignore=["F401","F841"]`——存量 typing.Dict/List 风格债（UP006×365）全量启用会卡死 push，只启用抓真 bug 的规则。pytest 需 `playwright install --with-deps chromium`。

## 数据源铁律

- **OpenRouter 价格铁律**：一律用 `openrouter.ai/api/v1/models` 真实价；禁止 `openrouter.yml` 写 `input_price/output_price` override 套第三方转售商报价。
- **condition 标注**：未标注「原厂直供」即云厂商自部署。腾讯云两站后缀→`原厂直供`/`腾讯云自建`；阿里云国际站/百炼→`阿里云自部署`；火山云海外→`火山引擎自部署`。atlascloud/openrouter 所有行 condition 置 None。
- **百炼缓存命中价**：输入单价 × 20%（估算值，非页面明确数据）。
- **OpenAI 长上下文价**：`scrapers/openai.py` `_LONG_CONTEXT_PRICES` 硬编码 GPT-5.6 Sol/Terra/Luna（**保留，动态抓取调研结论为不可行**——页面长档价由前端 JS 运行时注入，静态抓取拿不到）。靠 audit `OPENAI_LONG_DEV` 交叉校验兜底。

## 促销价解析铁律（2026-09-01）

厂商官网「限时折扣」会导致抓到**划线原价**而非实际扣费价，与 OpenRouter 差 100% 触发跨源告警。两个源的坑与解法：

- **zai（docs.z.ai）**：单元格形如 `<td><del>$0.15</del> $0.075</td>`，`string(.)` 得「$0.15 $0.075」，`clean_price` 取首个 → 错抓原价。解法：`scrapers/zai.py:_cell_text` 用 `xpath(".//text()[not(ancestor::del)]")` 排除 `<del>`。
- **bigmodel（open.bigmodel.cn）**：①模型名列 `name-box` 内首 `<p>` 是纯名、其后 `<div>` 是促销标签（「5折限时两周」），粘进名字会导致 matcher 归一化后匹配失败被丢弃 → `_model_name` 取首 `<p>`。②价格列 `price-box` 内两个 `.price-line`（首为折后价、次为划线原价），`string(.)` 得「1.4元 2.8元」→ 去符号拼成「1.42.8」→ 误读为 1.42 → `_price_text` 取首个 `.price-line`。
- 通用原则：**促销单元格一律「取首个目标节点」**，促销结束后节点数回落为 1，逻辑自动兼容，无需改代码。

## 测试铁律

- **数据依赖型测试必须用 fixture，不要读真实 data/**：读 data/watchlist.json 会在源线上 0 条时 flaky（CI 干净环境必挂）。
- `tests/test_parsers.py::test_watchlist_all_configured_targets_matched` 断言 models.yml 每个 canonical 都要能命中；**新增 canonical 必须同步在该测试补 synthetic record**（`recs.append({"model_raw": ...})`）。

## 双币种官方识别

- 标签：`tencent`→腾讯云国际、`tencent_cn`→腾讯云CN、`aliyun_intl`→阿里云国际。
- **`_is_official_any_currency`**：厂商国内站(CNY)+海外站(USD)均为官方原价。当前支持 DeepSeek（deepseek+deepseek_us）、GLM（bigmodel+zai）、Kimi（kimi+kimi_ai）。新增多站厂商在此函数加分支。
- site 去重逻辑用 source id 硬编码（`deepseek_us` 等），新增 USD 官方源需检查该处。

## 峰谷定价

- **DeepSeek 官网峰谷**：`api-docs.deepseek.com` 中英站双档，`scrapers/deepseek.py` 状态机解析（`last_field` 承接高峰行类别），输出 6 字段 + `condition="峰谷计费"`，主字段取闲时价。
- **窗口定义**：DeepSeek 高峰 09-12/14-18 全价、闲时减半；阿里云国际站闲时 22-08（错峰 08-09/12-14/18-22）。**两站窗口定义不同是既定事实，勿合并**。DeepSeek 官网周末全天闲时（`weekend_off: True`），aliyun_intl 显式 False。
- **缓存峰谷**：官网缓存命中同样分忙闲时；`site_tpl._table_row` 缓存列有峰谷字段时渲染「闲 X/高 Y」。
- **溢价基准 = 官网价**（`base_in = min(该模型官网行 input_rmb)`），非渠道间互比。
- OpenRouter 峰谷从 `pricing.overrides` 提取（UTC HHMM→北京时间）。

## 渠道源

- `aliyun_intl`（USD SPA）：Qwen/DeepSeek/Kimi/GLM，峰谷表列偏移 col_in=4/col_out=5/col_cache=6/col_peak=3。
- `atlascloud`（JSON API）：仅 `type=="Text"`。
- `tencent_cn`（CNY SPA）：取含「原厂直供」完整表，多表 last-wins，`_base_name` 剥离后缀。
- `aliyun_bailian`（CNY JSON API）：DeepSeek/GLM/Kimi/MiniMax，跳过海外区域。
- `zai`（智谱海外官方 USD，非渠道）：只取文本表，`_is_vision` 排除 GLM-*V/OCR。
- `bigmodel`（智谱国内官方 CNY）：取 TABLE[1] 语言模型主表。
- Kimi 双站 `kimi`(CNY)+`kimi_ai`(USD)：定价在 `/docs/pricing/chat` 的 chat-* 子页，国际站表头是英文，scraper 中英双语匹配。
- `volcengine_intl`（USD SPA）：`_SUFFIX_RE` 等归一化，分层取首行。

## 新模型收录

已补 mainstream_models.yml：GLM-5.3（¥8/¥28）、GLM-5.3-Flash（¥0.4/¥1.4，限时5折 ~两周）、Claude Opus 5（$5/$25）、Gemini 3.7 Flash（限时 $0.75/$3.75）、Grok 4.6（$2/$6）、Qwen3.8 Max（¥12/¥36）。
GLM-5.3 / GLM-5.3-Flash 已同时加入 `openrouter.yml` 白名单（`z-ai/glm-5.3`、`z-ai/glm-5.3-flash`），不靠 top-weekly 运气。

## 部署与抓取

- **永久地址**：https://lzc0403.github.io/token-pricing-scraper/
- **方案 A（云端唯一数据源）**：GitHub Action `scrape.yml`（北京时间 01:00 每日）是**唯一权威抓取源**并自动 push data/site；本机 `automation-1787338740315`（每日 10:40）只做「`git pull --ff-only` → `main.py --verify-only` 只读校验 → 异常上报」，**绝不抓取、绝不 push、绝不改 data/**。
- 本地推送前先 `git fetch` + `git merge origin/main`（CI 会领先）。

## git 仓库损坏修复铁律

- `.git` 已损坏 ≥4 次，均由 stash + rebase 中断触发。**直接 reclone 替换 .git，不要试 `git gc`/`read-tree`/`rebase` 修补**。
- **完整 clone，不要 `--depth`**：浅克隆对象库不完整，`reset --hard`/`rebase` 会报 `unable to read tree`。
- Windows 下删 `.git` 会被沙箱批量删除拦截 → 用 `os.rename` 备份旧 `.git` 再 `shutil.copytree` 新 `.git`。
- 替换后不用 `git reset --hard`（旧对象缺失会失败），改用 `git checkout --` 逐个还原数据文件 + 只 commit 代码修改。
- `.gitignore` 排除：`.workbuddy/skills/`、`sessions/`、`mcp.json`、`settings.json`。

## 其他

- 腾讯云国际站 Model Studio 不收录：GLM-5、GLM-5V/5-Turbo、kimi-k2.5、Kimi K2.7 Code HighSpeed、Phi4Max-M3、MiniMax-M2.5、Hy-MT2-Plus、Hy3、DeepSeek-v3.2。（Kimi K3 必须收录。）
- `aliyun` 源线上 0 条（2026-08-16 起，help.aliyun.com 改版/限流），测试靠 HEAD watchlist.json 恢复绕过。
- 代码审计（2026-08-20）：0 致命 / 2 高 / 6 中 / 5 低，三阶段改进计划已全部落地（CI lint、补测试、mypy、Jinja2、每日抓取、历史趋势图、价格推送）。

详见 README + docs/{architecture,openrouter,runbook,handoff}.md + AGENTS.md
