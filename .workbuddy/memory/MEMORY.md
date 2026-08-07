# 项目长期记忆 · token 定价

更新：2026-08-07

## 核心决策

- 站点由 `core/site.py` 生成，禁止手改 `site/index.html` 后指望保留。
- 展示：ModelMesh→胜算云；网页汇率交互默认 7.0。
- 海外：仅热门主力，含 GPT-4o；新品用 `config/new_models.yml` 监听。
- OpenRouter：`scrapers/openrouter.py` + `config/openrouter.yml`；原始缓存 `data/openrouter_raw.json`；验证 `core/openrouter_verify.py`。
- 渠道页包含 OpenRouter（USD）；与官网/海外官方参考分区展示。
- 阿里云：国内站 CNY（help.aliyun.com）+ 国际站 USD（modelstudio.console.alibabacloud.com），同一模型两站价格不同，需区分标注。
- **厂商价格查询入口**（portal 区块）：footer 上方，14 个厂商链接，CNY/USD 双色标签区分国内外站。

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
