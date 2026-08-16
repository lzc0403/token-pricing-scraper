# 大模型 Token 定价周报

> 生成时间：2026-08-16 18:11:53

## 一、目标模型跨源对照（已换算人民币）

| 模型 | 源 | 输入¥ | 输出¥ | 缓存命中 | 货币 | 原始价(输入/输出) | 上下文 |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| DeepSeek V3.2 | aliyun_bailian | 2 ¥ | 3 ¥ | 0.4 CNY | CNY | 2 CNY / 3 CNY | - |
| DeepSeek V3.2 | atlascloud | 1.82 ¥ | 2.66 ¥ | 0.13 USD | USD | 0.26 USD / 0.38 USD | 163K |
| DeepSeek V3.2 | tencent | - | 1.96 ¥ | 0.42 USD | USD | - / 0.28 USD | - |
| DeepSeek V4 Flash | aliyun_intl | - | 1.4 ¥ | 0.4 USD | USD | - / 0.2 USD | - |
| DeepSeek V4 Flash | atlascloud | 0.98 ¥ | 1.96 ¥ | 0.028 USD | USD | 0.14 USD / 0.28 USD | 1.04858M |
| DeepSeek V4 Flash | deepseek | - | 384 ¥ | - | CNY | - / 384 CNY | 1M |
| DeepSeek V4 Flash | modelmesh | 1 ¥ | 2 ¥ | - | CNY | 1 CNY / 2 CNY | 1000K |
| DeepSeek V4 Flash | openrouter | 0.43022 ¥ | 0.86044 ¥ | 0.012292 USD | USD | 0.06146 USD / 0.12292 USD | 1.04858M |
| DeepSeek V4 Flash | tencent | - | 0.98 ¥ | 0.28 USD | USD | - / 0.14 USD | - |
| DeepSeek V4 Flash | tencent_cn | 1 ¥ | 2 ¥ | 0.2 CNY | CNY | 1 CNY / 2 CNY | - |
| DeepSeek V4 Pro | aliyun_intl | - | 16.8 ¥ | 4.8 USD | USD | - / 2.4 USD | - |
| DeepSeek V4 Pro | atlascloud | 11.76 ¥ | 23.66 ¥ | 0.13 USD | USD | 1.68 USD / 3.38 USD | 1.04858M |
| DeepSeek V4 Pro | deepseek | - | 384 ¥ | 0.05 CNY | CNY | - / 384 CNY | 1M |
| DeepSeek V4 Pro | modelmesh | 3 ¥ | 6 ¥ | - | CNY | 3 CNY / 6 CNY | 1000K |
| DeepSeek V4 Pro | openrouter | 8.176 ¥ | 16.352 ¥ | 0.09855 USD | USD | 1.168 USD / 2.336 USD | 1.04858M |
| DeepSeek V4 Pro | tencent | - | 12.18 ¥ | 3.48 USD | USD | - / 1.74 USD | - |
| DeepSeek V4 Pro | tencent_cn | 12 ¥ | 24 ¥ | 1 CNY | CNY | 12 CNY / 24 CNY | - |
| Doubao Seed 2.1 Pro | atlascloud | 6.3 ¥ | 31.5 ¥ | 0.18 USD | USD | 0.9 USD / 4.5 USD | 262K |
| Doubao Seed 2.1 Pro | modelmesh | 6 ¥ | 30 ¥ | - | CNY | 6 CNY / 30 CNY | 256K |
| Doubao Seed 2.1 Pro | volcengine | 6 ¥ | 30 ¥ | 1.2 CNY | CNY | 6 CNY / 30 CNY | - |
| Doubao Seed 2.1 Turbo | atlascloud | 3.15 ¥ | 15.75 ¥ | 0.09 USD | USD | 0.45 USD / 2.25 USD | 262K |
| Doubao Seed 2.1 Turbo | modelmesh | 3 ¥ | 15 ¥ | - | CNY | 3 CNY / 15 CNY | 256K |
| Doubao Seed 2.1 Turbo | volcengine | 3 ¥ | 15 ¥ | 0.6 CNY | CNY | 3 CNY / 15 CNY | - |
| GLM-5.1 | aliyun_bailian | 6 ¥ | 24 ¥ | 1.2 CNY | CNY | 6 CNY / 24 CNY | - |
| GLM-5.1 | aliyun_intl | - | 9.8 ¥ | 4.4 USD | USD | - / 1.4 USD | - |
| GLM-5.1 | atlascloud | 8.82 ¥ | 27.72 ¥ | 0.234 USD | USD | 1.26 USD / 3.96 USD | 202K |
| GLM-5.1 | bigmodel | 6 ¥ | 24 ¥ | - | CNY | 6 CNY / 24 CNY | - |
| GLM-5.1 | modelmesh | 6 ¥ | 24 ¥ | - | CNY | 6 CNY / 24 CNY | 200K |
| GLM-5.1 | tencent | - | 5.88 ¥ | 3.36 USD | USD | - / 0.84 USD | - |
| GLM-5.1 | tencent | - | 7.84 ¥ | 3.92 USD | USD | - / 1.12 USD | - |
| GLM-5.1 | tencent_cn | 10.254 ¥ | 32.228 ¥ | 1.904 CNY | CNY | 10.254 CNY / 32.228 CNY | - |
| GLM-5.2 | aliyun_bailian | 8 ¥ | 28 ¥ | 1.6 CNY | CNY | 8 CNY / 28 CNY | - |
| GLM-5.2 | aliyun_intl | - | 9.8 ¥ | 4.4 USD | USD | - / 1.4 USD | - |
| GLM-5.2 | atlascloud | 8.82 ¥ | 27.72 ¥ | 0.234 USD | USD | 1.26 USD / 3.96 USD | 1.04858M |
| GLM-5.2 | bigmodel | 8 ¥ | 28 ¥ | - | CNY | 8 CNY / 28 CNY | - |
| GLM-5.2 | modelmesh | 8 ¥ | 28 ¥ | - | CNY | 8 CNY / 28 CNY | 1000K |
| GLM-5.2 | openrouter | 2.156 ¥ | 6.776 ¥ | 0.0572 USD | USD | 0.308 USD / 0.968 USD | 1.04858M |
| GLM-5.2 | tencent | - | 7.84 ¥ | 3.92 USD | USD | - / 1.12 USD | - |
| GLM-5.2 | tencent_cn | 10.254 ¥ | 32.2282 ¥ | 1.9044 CNY | CNY | 10.254 CNY / 32.2282 CNY | - |
| Kimi K2.6 | aliyun_bailian | 6.5 ¥ | 27 ¥ | 1.3 CNY | CNY | 6.5 CNY / 27 CNY | - |
| Kimi K2.6 | atlascloud | 6.65 ¥ | 28 ¥ | 0.16 USD | USD | 0.95 USD / 4 USD | 262K |
| Kimi K2.6 | kimi | 1.1 ¥ | 27 ¥ | 1.1 CNY | CNY | 1.1 CNY / 27 CNY | 262,144 tokens |
| Kimi K2.6 | modelmesh | 6.5 ¥ | 27 ¥ | - | CNY | 6.5 CNY / 27 CNY | 256K |
| Kimi K2.6 | openrouter | 3.7905 ¥ | 15.96 ¥ | 0.0912 USD | USD | 0.5415 USD / 2.28 USD | 262K |
| Kimi K2.6 | tencent | - | 6.006 ¥ | 3.566 USD | USD | - / 0.858 USD | - |
| Kimi K2.6 | tencent_cn | 6.5 ¥ | 27 ¥ | 1.1 CNY | CNY | 6.5 CNY / 27 CNY | - |
| Kimi K2.7 Code | aliyun_bailian | 6.5 ¥ | 27 ¥ | 1.3 CNY | CNY | 6.5 CNY / 27 CNY | - |
| Kimi K2.7 Code | aliyun_intl | - | 6.65 ¥ | 4 USD | USD | - / 0.95 USD | - |
| Kimi K2.7 Code | atlascloud | 6.65 ¥ | 28 ¥ | 0.16 USD | USD | 0.95 USD / 4 USD | 262K |
| Kimi K2.7 Code | kimi | 1.3 ¥ | 27 ¥ | 1.3 CNY | CNY | 1.3 CNY / 27 CNY | 262,144 tokens |
| Kimi K2.7 Code | modelmesh | 6.5 ¥ | 27 ¥ | - | CNY | 6.5 CNY / 27 CNY | 256K |
| Kimi K2.7 Code | tencent | - | 6.65 ¥ | 4 USD | USD | - / 0.95 USD | - |
| Kimi K2.7 Code | tencent_cn | 6.5 ¥ | 27 ¥ | 1.3 CNY | CNY | 6.5 CNY / 27 CNY | - |
| Kimi K3 | atlascloud | 21 ¥ | 105 ¥ | 0.3 USD | USD | 3 USD / 15 USD | 1.04858M |
| Kimi K3 | kimi | 2 ¥ | 100 ¥ | 2 CNY | CNY | 2 CNY / 100 CNY | 1,048,576 tokens |
| Kimi K3 | modelmesh | 20 ¥ | 100 ¥ | - | CNY | 20 CNY / 100 CNY | 1000K |
| Kimi K3 | openrouter | 21 ¥ | 105 ¥ | 0.3 USD | USD | 3 USD / 15 USD | 1.04858M |
| Kimi K3 | tencent | - | 19.117 ¥ | 13.653 USD | USD | - / 2.731 USD | - |
| Kimi K3 | tencent_cn | 21.974 ¥ | 109.869 ¥ | 2.197 CNY | CNY | 21.974 CNY / 109.869 CNY | - |
| MiniMax M2.7 | atlascloud | 2.1 ¥ | 8.4 ¥ | 0.06 USD | USD | 0.3 USD / 1.2 USD | 196K |
| MiniMax M2.7 | minimax | 2.1 ¥ | 8.4 ¥ | 0.42 CNY | CNY | 2.1 CNY / 8.4 CNY | - |
| MiniMax M2.7 | modelmesh | 2.1 ¥ | 8.4 ¥ | - | CNY | 2.1 CNY / 8.4 CNY | 200K |
| MiniMax M2.7 | tencent | - | 2.1 ¥ | 1.2 USD | USD | - / 0.3 USD | - |
| MiniMax M2.7 | tencent_cn | 2.197 ¥ | 8.79 ¥ | 0.439 CNY | CNY | 2.197 CNY / 8.79 CNY | - |
| MiniMax M3 | atlascloud | 2.1 ¥ | 8.4 ¥ | 0.06 USD | USD | 0.3 USD / 1.2 USD | 524K |
| MiniMax M3 | minimax | 2.1 ¥ | 8.4 ¥ | 0.42 CNY | CNY | 2.1 CNY / 8.4 CNY | ≤512K |
| MiniMax M3 | minimax | 4.2 ¥ | 16.8 ¥ | 0.84 CNY | CNY | 4.2 CNY / 16.8 CNY | 512K~1 |
| MiniMax M3 | modelmesh | 2.1 ¥ | 8.4 ¥ | - | CNY | 2.1 CNY / 8.4 CNY | 1000K |
| MiniMax M3 | openrouter | 2.1 ¥ | 8.4 ¥ | 0.06 USD | USD | 0.3 USD / 1.2 USD | 1.04858M |
| MiniMax M3 | tencent | - | 2.1 ¥ | 1.2 USD | USD | - / 0.3 USD | - |
| MiniMax M3 | tencent | - | 4.2 ¥ | 2.4 USD | USD | - / 0.6 USD | - |
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
| Kimi K2.7 Code | aliyun_intl | 输入 | 0.95 | - | USD |
| Kimi K2.7 Code | aliyun_intl | 输出 | 4 | 0.95 | USD |
| GLM-5.2 | aliyun_intl | 输入 | 1.4 | - | USD |
| GLM-5.2 | aliyun_intl | 输出 | 4.4 | 1.4 | USD |
| GLM-5.1 | aliyun_intl | 输入 | 1.4 | - | USD |
| GLM-5.1 | aliyun_intl | 输出 | 4.4 | 1.4 | USD |
| DeepSeek V4 Pro | aliyun_intl | 输入 | 2.4 | - | USD |
| DeepSeek V4 Pro | aliyun_intl | 输出 | 4.8 | 2.4 | USD |
| DeepSeek V4 Flash | aliyun_intl | 输入 | 0.2 | - | USD |
| DeepSeek V4 Flash | aliyun_intl | 输出 | 0.4 | 0.2 | USD |
| DeepSeek V4 Flash | tencent | 输入 | 0.14 | - | USD |
| DeepSeek V4 Flash | tencent | 输出 | 0.28 | 0.14 | USD |
| DeepSeek V4 Pro | tencent | 输入 | 1.74 | - | USD |
| DeepSeek V4 Pro | tencent | 输出 | 3.48 | 1.74 | USD |
| DeepSeek V3.2 | tencent | 输入 | 0.28 | - | USD |
| DeepSeek V3.2 | tencent | 输出 | 0.42 | 0.28 | USD |
| GLM-5.2 | tencent | 输入 | 1.12 | - | USD |
| GLM-5.2 | tencent | 输出 | 3.92 | 1.12 | USD |
| GLM-5.1 | tencent | 输入 | 1.12 | - | USD |
| GLM-5.1 | tencent | 输出 | 3.92 | 0.84 | USD |
| GLM-5.1 | tencent | 输入 | 1.12 | - | USD |
| GLM-5.1 | tencent | 输出 | 3.92 | 1.12 | USD |
| Kimi K3 | tencent | 输入 | 2.731 | - | USD |
| Kimi K3 | tencent | 输出 | 13.653 | 2.731 | USD |
| Kimi K2.7 Code | tencent | 输入 | 0.95 | - | USD |
| Kimi K2.7 Code | tencent | 输出 | 4 | 0.95 | USD |
| Kimi K2.6 | tencent | 输入 | 0.858 | - | USD |
| Kimi K2.6 | tencent | 输出 | 3.566 | 0.858 | USD |
| MiniMax M3 | tencent | 输入 | 0.6 | - | USD |
| MiniMax M3 | tencent | 输出 | 2.4 | 0.3 | USD |
| MiniMax M3 | tencent | 输入 | 0.6 | - | USD |
| MiniMax M3 | tencent | 输出 | 2.4 | 0.6 | USD |
| MiniMax M2.7 | tencent | 输入 | 0.3 | - | USD |
| MiniMax M2.7 | tencent | 输出 | 1.2 | 0.3 | USD |
| DeepSeek V4 Flash | deepseek | 输入 | 1 | - | CNY |
| DeepSeek V4 Flash | deepseek | 输出 | 2 | 384 | CNY |
| DeepSeek V4 Pro | deepseek | 输入 | 3 | - | CNY |
| DeepSeek V4 Pro | deepseek | 输出 | 6 | 384 | CNY |
| MiniMax M3 | minimax | 输入 | 4.2 | 2.1 | CNY |
| MiniMax M3 | minimax | 输出 | 16.8 | 8.4 | CNY |
| DeepSeek V4 Pro | openrouter | 输入 | 0.435 | 1.168 | USD |
| DeepSeek V4 Pro | openrouter | 输出 | 0.87 | 2.336 | USD |
| DeepSeek V4 Flash | openrouter | 输入 | 0.14 | 0.06146 | USD |
| DeepSeek V4 Flash | openrouter | 输出 | 0.28 | 0.12292 | USD |
| Kimi K2.6 | openrouter | 输入 | 0.95 | 0.5415 | USD |
| Kimi K2.6 | openrouter | 输出 | 4 | 2.28 | USD |
| GLM-5.2 | openrouter | 输入 | 0.76 | 0.308 | USD |
| GLM-5.2 | openrouter | 输出 | 2.42 | 0.968 | USD |

## 三、抓取状态

| 源 | 状态 | 记录数 | 说明 |
| --- | --- | ---: | --- |
| aliyun | 成功 | 0 | 抓取 0 条 |
| aliyun_intl | 成功 | 9 | 抓取 9 条 |
| aliyun_bailian | 成功 | 41 | 抓取 41 条 |
| volcengine | 成功 | 18 | 抓取 18 条 |
| tencent | 成功 | 33 | 抓取 33 条 |
| tencent_cn | 成功 | 25 | 抓取 25 条 |
| bigmodel | 成功 | 14 | 抓取 14 条 |
| deepseek | 成功 | 2 | 抓取 2 条 |
| minimax | 成功 | 4 | 抓取 4 条 |
| kimi | 成功 | 5 | 抓取 5 条 |
| modelmesh | 成功 | 64 | 抓取 64 条 |
| openrouter | 成功 | 23 | 抓取 23 条 |
| atlascloud | 成功 | 133 | 抓取 133 条 |