# 项目长期记忆 · token 定价

更新：2026-07-20

## 核心决策

- 站点由 `core/site.py` 生成，禁止手改 `site/index.html` 后指望保留。
- 展示：ModelMesh→胜算云；网页汇率交互默认 7.0。
- 海外：仅热门主力，含 GPT-4o；新品用 `config/new_models.yml` 监听。
- OpenRouter：`scrapers/openrouter.py` + `config/openrouter.yml`；原始缓存 `data/openrouter_raw.json`；验证 `core/openrouter_verify.py`。
- 渠道页包含 OpenRouter（USD）；与官网/海外官方参考分区展示。

## 部署

- **永久地址（GitHub Pages）**：https://lzc0403.github.io/token-pricing-scraper/ （public 仓库 + Actions 部署，每周日 18:00 UTC 自动抓取并发布 site/；workflow_dispatch 可手动触发）
- 旧 CloudStudio 临时沙箱已弃用（每次换 URL、会过期）
- CI 数据提交模式：scrape.yml 的「Commit results」会自动 push data/site 到 origin/main，本地 main 会落后于远程 → 任何本地推送前先 `git fetch` + `git merge origin/main`
- 部署源 = `main` 分支（含 feature/mainstream-model-sections 全部特性）

## 文档

见 README + docs/{architecture,openrouter,runbook,handoff}.md + AGENTS.md
