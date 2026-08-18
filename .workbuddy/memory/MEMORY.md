# 项目长期记忆 · token 定价

更新：2026-08-17

## 核心决策

- 站点由 `core/site.py` 生成，禁止手改 `site/index.html` 后指望保留。
- 展示：ModelMesh→胜算云；网页汇率交互默认 7.0。
- 海外：仅热门主力，含 GPT-4o；新品用 `config/new_models.yml` 监听。
- OpenRouter：`scrapers/openrouter.py` + `config/openrouter.yml`；原始缓存 `data/openrouter_raw.json`；验证 `core/openrouter_verify.py`。
- **OpenRouter 价格铁律**：一律用 `openrouter.ai/api/v1/models` 返回的真实价；**禁止**在 `openrouter.yml` 写 `input_price/output_price` override 去套用第三方转售商（如 AtlasCloud）的报价。2026-08-07 曾误把 AtlasCloud 的 $0.09/$0.18 写进 V4 Flash override，已删除，恢复真实价 $0.0882/$0.1764。
- 渠道页包含 OpenRouter（USD）；与官网/海外官方参考分区展示。
- **阿里云国际站**抓取：`config/sources.yml` 的 `aliyun_intl` 源（USD, js:true SPA）→ `scrapers/aliyun_intl.py`，抓 Qwen/DeepSeek/Kimi/GLM 共 9 模型（含 qwen3.8-max）。站点内为独立「阿里云国际站」海外渠道分组，与国内阿里云（CNY）区分。
- **AtlasCloud 渠道源**：`config/sources.yml` 的 `atlascloud` 源（USD，JSON API `console.atlascloud.ai/api/v1/models`）→ `scrapers/atlascloud.py`。仅取 `type=="Text"` 的 LLM 模型，命中目标后与现有 canonical 对齐展示；此前误写进 OpenRouter 的 AtlasCloud 价现在正确归属 AtlasCloud 渠道分组。
- 页面默认缩放：`core/site.py` CSS `html{zoom:1.1}`（同时保留 `overflow-x:clip` 防滚动条），桌面视口下无溢出、无裁切。
- **2026-08-08 视觉统一**：引入 `--sp-*` 间距、`--r-sm/--r/--r-lg` 圆角、`--sh-1/--sh-2/--sh-3` 阴影三级设计令牌；body 背景 `--canvas` 浅灰、卡片 `#fff` 浮起；主色 `theme-color` 统一为 `#2BAE85`；价格单元格采用 `px-val`/`px-cur`/`js-rmb-hint` 三层结构；补齐 `.market-tabs` 等缺失样式。任何后续样式改动必须保持 JS 依赖类名（`js-cny-main`/`js-rmb-hint`/`js-row` 等）不变。
- **2026-08-09 官方行标识优化**：官方定价表不再整行涂 `#fff8e7` 黄色（刺眼、破坏白卡片浮起感）。改为白底 + 左侧 2px 品牌绿内阴影线标识；`.tag-official` 同步改用品牌绿软底；hover 统一 `#f8fafb`。
- 阿里云：国内站 CNY（help.aliyun.com）+ 国际站 USD（modelstudio.console.alibabacloud.com），同一模型两站价格不同，需区分标注。
- **腾讯云国内站渠道源**：`config/sources.yml` 的 `tencent_cn` 源（CNY，js:true SPA，`cloud.tencent.com/document/product/1823/130055`）→ `scrapers/tencent_cn.py`。页面语言模型表含「推理输入/推理输出/缓存命中」（元/百万 tokens），同模型分「原厂直供」与「腾讯云自建」两档，用 `condition` 区分；解析时取含「原厂直供」的完整表，多表 last-wins 避免概览表低价覆盖。
- **阿里云百炼渠道源**：`config/sources.yml` 的 `aliyun_bailian` 源（CNY，js:false JSON API）→ `scrapers/bailian.py`。控制台 SPA 不公开渲染价格表，改走 `help.aliyun.com/help/json/document_detail.json?alias=/model-studio/model-pricing` 接口，覆盖 DeepSeek / GLM / Kimi / MiniMax；缓存命中价按输入单价 × 20% 计算。
- **2026-08-10 DeepSeek 来源类型 condition 标注铁律**：用户规则——「未在页面标注『原厂直供』的即云厂商自部署」。各 scraper 对 DeepSeek 模型须按此规则填 `condition` 字段：腾讯云两站（`tencent.py`/`tencent_cn.py`）识别「原厂直供」后缀→`原厂直供`，同名无后缀行→`腾讯云自建`；阿里云国际站/百炼（`aliyun_intl.py`/`bailian.py`）DeepSeek 行无标记→`阿里云自部署`；非 DeepSeek 模型不补标。`core/site.py` 渲染层 `_normalize_row` 透传 condition，`_table_row` 在「来源」列 `<span class="pill">` 旁加 `<span class="tag tag-cond">` 小标签展示；新增 `.tag-cond` CSS。
- **2026-08-11 SOURCE_LABELS 简化 + condition 清理**：`tencent`→`腾讯云国际`、`tencent_cn`→`腾讯云CN`、`aliyun_intl`→`阿里云国际`（全去括号精简）。condition 字段仅保留有意义的来源类型（原厂直供/腾讯云自建/阿里云自部署）与 token 长度条件；三类冗余 condition 一律置 None：①atlascloud.py 所有行（原 `AtlasCloud (atlascloud.ai) · USD/1M tokens`，与 pill 重复）；②openrouter.py 所有行（原 `id=xxx | note`，内部备注，原始 id 仍存于 `openrouter_id` 字段供 verify）；③aliyun_intl.py 非 DeepSeek 行（原 `阿里云国际站 Model Studio (ap-southeast-1)`，区域信息已由 SOURCE_LABELS 表达）。
- **2026-08-16 智谱 Z.ai 海外官方渠道源**：`config/sources.yml` 的 `zai` 源（USD，js:false，`docs.z.ai/guides/overview/pricing`）→ `scrapers/zai.py`。只取文本模型表（表头含 Model+Input+Output），收录 GLM-5.2/5.1/5/5-Turbo/4.7/4.6/4.5/4.5-Air 等 12 条；视觉模型（GLM-5V/4.6V/4.5V/OCR）用正则 `glm-\d+(?:\.\d+)?v` + `ocr` 子串过滤。**关键：zai 不在 CHANNEL_SOURCES，而是官方 USD 源**——与 `bigmodel`（智谱国内站 CNY）对称，`_is_official_any_currency` 扩展支持 GLM+(bigmodel|zai) 双币种官方识别，USD 行进官方区海外表。GLM-5.3 仅 Coding Plan 订阅提供、API 未开放，定价页无 → 抓不到属正常。
- **2026-08-16 `_is_official_any_currency` 双币种官方识别铁律**：厂商国内站(CNY)+海外站(USD)均为官方原价。当前支持 DeepSeek（deepseek CNY + deepseek_us USD）与 GLM（bigmodel CNY + zai USD）。新增多站厂商时在此函数加 `if str(canon).startswith("<前缀>") and src in ("<国内id>", "<海外id>")` 分支。注意 site.py:668 `if x["source"] == "deepseek_us" or not already_cny` 的去重逻辑用 source id 硬编码，新增 USD 官方源需检查此处。
- **2026-08-16 BytePlus 火山云海外渠道源**：`config/sources.yml` 的 `volcengine_intl` 源（USD，js:true SPA，`docs.byteplus.com/en/docs/ModelArk/1544106`）→ `scrapers/volcengine_intl.py`。仅抓「大语言模型-在线推理(标准)」表，收录 DeepSeek（v4-pro/v4-flash/v3.2）+ GLM（5-2/4-7）系列；`_SUFFIX_RE` 剥离日期快照后缀（-260425 等），`_GA_SUFFIX_RE` 剥离 `-ga-260731`，`_VERSION_DASH_RE` 转 `glm-5-2`→`glm-5.2`；DeepSeek 标 condition=`火山引擎自部署`，GLM 留空。分层定价只保留首行（基准档）。
- **2026-08-16 DeepSeek 双站 + 峰谷 + 正式版归一**：`deepseek`（中文站 CNY）+ `deepseek_us`（英文站 USD）并列官方区。0731=Flash 正式版、0813=Pro 正式版，`_clean_model()` 剥离「0731 正式版」「0813 正式版」「（新价格）」标记后归一到标准名，版本号进 condition。峰谷计费来自腾讯云国际站（tencent 源），`peak_cond` 列值（空闲时段/高峰时段）加入 condition，高峰 9:00-12:00/14:00-18:00 全价、空闲减半，8/17 生效。官方区+海外渠道面板均有 `.peak-note` 说明条。
- **2026-08-16 新模型收录**：GLM-5.3（canonical+aliases，Z.ai 定价页无，Coding Plan 订阅专属）；Claude Opus 5（$5/$25，Fast $10/$50，`_CLAUDE_OFFICIAL` 白名单加 `"Claude Opus 5": ("Opus 5", "claude-opus-5")`）；Gemini 3.7 Flash（限时 $0.75/$3.75，之后 $1.50/$7.50）；Grok 4.6（$2/$6，缓存 $0.50）。后三者进海外主流目录+OpenRouter 白名单。
- **2026-08-16 git 仓库损坏修复**：`.git` 对象库物理损坏（`.github/workflows` tree 不可读 + index cache-tree 损坏 + reflog 损坏）。修复方案：`git clone --depth 1 origin /tmp/tps-restore` → `cp -rv .git/objects/* .git/objects/` → `rm .git/index && git read-tree HEAD`。后续仍有 `geometric-repack` 警告，建议 `git gc --prune=now` 或完整 reclone。
- **2026-08-16 aliyun 源线上抓取 0 条**：`help.aliyun.com` 页面可能改版/限流，线上 `aliyun: 0 条`。测试 `test_official_rows_vendor_grouped_with_qwen_cache` 依赖 aliyun 有 Qwen3.7-Max/Plus 数据，通过从 HEAD watchlist.json 恢复 aliyun 记录绕过。后续需排查 aliyun scraper 失效根因。
- **2026-08-17 DeepSeek 官网页面改版为峰谷定价（重大）**：`api-docs.deepseek.com` 中英文站定价表从单档改为峰谷双档结构。新表结构：每类价格（缓存命中/缓存未命中/输出）拆成两行，第一行 `[总标签?, 类别, 子标签(空闲时段/OFF-PEAK), 值1, 值2]`，第二行 `[子标签(高峰时段/PEAK), 值1, 值2]`。`scrapers/deepseek.py` 已全面重写：状态机式解析（`last_field` 承接高峰行类别），输出 `peak_input_low/high`、`peak_output_low/high`、`peak_cache_low/high` 6 字段 + `condition="峰谷计费"`，`input/output/cache_hit` 主字段取空闲价（与历史单档语义最接近）。**新价格大幅上涨**：V4 Pro CNY 输入空闲 ¥4.5→高峰 ¥9.0（旧 ¥3），输出空闲 ¥13.5→高峰 ¥27.0（旧 ¥6）；USD 对称。`_rec()` 不支持 peak_* 参数，手动 dict 扩展。`core/site.py` `_price_cells` CNY 模式已修：`peak_input_rmb_low` 为 None 时 fallback 到 `peak_input_low`（CNY 源原币种即 CNY 无需换算）。
- **2026-08-17 自动化任务缺口**：本地无 token 定价每日抓取自动化任务（automation list 确认），仅靠 GitHub Actions 每周日 18:00 UTC 跑。用户期望每日抓取但实际未配置。如需每日抓取，需新建 automation 或本地 cron。
- **厂商价格查询入口**（portal 区块）：footer 上方，17 个厂商链接卡片，CNY/USD 双色标签（绿 ¥ 国内官网 / 蓝 $ 英文·国际站）区分。双卡厂商：阿里云（国内 help.aliyun.com / 国际 modelstudio.console）、腾讯云（国内 tencentcloud.com/zh / 国际 tencentcloud.com）、DeepSeek（中文 api-docs.deepseek.com/zh-cn / 英文 api-docs.deepseek.com/quick_start/pricing）、Kimi（中文 platform.kimi.com/docs/pricing/chat-k3 / 英文 platform.moonshot.ai）、MiniMax（中文 platform.minimaxi.com / 英文 platform.minimax.io/docs/guides/pricing-paygo）。门户标题下 `.ph` 一行说明「同模型 ¥/$ 双定价」逻辑。

## 部署

- **永久地址（GitHub Pages）**：https://lzc0403.github.io/token-pricing-scraper/ （public 仓库 + Actions 部署，每周日 18:00 UTC 自动抓取并发布 site/；workflow_dispatch 可手动触发）
- 旧 CloudStudio 临时沙箱已弃用（每次换 URL、会过期）
- CI 数据提交模式：scrape.yml 的「Commit results」会自动 push data/site 到 origin/main，本地 main 会落后于远程 → 任何本地推送前先 `git fetch` + `git merge origin/main`
- 部署源 = `main` 分支（含 feature/mainstream-model-sections 全部特性）

## 文档

见 README + docs/{architecture,openrouter,runbook,handoff}.md + AGENTS.md

## 模型清单排除项（2026-08-07 确认）

腾讯云国际站 Model Studio 截图（USD/百万 tokens）中，以下模型**明确不收录**：
- GLM-5、GLM-5V-Turbo / GLM-5-Turbo
- kimi-k2.5、Kimi K2.7 Code HighSpeed
- ~~Kimi K3~~（**必须收录**，2026-08-07 修正：K3 是核心模型，保留不动）
- Phi4Max-M3（分段）
- MiniMax-M2.5
- Hy-MT2-Plus
- Hy3、DeepSeek-v3.2（与官方/腾讯云已收录版本重复或价不一致，不单列）

截图页面来源推测：腾讯云国际站 Model Studio（含「原厂直供 / 腾讯云自建」双渠道标签）。当前项目 GitHub Pages 按 source 字段（tencent/openrouter/deepseek）分区，无「原厂直供/腾讯云自建」标签。
