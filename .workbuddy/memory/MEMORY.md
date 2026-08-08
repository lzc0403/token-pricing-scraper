# 项目长期记忆 · token 定价

更新：2026-08-07

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
