# 项目长期记忆 · token 定价

更新：2026-07-18

## 核心决策

- 站点由 `core/site.py` 生成，禁止手改 `site/index.html` 后指望保留。
- 展示：ModelMesh→胜算云；网页汇率交互默认 7.0。
- 海外：仅热门主力，含 GPT-4o；新品用 `config/new_models.yml` 监听。
- OpenRouter：`scrapers/openrouter.py` + `config/openrouter.yml`；原始缓存 `data/openrouter_raw.json`；验证 `core/openrouter_verify.py`。
- 渠道页包含 OpenRouter（USD）；与官网/海外官方参考分区展示。

## 部署

CloudStudio: https://0946e061d8e1463e8946a119b5aa0afb.app.codebuddy.work

## 文档

见 README + docs/{architecture,openrouter,runbook,handoff}.md + AGENTS.md
