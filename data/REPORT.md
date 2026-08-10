# 大模型 Token 定价周报

> 生成时间：2026-08-10 12:01:37

## 一、目标模型跨源对照（已换算人民币）

| 模型 | 源 | 输入¥ | 输出¥ | 缓存命中 | 货币 | 原始价(输入/输出) | 上下文 |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| DeepSeek V3.2 | aliyun_bailian | 2 ¥ | 3 ¥ | 0.4 CNY | CNY | 2 CNY / 3 CNY | - |
| DeepSeek V3.2 | aliyun_intl | 3.99 ¥ | 11.97 ¥ | 0.114 USD | USD | 0.57 USD / 1.71 USD | - |
| DeepSeek V3.2 | atlascloud | 1.82 ¥ | 2.66 ¥ | 0.13 USD | USD | 0.26 USD / 0.38 USD | 163K |
| DeepSeek V3.2 | tencent | 1.96 ¥ | 2.94 ¥ | 0.056 USD | USD | 0.28 USD / 0.42 USD | - |
| DeepSeek V4 Flash | aliyun_bailian | 1 ¥ | 2 ¥ | 0.2 CNY | CNY | 1 CNY / 2 CNY | - |
| DeepSeek V4 Flash | aliyun_intl | 1.4 ¥ | 2.8 ¥ | 0.04 USD | USD | 0.2 USD / 0.4 USD | - |
| DeepSeek V4 Flash | atlascloud | 0.98 ¥ | 1.96 ¥ | 0.028 USD | USD | 0.14 USD / 0.28 USD | 1.04858M |
| DeepSeek V4 Flash | deepseek | 1 ¥ | 2 ¥ | 0.02 CNY | CNY | 1 CNY / 2 CNY | 1M |
| DeepSeek V4 Flash | modelmesh | 1 ¥ | 2 ¥ | - | CNY | 1 CNY / 2 CNY | 1000K |
| DeepSeek V4 Flash | openrouter | 0.98 ¥ | 1.96 ¥ | 0.028 USD | USD | 0.14 USD / 0.28 USD | 1.04858M |
| DeepSeek V4 Flash | tencent | 0.98 ¥ | 1.96 ¥ | 0.028 USD | USD | 0.14 USD / 0.28 USD | - |
| DeepSeek V4 Flash | tencent_cn | 1 ¥ | 2 ¥ | 0.02 CNY | CNY | 1 CNY / 2 CNY | - |
| DeepSeek V4 Flash | tencent_cn | 1 ¥ | 2 ¥ | 0.2 CNY | CNY | 1 CNY / 2 CNY | - |
| DeepSeek V4 Pro | aliyun_bailian | 12 ¥ | 24 ¥ | 2.4 CNY | CNY | 12 CNY / 24 CNY | - |
| DeepSeek V4 Pro | aliyun_intl | 16.8 ¥ | 33.6 ¥ | 0.2 USD | USD | 2.4 USD / 4.8 USD | - |
| DeepSeek V4 Pro | atlascloud | 11.76 ¥ | 23.66 ¥ | 0.13 USD | USD | 1.68 USD / 3.38 USD | 1.04858M |
| DeepSeek V4 Pro | deepseek | 3 ¥ | 6 ¥ | 0.025 CNY | CNY | 3 CNY / 6 CNY | 1M |
| DeepSeek V4 Pro | modelmesh | 3 ¥ | 6 ¥ | - | CNY | 3 CNY / 6 CNY | 1000K |
| DeepSeek V4 Pro | openrouter | 3.045 ¥ | 6.09 ¥ | 0.003625 USD | USD | 0.435 USD / 0.87 USD | 1.04858M |
| DeepSeek V4 Pro | tencent | 12.18 ¥ | 24.36 ¥ | 0.145 USD | USD | 1.74 USD / 3.48 USD | - |
| DeepSeek V4 Pro | tencent_cn | 3 ¥ | 6 ¥ | 0.025 CNY | CNY | 3 CNY / 6 CNY | - |
| DeepSeek V4 Pro | tencent_cn | 12 ¥ | 24 ¥ | 1 CNY | CNY | 12 CNY / 24 CNY | - |
| Doubao Seed 2.1 Pro | atlascloud | 6.3 ¥ | 31.5 ¥ | 0.18 USD | USD | 0.9 USD / 4.5 USD | 262K |
| Doubao Seed 2.1 Pro | modelmesh | 6 ¥ | 30 ¥ | - | CNY | 6 CNY / 30 CNY | 256K |
| Doubao Seed 2.1 Pro | volcengine | 6 ¥ | 30 ¥ | 1.2 CNY | CNY | 6 CNY / 30 CNY | - |
| Doubao Seed 2.1 Turbo | atlascloud | 3.15 ¥ | 15.75 ¥ | 0.09 USD | USD | 0.45 USD / 2.25 USD | 262K |
| Doubao Seed 2.1 Turbo | modelmesh | 3 ¥ | 15 ¥ | - | CNY | 3 CNY / 15 CNY | 256K |
| Doubao Seed 2.1 Turbo | volcengine | 3 ¥ | 15 ¥ | 0.6 CNY | CNY | 3 CNY / 15 CNY | - |
| GLM-5.1 | aliyun_bailian | 6 ¥ | 24 ¥ | 1.2 CNY | CNY | 6 CNY / 24 CNY | - |
| GLM-5.1 | aliyun_intl | 9.8 ¥ | 30.8 ¥ | 0.26 USD | USD | 1.4 USD / 4.4 USD | - |
| GLM-5.1 | atlascloud | 8.82 ¥ | 27.72 ¥ | 0.234 USD | USD | 1.26 USD / 3.96 USD | 202K |
| GLM-5.1 | bigmodel | 6 ¥ | 24 ¥ | - | CNY | 6 CNY / 24 CNY | - |
| GLM-5.1 | modelmesh | 6 ¥ | 24 ¥ | - | CNY | 6 CNY / 24 CNY | 200K |
| GLM-5.1 | tencent | 5.88 ¥ | 23.52 ¥ | 0.182 USD | USD | 0.84 USD / 3.36 USD | - |
| GLM-5.1 | tencent | 7.84 ¥ | 27.44 ¥ | 0.28 USD | USD | 1.12 USD / 3.92 USD | - |
| GLM-5.1 | tencent_cn | 10.254 ¥ | 32.228 ¥ | 1.904 CNY | CNY | 10.254 CNY / 32.228 CNY | - |
| GLM-5.2 | aliyun_bailian | 8 ¥ | 28 ¥ | 1.6 CNY | CNY | 8 CNY / 28 CNY | - |
| GLM-5.2 | aliyun_intl | 9.8 ¥ | 30.8 ¥ | 0.28 USD | USD | 1.4 USD / 4.4 USD | - |
| GLM-5.2 | atlascloud | 8.82 ¥ | 27.72 ¥ | 0.234 USD | USD | 1.26 USD / 3.96 USD | 1.04858M |
| GLM-5.2 | bigmodel | 8 ¥ | 28 ¥ | - | CNY | 8 CNY / 28 CNY | - |
| GLM-5.2 | modelmesh | 8 ¥ | 28 ¥ | - | CNY | 8 CNY / 28 CNY | 1000K |
| GLM-5.2 | openrouter | 5.32 ¥ | 16.94 ¥ | 0.14 USD | USD | 0.76 USD / 2.42 USD | 1.04858M |
| GLM-5.2 | tencent | 7.84 ¥ | 27.44 ¥ | 0.28 USD | USD | 1.12 USD / 3.92 USD | - |
| GLM-5.2 | tencent_cn | 10.254 ¥ | 32.2282 ¥ | 1.9044 CNY | CNY | 10.254 CNY / 32.2282 CNY | - |
| Kimi K2.6 | aliyun_bailian | 6.5 ¥ | 27 ¥ | 1.3 CNY | CNY | 6.5 CNY / 27 CNY | - |
| Kimi K2.6 | atlascloud | 6.65 ¥ | 28 ¥ | 0.16 USD | USD | 0.95 USD / 4 USD | 262K |
| Kimi K2.6 | kimi | 1.1 ¥ | 27 ¥ | 1.1 CNY | CNY | 1.1 CNY / 27 CNY | 262,144 tokens |
| Kimi K2.6 | modelmesh | 6.5 ¥ | 27 ¥ | - | CNY | 6.5 CNY / 27 CNY | 256K |
| Kimi K2.6 | openrouter | 6.65 ¥ | 28 ¥ | 0.16 USD | USD | 0.95 USD / 4 USD | 262K |
| Kimi K2.6 | tencent | 6.006 ¥ | 24.962 ¥ | 0.145 USD | USD | 0.858 USD / 3.566 USD | - |
| Kimi K2.6 | tencent_cn | 6.5 ¥ | 27 ¥ | 1.1 CNY | CNY | 6.5 CNY / 27 CNY | - |
| Kimi K2.7 Code | aliyun_bailian | 6.5 ¥ | 27 ¥ | 1.3 CNY | CNY | 6.5 CNY / 27 CNY | - |
| Kimi K2.7 Code | aliyun_intl | 6.65 ¥ | 28 ¥ | 0.19 USD | USD | 0.95 USD / 4 USD | - |
| Kimi K2.7 Code | atlascloud | 6.65 ¥ | 28 ¥ | 0.16 USD | USD | 0.95 USD / 4 USD | 262K |
| Kimi K2.7 Code | kimi | 1.3 ¥ | 27 ¥ | 1.3 CNY | CNY | 1.3 CNY / 27 CNY | 262,144 tokens |
| Kimi K2.7 Code | modelmesh | 6.5 ¥ | 27 ¥ | - | CNY | 6.5 CNY / 27 CNY | 256K |
| Kimi K2.7 Code | tencent | 6.65 ¥ | 28 ¥ | 0.19 USD | USD | 0.95 USD / 4 USD | - |
| Kimi K2.7 Code | tencent_cn | 6.5 ¥ | 27 ¥ | 1.3 CNY | CNY | 6.5 CNY / 27 CNY | - |
| Kimi K3 | aliyun_bailian | 20 ¥ | 100 ¥ | 4 CNY | CNY | 20 CNY / 100 CNY | - |
| Kimi K3 | atlascloud | 21 ¥ | 105 ¥ | 0.3 USD | USD | 3 USD / 15 USD | 1.04858M |
| Kimi K3 | kimi | 2 ¥ | 100 ¥ | 2 CNY | CNY | 2 CNY / 100 CNY | 1,048,576 tokens |
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
| Qwen3.7 Max | aliyun | 14.4 ¥ | 43.2 ¥ | 2.88 CNY | CNY | 14.4 CNY / 43.2 CNY | - |
| Qwen3.7 Max | aliyun_intl | 17.5 ¥ | 52.5 ¥ | 0.5 USD | USD | 2.5 USD / 7.5 USD | - |
| Qwen3.7 Max | atlascloud | 17.5 ¥ | 52.5 ¥ | 0.5 USD | USD | 2.5 USD / 7.5 USD | 1M |
| Qwen3.7 Max | modelmesh | 6 ¥ | 18 ¥ | - | CNY | 6 CNY / 18 CNY | 1000K |
| Qwen3.7 Plus | aliyun | 2.4 ¥ | 9.6 ¥ | 0.48 CNY | CNY | 2.4 CNY / 9.6 CNY | - |
| Qwen3.7 Plus | aliyun_intl | 2.8 ¥ | 11.2 ¥ | 0.08 USD | USD | 0.4 USD / 1.6 USD | - |
| Qwen3.7 Plus | atlascloud | 2.8 ¥ | 11.2 ¥ | 0.08 USD | USD | 0.4 USD / 1.6 USD | 1M |
| Qwen3.7 Plus | modelmesh | 1.6 ¥ | 6.4 ¥ | - | CNY | 1.6 CNY / 6.4 CNY | 1000K |
| Qwen3.8 Max | aliyun_intl | 14 ¥ | 42 ¥ | 0.25 USD | USD | 2 USD / 6 USD | - |
| Qwen3.8 Max | atlascloud | 14 ¥ | 42 ¥ | 0.25 USD | USD | 2 USD / 6 USD | 1M |
| Qwen3.8 Max | modelmesh | 12 ¥ | 36 ¥ | - | CNY | 12 CNY / 36 CNY | 1000K |

## 二、周环比变动

| 模型 | 源 | 字段 | 旧值 | 新值 | 货币 |
| --- | --- | --- | ---: | ---: | --- |
| GLM-5.1 | tencent | 输入 | 1.12 | 0.84 | USD |
| GLM-5.1 | tencent | 输出 | 3.92 | 3.36 | USD |
| MiniMax M3 | tencent | 输入 | 0.6 | 0.3 | USD |
| MiniMax M3 | tencent | 输出 | 2.4 | 1.2 | USD |
| DeepSeek V4 Pro | tencent_cn | 输入 | 12 | 3 | CNY |
| DeepSeek V4 Pro | tencent_cn | 输出 | 24 | 6 | CNY |
| MiniMax M3 | minimax | 输入 | 4.2 | 2.1 | CNY |
| MiniMax M3 | minimax | 输出 | 16.8 | 8.4 | CNY |
| Kimi K2.6 | openrouter | 输入 | 0.5795 | 0.95 | USD |
| Kimi K2.6 | openrouter | 输出 | 2.44 | 4 | USD |
| GLM-5.2 | openrouter | 输入 | 0.07 | 0.76 | USD |
| GLM-5.2 | openrouter | 输出 | 0.22 | 2.42 | USD |

## 三、抓取状态

| 源 | 状态 | 记录数 | 说明 |
| --- | --- | ---: | --- |
| aliyun | 成功 | 2 | 抓取 2 条 |
| aliyun_intl | 成功 | 9 | 抓取 9 条 |
| aliyun_bailian | 成功 | 28 | 抓取 28 条 |
| volcengine | 成功 | 18 | 抓取 18 条 |
| tencent | 成功 | 26 | 抓取 26 条 |
| tencent_cn | 成功 | 25 | 抓取 25 条 |
| bigmodel | 成功 | 14 | 抓取 14 条 |
| deepseek | 成功 | 2 | 抓取 2 条 |
| minimax | 成功 | 4 | 抓取 4 条 |
| kimi | 成功 | 5 | 抓取 5 条 |
| modelmesh | 成功 | 64 | 抓取 64 条 |
| openrouter | 成功 | 23 | 抓取 23 条 |
| atlascloud | 成功 | 126 | 抓取 126 条 |