# 大模型 Token 定价周报

> 生成时间：2026-07-19 17:26:30

## 一、目标模型跨源对照（已换算人民币）

| 模型 | 源 | 输入¥ | 输出¥ | 缓存命中 | 货币 | 原始价(输入/输出) | 上下文 |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| DeepSeek V3.2 | tencent | 2.016 ¥ | 3.024 ¥ | 0.056 USD | USD | 0.28 USD / 0.42 USD | - |
| DeepSeek V4 Flash | deepseek | 1 ¥ | 2 ¥ | 0.02 CNY | CNY | 1 CNY / 2 CNY | 1M |
| DeepSeek V4 Flash | openrouter | 0.7056 ¥ | 1.4112 ¥ | 0.0196 USD | USD | 0.098 USD / 0.196 USD | 1.04858M |
| DeepSeek V4 Flash | tencent | 1.008 ¥ | 2.016 ¥ | 0.028 USD | USD | 0.14 USD / 0.28 USD | - |
| DeepSeek V4 Pro | deepseek | 3 ¥ | 6 ¥ | 0.025 CNY | CNY | 3 CNY / 6 CNY | 1M |
| DeepSeek V4 Pro | openrouter | 3.132 ¥ | 6.264 ¥ | 0.003625 USD | USD | 0.435 USD / 0.87 USD | 1.04858M |
| DeepSeek V4 Pro | tencent | 12.528 ¥ | 25.056 ¥ | 0.145 USD | USD | 1.74 USD / 3.48 USD | - |
| Doubao Seed 2.1 Pro | volcengine | 6 ¥ | 30 ¥ | 1.2 CNY | CNY | 6 CNY / 30 CNY | - |
| Doubao Seed 2.1 Turbo | volcengine | 3 ¥ | 15 ¥ | 0.6 CNY | CNY | 3 CNY / 15 CNY | - |
| GLM-5.1 | bigmodel | 6 ¥ | 24 ¥ | - | CNY | 6 CNY / 24 CNY | - |
| GLM-5.1 | tencent | 6.048 ¥ | 24.192 ¥ | 0.182 USD | USD | 0.84 USD / 3.36 USD | - |
| GLM-5.1 | tencent | 8.064 ¥ | 28.224 ¥ | 0.28 USD | USD | 1.12 USD / 3.92 USD | - |
| GLM-5.2 | bigmodel | 8 ¥ | 28 ¥ | - | CNY | 8 CNY / 28 CNY | - |
| GLM-5.2 | openrouter | 1.73376 ¥ | 5.44896 ¥ | 0.04472 USD | USD | 0.2408 USD / 0.7568 USD | 1.04858M |
| GLM-5.2 | tencent | 8.064 ¥ | 28.224 ¥ | 0.28 USD | USD | 1.12 USD / 3.92 USD | - |
| Kimi K2.6 | kimi | 1.1 ¥ | 27 ¥ | 1.1 CNY | CNY | 1.1 CNY / 27 CNY | 262,144 tokens |
| Kimi K2.6 | openrouter | 4.9248 ¥ | 24.624 ¥ | 0.144 USD | USD | 0.684 USD / 3.42 USD | 262K |
| Kimi K2.6 | tencent | 6.1776 ¥ | 25.6752 ¥ | 0.145 USD | USD | 0.858 USD / 3.566 USD | - |
| Kimi K2.7 Code | kimi | 1.3 ¥ | 27 ¥ | 1.3 CNY | CNY | 1.3 CNY / 27 CNY | 262,144 tokens |
| Kimi K2.7 Code | tencent | 6.84 ¥ | 28.8 ¥ | 0.19 USD | USD | 0.95 USD / 4 USD | - |
| Kimi K3 | kimi | 2 ¥ | 100 ¥ | 2 CNY | CNY | 2 CNY / 100 CNY | 1,048,576 tokens |
| Kimi K3 | openrouter | 21.6 ¥ | 108 ¥ | 0.3 USD | USD | 3 USD / 15 USD | 1.04858M |
| MiniMax M2.7 | minimax | 2.1 ¥ | 8.4 ¥ | 0.42 CNY | CNY | 2.1 CNY / 8.4 CNY | - |
| MiniMax M2.7 | tencent | 2.16 ¥ | 8.64 ¥ | 0.06 USD | USD | 0.3 USD / 1.2 USD | - |
| MiniMax M3 | minimax | 2.1 ¥ | 8.4 ¥ | 0.42 CNY | CNY | 2.1 CNY / 8.4 CNY | ≤512K |
| MiniMax M3 | minimax | 4.2 ¥ | 16.8 ¥ | 0.84 CNY | CNY | 4.2 CNY / 16.8 CNY | 512K~1 |
| MiniMax M3 | openrouter | 2.16 ¥ | 8.64 ¥ | 0.06 USD | USD | 0.3 USD / 1.2 USD | 1.04858M |
| MiniMax M3 | tencent | 2.16 ¥ | 8.64 ¥ | 0.06 USD | USD | 0.3 USD / 1.2 USD | - |
| MiniMax M3 | tencent | 4.32 ¥ | 17.28 ¥ | 0.12 USD | USD | 0.6 USD / 2.4 USD | - |
| Qwen3.7 Max | aliyun | 14.4 ¥ | 43.2 ¥ | 2.88 CNY | CNY | 14.4 CNY / 43.2 CNY | - |
| Qwen3.7 Plus | aliyun | 2.4 ¥ | 9.6 ¥ | 0.48 CNY | CNY | 2.4 CNY / 9.6 CNY | - |

## 二、周环比变动

| 模型 | 源 | 字段 | 旧值 | 新值 | 货币 |
| --- | --- | --- | ---: | ---: | --- |
| GLM-5.1 | tencent | 输入 | 1.12 | 0.84 | USD |
| GLM-5.1 | tencent | 输出 | 3.92 | 3.36 | USD |
| MiniMax M3 | tencent | 输入 | 0.6 | 0.3 | USD |
| MiniMax M3 | tencent | 输出 | 2.4 | 1.2 | USD |
| MiniMax M3 | minimax | 输入 | 4.2 | 2.1 | CNY |
| MiniMax M3 | minimax | 输出 | 16.8 | 8.4 | CNY |
| GLM-5.2 | openrouter | 输入 | 0.2436 | 0.2408 | USD |
| GLM-5.2 | openrouter | 输出 | 0.7656 | 0.7568 | USD |

## 三、抓取状态

| 源 | 状态 | 记录数 | 说明 |
| --- | --- | ---: | --- |
| aliyun | 成功 | 2 | 抓取 2 条 |
| volcengine | 成功 | 18 | 抓取 18 条 |
| tencent | 成功 | 23 | 抓取 23 条 |
| bigmodel | 成功 | 14 | 抓取 14 条 |
| deepseek | 成功 | 2 | 抓取 2 条 |
| minimax | 成功 | 4 | 抓取 4 条 |
| kimi | 成功 | 5 | 抓取 5 条 |
| modelmesh | 成功 | 0 | 抓取 0 条 |
| openrouter | 成功 | 23 | 抓取 23 条 |