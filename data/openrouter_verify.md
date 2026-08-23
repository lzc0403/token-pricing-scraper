# OpenRouter 二次验证报告

- 时间：2026-08-23 17:13:51
- 抓取时间：2026-08-23T17:10:38.849069+00:00
- 结果：✅ 通过
- 原始模型数：422
- 解析条数：38
- 白名单：27（缺失 0 / API 无 1）
- 可疑：1（high 0 / med 0 / low 1）

## 可疑项
- [low] `OR_WHITELIST_ABSENT` openai/gpt-5.6 — 白名单模型当前 OpenRouter API 无此 id: openai/gpt-5.6

## 解析样本
- GPT-4o (`openai/gpt-4o`) in=2.5 out=10.0
- GPT-5 (`openai/gpt-5`) in=1.25 out=10.0
- GPT-5.5 (`openai/gpt-5.5`) in=5.0 out=30.0
- GPT-5.5 Pro (`openai/gpt-5.5-pro`) in=30.0 out=180.0
- GPT-5.6 Terra (`openai/gpt-5.6-terra`) in=2.0 out=12.0
- GPT-5.6 Luna (`openai/gpt-5.6-luna`) in=0.2 out=1.2
- Claude Sonnet 5 (`anthropic/claude-sonnet-5`) in=2.0 out=10.0
- Claude Sonnet 4.6 (`anthropic/claude-sonnet-4.6`) in=3.0 out=15.0
- Claude Sonnet 4.5 (`anthropic/claude-sonnet-4.5`) in=3.0 out=15.0
- Claude Opus 4.8 (`anthropic/claude-opus-4.8`) in=5.0 out=25.0
- Claude Opus 4.7 (`anthropic/claude-opus-4.7`) in=5.0 out=25.0
- Claude Opus 4.6 (`anthropic/claude-opus-4.6`) in=5.0 out=25.0
- Claude Opus 4.5 (`anthropic/claude-opus-4.5`) in=5.0 out=25.0
- Claude Opus 5 (`anthropic/claude-opus-5`) in=5.0 out=25.0
- Claude Fable 5 (`anthropic/claude-fable-5`) in=10.0 out=50.0
