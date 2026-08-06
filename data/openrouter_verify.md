# OpenRouter 二次验证报告

- 时间：2026-08-06 17:21:06
- 抓取时间：2026-08-06T17:20:55.362596+00:00
- 结果：❌ 未通过
- 原始模型数：399
- 解析条数：23
- 白名单：11（缺失 0 / API 无 0）
- 可疑：2（high 2 / med 0 / low 0）

## 可疑项
- [high] `OR_PRICE_MISMATCH` deepseek/deepseek-v4-flash — input 换算不一致 exp=0.0882 got=0.09
- [high] `OR_PRICE_MISMATCH` deepseek/deepseek-v4-flash — output 换算不一致 exp=0.1764 got=0.18

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
- Kimi K2.6 (`moonshotai/kimi-k2.6`) in=0.57 out=2.4
- Kimi K3 (`moonshotai/kimi-k3`) in=3.0 out=15.0
- Hy3 (`tencent/hy3`) in=0.132 out=0.528
- MiMo-V2.5 (`xiaomi/mimo-v2.5`) in=0.14 out=0.28
- DeepSeek V4 Flash 0731 (`deepseek/deepseek-v4-flash-0731`) in=0.09 out=0.18
- GPT-5.6 Luna (`openai/gpt-5.6-luna`) in=0.1 out=0.6
