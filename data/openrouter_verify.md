# OpenRouter 二次验证报告

- 时间：2026-07-26 18:50:26
- 抓取时间：2026-07-26T18:50:17.406442+00:00
- 结果：❌ 未通过
- 原始模型数：343
- 解析条数：23
- 白名单：11（缺失 0 / API 无 0）
- 可疑：2（high 2 / med 0 / low 0）

## 可疑项
- [high] `OR_PRICE_MISMATCH` deepseek/deepseek-v4-flash — input 换算不一致 exp=0.14 got=0.09
- [high] `OR_PRICE_MISMATCH` deepseek/deepseek-v4-flash — output 换算不一致 exp=0.28 got=0.18

## 解析样本
- GPT-4o (`openai/gpt-4o`) in=2.5 out=10.0
- GPT-5 (`openai/gpt-5`) in=1.25 out=10.0
- Claude Sonnet 5 (`anthropic/claude-sonnet-5`) in=2.0 out=10.0
- Claude Opus 4.8 (`anthropic/claude-opus-4.8`) in=5.0 out=25.0
- Gemini 2.5 Pro (`google/gemini-2.5-pro`) in=1.25 out=10.0
- Gemini 2.5 Flash (`google/gemini-2.5-flash`) in=0.3 out=2.5
- DeepSeek V4 Pro (`deepseek/deepseek-v4-pro`) in=0.435 out=0.87
- DeepSeek V4 Flash (`deepseek/deepseek-v4-flash`) in=0.09 out=0.18
- MiniMax M3 (`minimax/minimax-m3`) in=0.3 out=1.2
- Kimi K2.6 (`moonshotai/kimi-k2.6`) in=0.646 out=2.72
- Kimi K3 (`moonshotai/kimi-k3`) in=3.0 out=15.0
- MiMo-V2.5 (`xiaomi/mimo-v2.5`) in=0.14 out=0.28
- Hy3 (`tencent/hy3`) in=0.132 out=0.528
- GLM 5.2 (`z-ai/glm-5.2`) in=0.6692 out=2.1032
- Step 3.7 Flash (`stepfun/step-3.7-flash`) in=0.2 out=1.15
