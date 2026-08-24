# 大模型 Token 定价周报

> 生成时间：2026-08-24 03:25:23

## 一、目标模型跨源对照（已换算人民币）

| 模型 | 源 | 输入¥ | 输出¥ | 缓存命中 | 货币 | 原始价(输入/输出) | 上下文 |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| Claude Fable 5 | openrouter | 70 ¥ | 350 ¥ | 1 USD | USD | 10 USD / 50 USD | 1M |
| Claude Haiku 4.5 | openrouter | 7 ¥ | 35 ¥ | 0.1 USD | USD | 1 USD / 5 USD | 200K |
| Claude Opus 4.5 | openrouter | 35 ¥ | 175 ¥ | 0.5 USD | USD | 5 USD / 25 USD | 200K |
| Claude Opus 4.6 | openrouter | 35 ¥ | 175 ¥ | 0.5 USD | USD | 5 USD / 25 USD | 1M |
| Claude Opus 4.7 | openrouter | 35 ¥ | 175 ¥ | 0.5 USD | USD | 5 USD / 25 USD | 1M |
| Claude Opus 4.8 | openrouter | 35 ¥ | 175 ¥ | 0.5 USD | USD | 5 USD / 25 USD | 1M |
| Claude Opus 5 | openrouter | 35 ¥ | 175 ¥ | 0.5 USD | USD | 5 USD / 25 USD | 1M |
| Claude Sonnet 4.5 | openrouter | 21 ¥ | 105 ¥ | 0.3 USD | USD | 3 USD / 15 USD | 1M |
| Claude Sonnet 4.6 | openrouter | 21 ¥ | 105 ¥ | 0.3 USD | USD | 3 USD / 15 USD | 1M |
| Claude Sonnet 5 | openrouter | 14 ¥ | 70 ¥ | 0.2 USD | USD | 2 USD / 10 USD | 1M |
| DeepSeek V3.2 | aliyun_bailian | 2 ¥ | 3 ¥ | 0.4 CNY | CNY | 2 CNY / 3 CNY | - |
| DeepSeek V3.2 | atlascloud | 1.82 ¥ | 2.66 ¥ | 0.13 USD | USD | 0.26 USD / 0.38 USD | 163K |
| DeepSeek V3.2 | tencent | 1.96 ¥ | 2.94 ¥ | 0.056 USD | USD | 0.28 USD / 0.42 USD | - |
| DeepSeek V3.2 | volcengine_intl | 1.96 ¥ | 2.94 ¥ | 0.056 USD | USD | 0.28 USD / 0.42 USD | - |
| DeepSeek V4 Flash | aliyun_bailian | 1 ¥ | 2 ¥ | 0.2 CNY | CNY | 1 CNY / 2 CNY | - |
| DeepSeek V4 Flash | aliyun_intl | 3.08 ¥ | 9.24 ¥ | 0.044 USD | USD | 0.44 USD / 1.32 USD | - |
| DeepSeek V4 Flash | atlascloud | 0.98 ¥ | 1.96 ¥ | 0.028 USD | USD | 0.14 USD / 0.28 USD | 1.04858M |
| DeepSeek V4 Flash | deepseek | 3 ¥ | 9 ¥ | 0.1 CNY | CNY | 3 CNY / 9 CNY | 1M |
| DeepSeek V4 Flash | deepseek_us | 3.08 ¥ | 9.24 ¥ | 0.014 USD | USD | 0.44 USD / 1.32 USD | 1M |
| DeepSeek V4 Flash | openrouter | 0.4018 ¥ | 0.8036 ¥ | 0.01148 USD | USD | 0.0574 USD / 0.1148 USD | 1.04858M |
| DeepSeek V4 Flash | tencent | 1.54 ¥ | 4.62 ¥ | 0.007 USD | USD | 0.22 USD / 0.66 USD | - |
| DeepSeek V4 Flash | tencent | 3.08 ¥ | 9.24 ¥ | 0.014 USD | USD | 0.44 USD / 1.32 USD | - |
| DeepSeek V4 Flash | tencent | 0.98 ¥ | 1.96 ¥ | 0.028 USD | USD | 0.14 USD / 0.28 USD | - |
| DeepSeek V4 Flash | tencent_cn | 1 ¥ | 2 ¥ | 0.2 CNY | CNY | 1 CNY / 2 CNY | - |
| DeepSeek V4 Flash | volcengine_intl | 3.08 ¥ | 9.24 ¥ | 0.014 USD | USD | 0.44 USD / 1.32 USD | - |
| DeepSeek V4 Pro | aliyun_bailian | 12 ¥ | 24 ¥ | 2.4 CNY | CNY | 12 CNY / 24 CNY | - |
| DeepSeek V4 Pro | aliyun_intl | 9.24 ¥ | 27.72 ¥ | 0.132 USD | USD | 1.32 USD / 3.96 USD | - |
| DeepSeek V4 Pro | atlascloud | 11.76 ¥ | 23.66 ¥ | 0.13 USD | USD | 1.68 USD / 3.38 USD | 1.04858M |
| DeepSeek V4 Pro | deepseek | 9 ¥ | 27 ¥ | 0.3 CNY | CNY | 9 CNY / 27 CNY | 1M |
| DeepSeek V4 Pro | deepseek_us | 9.24 ¥ | 27.72 ¥ | 0.044 USD | USD | 1.32 USD / 3.96 USD | 1M |
| DeepSeek V4 Pro | modelmesh | 3 ¥ | 6 ¥ | - | CNY | 3 CNY / 6 CNY | 1000K |
| DeepSeek V4 Pro | openrouter | 3.68323 ¥ | 7.36646 ¥ | 0.043848 USD | USD | 0.526176 USD / 1.05235 USD | 1.04858M |
| DeepSeek V4 Pro | tencent | 4.62 ¥ | 13.86 ¥ | 0.022 USD | USD | 0.66 USD / 1.98 USD | - |
| DeepSeek V4 Pro | tencent | 9.24 ¥ | 27.72 ¥ | 0.044 USD | USD | 1.32 USD / 3.96 USD | - |
| DeepSeek V4 Pro | tencent | 12.18 ¥ | 24.36 ¥ | 0.145 USD | USD | 1.74 USD / 3.48 USD | - |
| DeepSeek V4 Pro | tencent_cn | 12 ¥ | 24 ¥ | 1 CNY | CNY | 12 CNY / 24 CNY | - |
| DeepSeek V4 Pro | volcengine_intl | 9.24 ¥ | 27.72 ¥ | 0.044 USD | USD | 1.32 USD / 3.96 USD | - |
| DeepSeek V4 Pro 0813 | openrouter | 7.854 ¥ | 23.562 ¥ | 0.0374 USD | USD | 1.122 USD / 3.366 USD | 1.04858M |
| Doubao Seed 2.1 Pro | atlascloud | 6.3 ¥ | 31.5 ¥ | 0.18 USD | USD | 0.9 USD / 4.5 USD | 262K |
| Doubao Seed 2.1 Pro | modelmesh | 6 ¥ | 30 ¥ | - | CNY | 6 CNY / 30 CNY | 256K |
| Doubao Seed 2.1 Pro | volcengine | 6 ¥ | 30 ¥ | 1.2 CNY | CNY | 6 CNY / 30 CNY | - |
| Doubao Seed 2.1 Turbo | atlascloud | 3.15 ¥ | 15.75 ¥ | 0.09 USD | USD | 0.45 USD / 2.25 USD | 262K |
| Doubao Seed 2.1 Turbo | modelmesh | 3 ¥ | 15 ¥ | - | CNY | 3 CNY / 15 CNY | 256K |
| Doubao Seed 2.1 Turbo | volcengine | 3 ¥ | 15 ¥ | 0.6 CNY | CNY | 3 CNY / 15 CNY | - |
| GLM-4.7 | aliyun_bailian | 3 ¥ | 14 ¥ | 0.6 CNY | CNY | 3 CNY / 14 CNY | - |
| GLM-4.7 | atlascloud | 3.64 ¥ | 12.95 ¥ | 0.12 USD | USD | 0.52 USD / 1.85 USD | 202K |
| GLM-4.7 | bigmodel | 2 ¥ | 8 ¥ | - | CNY | 2 CNY / 8 CNY | - |
| GLM-4.7 | volcengine_intl | 4.2 ¥ | 15.4 ¥ | 0.11 USD | USD | 0.6 USD / 2.2 USD | - |
| GLM-4.7 | zai | 4.2 ¥ | 15.4 ¥ | 0.11 USD | USD | 0.6 USD / 2.2 USD | - |
| GLM-5.1 | aliyun_bailian | 6 ¥ | 24 ¥ | 1.2 CNY | CNY | 6 CNY / 24 CNY | - |
| GLM-5.1 | aliyun_intl | 9.8 ¥ | 30.8 ¥ | 0.26 USD | USD | 1.4 USD / 4.4 USD | - |
| GLM-5.1 | atlascloud | 8.82 ¥ | 27.72 ¥ | 0.234 USD | USD | 1.26 USD / 3.96 USD | 202K |
| GLM-5.1 | bigmodel | 6 ¥ | 24 ¥ | - | CNY | 6 CNY / 24 CNY | - |
| GLM-5.1 | modelmesh | 6 ¥ | 24 ¥ | - | CNY | 6 CNY / 24 CNY | 200K |
| GLM-5.1 | tencent | 5.88 ¥ | 23.52 ¥ | 0.182 USD | USD | 0.84 USD / 3.36 USD | - |
| GLM-5.1 | tencent | 7.84 ¥ | 27.44 ¥ | 0.28 USD | USD | 1.12 USD / 3.92 USD | - |
| GLM-5.1 | tencent_cn | 10.254 ¥ | 32.228 ¥ | 1.904 CNY | CNY | 10.254 CNY / 32.228 CNY | - |
| GLM-5.1 | zai | 9.8 ¥ | 30.8 ¥ | 0.26 USD | USD | 1.4 USD / 4.4 USD | - |
| GLM-5.2 | aliyun_bailian | 8 ¥ | 28 ¥ | 1.6 CNY | CNY | 8 CNY / 28 CNY | - |
| GLM-5.2 | aliyun_intl | 9.8 ¥ | 30.8 ¥ | 0.28 USD | USD | 1.4 USD / 4.4 USD | - |
| GLM-5.2 | atlascloud | 8.82 ¥ | 27.72 ¥ | 0.234 USD | USD | 1.26 USD / 3.96 USD | 1.04858M |
| GLM-5.2 | bigmodel | 8 ¥ | 28 ¥ | - | CNY | 8 CNY / 28 CNY | - |
| GLM-5.2 | modelmesh | 8 ¥ | 28 ¥ | - | CNY | 8 CNY / 28 CNY | 1000K |
| GLM-5.2 | openrouter | 6.762 ¥ | 21.252 ¥ | 0.1932 USD | USD | 0.966 USD / 3.036 USD | 1.04858M |
| GLM-5.2 | tencent | 7.84 ¥ | 27.44 ¥ | 0.28 USD | USD | 1.12 USD / 3.92 USD | - |
| GLM-5.2 | tencent_cn | 10.254 ¥ | 32.2282 ¥ | 1.9044 CNY | CNY | 10.254 CNY / 32.2282 CNY | - |
| GLM-5.2 | volcengine_intl | 9.8 ¥ | 30.8 ¥ | 0.26 USD | USD | 1.4 USD / 4.4 USD | - |
| GLM-5.2 | zai | 9.8 ¥ | 30.8 ¥ | 0.26 USD | USD | 1.4 USD / 4.4 USD | - |
| GLM-5.3 | aliyun_bailian | 8 ¥ | 28 ¥ | 1.6 CNY | CNY | 8 CNY / 28 CNY | - |
| GLM-5.3 | atlascloud | 11.466 ¥ | 36.036 ¥ | 0.304 USD | USD | 1.638 USD / 5.148 USD | 1.04858M |
| GLM-5.3 | bigmodel | 8 ¥ | 28 ¥ | - | CNY | 8 CNY / 28 CNY | - |
| GLM-5.3 | modelmesh | 8 ¥ | 28 ¥ | - | CNY | 8 CNY / 28 CNY | 1000K |
| GLM-5.3 | tencent | 7.7812 ¥ | 27.2349 ¥ | 0.2779 USD | USD | 1.1116 USD / 3.8907 USD | - |
| GLM-5.3 | tencent_cn | 10.0752 ¥ | 31.665 ¥ | 1.87112 CNY | CNY | 10.0752 CNY / 31.665 CNY | - |
| GLM-5.3 | zai | 9.8 ¥ | 30.8 ¥ | 0.26 USD | USD | 1.4 USD / 4.4 USD | - |
| GPT-4o | openrouter | 17.5 ¥ | 70 ¥ | 1.25 USD | USD | 2.5 USD / 10 USD | 128K |
| GPT-5 | openrouter | 8.75 ¥ | 70 ¥ | 0.125 USD | USD | 1.25 USD / 10 USD | 400K |
| GPT-5.5 | openai | 35 ¥ | 210 ¥ | 0.5 USD | USD | 5 USD / 30 USD | 1M |
| GPT-5.5 | openrouter | 35 ¥ | 210 ¥ | 0.5 USD | USD | 5 USD / 30 USD | 1.05M |
| GPT-5.5 Pro | openai | 210 ¥ | 1260 ¥ | - | USD | 30 USD / 180 USD | 1M |
| GPT-5.5 Pro | openrouter | 210 ¥ | 1260 ¥ | - | USD | 30 USD / 180 USD | 1.05M |
| GPT-5.6 Luna | openai | 1.4 ¥ | 8.4 ¥ | 0.02 USD | USD | 0.2 USD / 1.2 USD | 1M |
| GPT-5.6 Luna | openai | 2.8 ¥ | 12.6 ¥ | 0.04 USD | USD | 0.4 USD / 1.8 USD | 1M |
| GPT-5.6 Luna | openrouter | 1.4 ¥ | 8.4 ¥ | 0.02 USD | USD | 0.2 USD / 1.2 USD | 1.05M |
| GPT-5.6 Sol | openai | 28 ¥ | 140 ¥ | 0.4 USD | USD | 4 USD / 20 USD | 1M |
| GPT-5.6 Sol | openai | 70 ¥ | 315 ¥ | 1 USD | USD | 10 USD / 45 USD | 1M |
| GPT-5.6 Terra | openai | 14 ¥ | 84 ¥ | 0.2 USD | USD | 2 USD / 12 USD | 1M |
| GPT-5.6 Terra | openai | 28 ¥ | 126 ¥ | 0.4 USD | USD | 4 USD / 18 USD | 1M |
| GPT-5.6 Terra | openrouter | 14 ¥ | 84 ¥ | 0.2 USD | USD | 2 USD / 12 USD | 1.05M |
| Gemini 2.5 Flash | openrouter | 2.1 ¥ | 17.5 ¥ | 0.03 USD | USD | 0.3 USD / 2.5 USD | 1.04858M |
| Gemini 2.5 Pro | openrouter | 8.75 ¥ | 70 ¥ | 0.125 USD | USD | 1.25 USD / 10 USD | 1.04858M |
| Gemini 3.7 Flash | openrouter | 2.625 ¥ | 13.125 ¥ | 0.0375 USD | USD | 0.375 USD / 1.875 USD | 1.04858M |
| Grok 4.6 | openrouter | 14 ¥ | 42 ¥ | 0.5 USD | USD | 2 USD / 6 USD | 500K |
| Kimi K2.6 | aliyun_bailian | 6.5 ¥ | 27 ¥ | 1.3 CNY | CNY | 6.5 CNY / 27 CNY | - |
| Kimi K2.6 | atlascloud | 6.65 ¥ | 28 ¥ | 0.16 USD | USD | 0.95 USD / 4 USD | 262K |
| Kimi K2.6 | kimi | 6.5 ¥ | 27 ¥ | 1.1 CNY | CNY | 6.5 CNY / 27 CNY | 262,144 tokens |
| Kimi K2.6 | modelmesh | 6.5 ¥ | 27 ¥ | - | CNY | 6.5 CNY / 27 CNY | 256K |
| Kimi K2.6 | openrouter | 6.65 ¥ | 28 ¥ | 0.16 USD | USD | 0.95 USD / 4 USD | 262K |
| Kimi K2.6 | tencent | 6.006 ¥ | 24.962 ¥ | 0.145 USD | USD | 0.858 USD / 3.566 USD | - |
| Kimi K2.6 | tencent_cn | 6.5 ¥ | 27 ¥ | 1.1 CNY | CNY | 6.5 CNY / 27 CNY | - |
| Kimi K2.7 Code | aliyun_bailian | 6.5 ¥ | 27 ¥ | 1.3 CNY | CNY | 6.5 CNY / 27 CNY | - |
| Kimi K2.7 Code | aliyun_intl | 6.65 ¥ | 28 ¥ | 0.19 USD | USD | 0.95 USD / 4 USD | - |
| Kimi K2.7 Code | atlascloud | 6.65 ¥ | 28 ¥ | 0.16 USD | USD | 0.95 USD / 4 USD | 262K |
| Kimi K2.7 Code | kimi | 6.5 ¥ | 27 ¥ | 1.3 CNY | CNY | 6.5 CNY / 27 CNY | 262,144 tokens |
| Kimi K2.7 Code | modelmesh | 6.5 ¥ | 27 ¥ | - | CNY | 6.5 CNY / 27 CNY | 256K |
| Kimi K2.7 Code | tencent | 6.65 ¥ | 28 ¥ | 0.19 USD | USD | 0.95 USD / 4 USD | - |
| Kimi K2.7 Code | tencent_cn | 6.5 ¥ | 27 ¥ | 1.3 CNY | CNY | 6.5 CNY / 27 CNY | - |
| Kimi K3 | aliyun_intl | 21 ¥ | 105 ¥ | 0.3 USD | USD | 3 USD / 15 USD | - |
| Kimi K3 | atlascloud | 21 ¥ | 105 ¥ | 0.3 USD | USD | 3 USD / 15 USD | 1.04858M |
| Kimi K3 | kimi | 20 ¥ | 100 ¥ | 2 CNY | CNY | 20 CNY / 100 CNY | 1,048,576 tokens |
| Kimi K3 | modelmesh | 20 ¥ | 100 ¥ | - | CNY | 20 CNY / 100 CNY | 1000K |
| Kimi K3 | openrouter | 21 ¥ | 105 ¥ | 0.3 USD | USD | 3 USD / 15 USD | 1.04858M |
| Kimi K3 | tencent | 19.117 ¥ | 95.571 ¥ | 0.2731 USD | USD | 2.731 USD / 13.653 USD | - |
| Kimi K3 | tencent_cn | 21.974 ¥ | 109.869 ¥ | 2.197 CNY | CNY | 21.974 CNY / 109.869 CNY | - |
| MiniMax M2.7 | aliyun_bailian | 2.1 ¥ | 8.4 ¥ | 0.42 CNY | CNY | 2.1 CNY / 8.4 CNY | - |
| MiniMax M2.7 | atlascloud | 2.1 ¥ | 8.4 ¥ | 0.06 USD | USD | 0.3 USD / 1.2 USD | 196K |
| MiniMax M2.7 | minimax | 2.1 ¥ | 8.4 ¥ | 0.42 CNY | CNY | 2.1 CNY / 8.4 CNY | - |
| MiniMax M2.7 | modelmesh | 2.1 ¥ | 8.4 ¥ | - | CNY | 2.1 CNY / 8.4 CNY | 200K |
| MiniMax M2.7 | tencent | 2.1 ¥ | 8.4 ¥ | 0.06 USD | USD | 0.3 USD / 1.2 USD | - |
| MiniMax M2.7 | tencent_cn | 2.197 ¥ | 8.79 ¥ | 0.439 CNY | CNY | 2.197 CNY / 8.79 CNY | - |
| MiniMax M3 | aliyun_bailian | 4.2 ¥ | 16.8 ¥ | 0.84 CNY | CNY | 4.2 CNY / 16.8 CNY | - |
| MiniMax M3 | atlascloud | 2.1 ¥ | 8.4 ¥ | 0.06 USD | USD | 0.3 USD / 1.2 USD | 524K |
| MiniMax M3 | minimax | 2.1 ¥ | 8.4 ¥ | 0.42 CNY | CNY | 2.1 CNY / 8.4 CNY | ≤512K |
| MiniMax M3 | minimax | 4.2 ¥ | 16.8 ¥ | 0.84 CNY | CNY | 4.2 CNY / 16.8 CNY | 512K~1 |
| MiniMax M3 | modelmesh | 2.1 ¥ | 8.4 ¥ | - | CNY | 2.1 CNY / 8.4 CNY | 1000K |
| MiniMax M3 | openrouter | 2.1 ¥ | 8.4 ¥ | 0.06 USD | USD | 0.3 USD / 1.2 USD | 1.04858M |
| MiniMax M3 | tencent | 2.1 ¥ | 8.4 ¥ | 0.06 USD | USD | 0.3 USD / 1.2 USD | - |
| MiniMax M3 | tencent | 4.2 ¥ | 16.8 ¥ | 0.12 USD | USD | 0.6 USD / 2.4 USD | - |
| MiniMax M3 | tencent_cn | 2.1 ¥ | 8.4 ¥ | 0.42 CNY | CNY | 2.1 CNY / 8.4 CNY | - |
| Qwen3.7 Max | aliyun_intl | 17.5 ¥ | 52.5 ¥ | 0.5 USD | USD | 2.5 USD / 7.5 USD | - |
| Qwen3.7 Max | atlascloud | 17.5 ¥ | 52.5 ¥ | 0.5 USD | USD | 2.5 USD / 7.5 USD | 1M |
| Qwen3.7 Max | modelmesh | 6 ¥ | 18 ¥ | - | CNY | 6 CNY / 18 CNY | 1000K |
| Qwen3.7 Plus | aliyun_intl | 2.8 ¥ | 11.2 ¥ | 0.08 USD | USD | 0.4 USD / 1.6 USD | - |
| Qwen3.7 Plus | atlascloud | 2.8 ¥ | 11.2 ¥ | 0.08 USD | USD | 0.4 USD / 1.6 USD | 1M |
| Qwen3.7 Plus | modelmesh | 1.6 ¥ | 6.4 ¥ | - | CNY | 1.6 CNY / 6.4 CNY | 1000K |
| Qwen3.8 Max | aliyun_intl | 14 ¥ | 42 ¥ | 0.25 USD | USD | 2 USD / 6 USD | - |
| Qwen3.8 Max | atlascloud | 14 ¥ | 42 ¥ | 0.25 USD | USD | 2 USD / 6 USD | 1M |
| Qwen3.8 Max | modelmesh | 12 ¥ | 36 ¥ | - | CNY | 12 CNY / 36 CNY | 1000K |

## 二、周环比变动

| 模型 | 源 | 字段 | 旧值 | 新值 | 货币 |
| --- | --- | --- | ---: | ---: | --- |
| GPT-5.6 Sol | openai | 输入 | 10 | 4 | USD |
| GPT-5.6 Sol | openai | 输出 | 45 | 20 | USD |
| GPT-5.6 Terra | openai | 输入 | 4 | 2 | USD |
| GPT-5.6 Terra | openai | 输出 | 18 | 12 | USD |
| GPT-5.6 Luna | openai | 输入 | 0.4 | 0.2 | USD |
| GPT-5.6 Luna | openai | 输出 | 1.8 | 1.2 | USD |
| DeepSeek V4 Pro | openrouter | 输入 | 0.396894 | 0.526176 | USD |
| DeepSeek V4 Pro | openrouter | 输出 | 0.793788 | 1.05235 | USD |
| DeepSeek V4 Flash | openrouter | 输入 | 0.04886 | 0.0574 | USD |
| DeepSeek V4 Flash | openrouter | 输出 | 0.09772 | 0.1148 | USD |
| DeepSeek V4 Flash | tencent | 输入 | 0.14 | 0.22 | USD |
| DeepSeek V4 Flash | tencent | 输出 | 0.28 | 0.66 | USD |
| DeepSeek V4 Flash | tencent | 输入 | 0.14 | 0.44 | USD |
| DeepSeek V4 Flash | tencent | 输出 | 0.28 | 1.32 | USD |
| DeepSeek V4 Pro | tencent | 输入 | 1.74 | 0.66 | USD |
| DeepSeek V4 Pro | tencent | 输出 | 3.48 | 1.98 | USD |
| DeepSeek V4 Pro | tencent | 输入 | 1.74 | 1.32 | USD |
| DeepSeek V4 Pro | tencent | 输出 | 3.48 | 3.96 | USD |
| GLM-5.1 | tencent | 输入 | 1.12 | 0.84 | USD |
| GLM-5.1 | tencent | 输出 | 3.92 | 3.36 | USD |
| MiniMax M3 | tencent | 输入 | 0.6 | 0.3 | USD |
| MiniMax M3 | tencent | 输出 | 2.4 | 1.2 | USD |
| MiniMax M3 | minimax | 输入 | 4.2 | 2.1 | CNY |
| MiniMax M3 | minimax | 输出 | 16.8 | 8.4 | CNY |

## 三、抓取状态

| 源 | 状态 | 记录数 | 说明 |
| --- | --- | ---: | --- |
| openai | 成功 | 8 | 抓取 8 条 |
| openrouter | 成功 | 38 | 抓取 38 条 |
| zai | 成功 | 13 | 抓取 13 条 |
| deepseek_us | 成功 | 3 | 抓取 3 条 |
| atlascloud | 成功 | 133 | 抓取 133 条 |
| deepseek | 成功 | 3 | 抓取 3 条 |
| aliyun | 成功 | 0 | 抓取 0 条 |
| aliyun_bailian | 成功 | 28 | 抓取 28 条 |
| aliyun_intl | 成功 | 10 | 抓取 10 条 |
| volcengine | 成功 | 18 | 抓取 18 条 |
| volcengine_intl | 成功 | 5 | 抓取 5 条 |
| tencent | 成功 | 33 | 抓取 33 条 |
| tencent_cn | 成功 | 26 | 抓取 26 条 |
| bigmodel | 成功 | 15 | 抓取 15 条 |
| minimax | 成功 | 4 | 抓取 4 条 |
| kimi | 成功 | 5 | 抓取 5 条 |
| modelmesh | 成功 | 63 | 抓取 63 条 |