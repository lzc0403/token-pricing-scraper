# 大模型 Token 定价周报

> 生成时间：2026-07-17 07:15:36

## 一、目标模型跨源对照（已换算人民币）

| 模型 | 源 | 输入¥ | 输出¥ | 缓存命中 | 货币 | 原始价(输入/输出) | 上下文 |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| DeepSeek V3.2 | tencent | 2.016 ¥ | 3.024 ¥ | 0.056 USD | USD | 0.28 USD / 0.42 USD | - |
| DeepSeek V4 Flash | deepseek | 1 ¥ | 2 ¥ | - | CNY | 1 CNY / 2 CNY | 1M |
| DeepSeek V4 Flash | tencent | 1.008 ¥ | 2.016 ¥ | 0.0028 USD | USD | 0.14 USD / 0.28 USD | - |
| DeepSeek V4 Flash | tencent | 1.008 ¥ | 2.016 ¥ | 0.028 USD | USD | 0.14 USD / 0.28 USD | - |
| DeepSeek V4 Pro | deepseek | 3 ¥ | 6 ¥ | - | CNY | 3 CNY / 6 CNY | 1M |
| DeepSeek V4 Pro | tencent | 3.132 ¥ | 6.264 ¥ | 0.00363 USD | USD | 0.435 USD / 0.87 USD | - |
| DeepSeek V4 Pro | tencent | 12.528 ¥ | 25.056 ¥ | 0.145 USD | USD | 1.74 USD / 3.48 USD | - |
| GLM-5.1 | bigmodel | 6 ¥ | 24 ¥ | - | CNY | 6 CNY / 24 CNY | - |
| GLM-5.1 | tencent | 6.048 ¥ | 24.192 ¥ | 0.182 USD | USD | 0.84 USD / 3.36 USD | - |
| GLM-5.1 | tencent | 8.064 ¥ | 28.224 ¥ | 0.28 USD | USD | 1.12 USD / 3.92 USD | - |
| GLM-5.2 | bigmodel | 8 ¥ | 28 ¥ | - | CNY | 8 CNY / 28 CNY | - |
| GLM-5.2 | tencent | 8.064 ¥ | 28.224 ¥ | 0.28 USD | USD | 1.12 USD / 3.92 USD | - |
| Kimi K2.6 | kimi | 1.1 ¥ | 27 ¥ | 1.1 CNY | CNY | 1.1 CNY / 27 CNY | 262,144 tokens |
| Kimi K2.6 | tencent | 6.1776 ¥ | 25.6752 ¥ | 0.145 USD | USD | 0.858 USD / 3.566 USD | - |
| MiniMax M2.7 | minimax | 2.1 ¥ | 8.4 ¥ | 0.42 CNY | CNY | 2.1 CNY / 8.4 CNY | - |
| MiniMax M2.7 | minimax | 4.2 ¥ | 16.8 ¥ | 0.42 CNY | CNY | 4.2 CNY / 16.8 CNY | - |
| MiniMax M2.7 | tencent | 2.16 ¥ | 8.64 ¥ | 0.06 USD | USD | 0.3 USD / 1.2 USD | - |
| Seedance 2.0 | volcengine | 3.2 ¥ | 16 ¥ | 0.64 CNY | CNY | 3.2 CNY / 16 CNY | - |
| Seedance 2.0 | volcengine | 0.6 ¥ | 3.6 ¥ | 0.12 CNY | CNY | 0.6 CNY / 3.6 CNY | - |
| Seedance 2.0 | volcengine | 0.2 ¥ | 2 ¥ | 0.04 CNY | CNY | 0.2 CNY / 2 CNY | - |
| Seedance 2.0 | volcengine | 3.2 ¥ | 16 ¥ | 0.64 CNY | CNY | 3.2 CNY / 16 CNY | - |
| qwen3.7 | aliyun | 6 ¥ | 18 ¥ | - | CNY | 6 CNY / 18 CNY | - |
| qwen3.7 | aliyun | 6.4 ¥ | 6.4 ¥ | - | CNY | 6.4 CNY / 6.4 CNY | - |

## 二、周环比变动

| 模型 | 源 | 字段 | 旧值 | 新值 | 货币 |
| --- | --- | --- | ---: | ---: | --- |
| qwen3.7 | aliyun | 输入 | 6.4 | 6 | CNY |
| qwen3.7 | aliyun | 输出 | 6.4 | 18 | CNY |
| Seedance 2.0 | volcengine | 输入 | 3.2 | 0.6 | CNY |
| Seedance 2.0 | volcengine | 输出 | 16 | 3.6 | CNY |
| Seedance 2.0 | volcengine | 输入 | 3.2 | 0.2 | CNY |
| Seedance 2.0 | volcengine | 输出 | 16 | 2 | CNY |
| DeepSeek V4 Pro | tencent | 输入 | 1.74 | 0.435 | USD |
| DeepSeek V4 Pro | tencent | 输出 | 3.48 | 0.87 | USD |
| GLM-5.1 | tencent | 输入 | 1.12 | 0.84 | USD |
| GLM-5.1 | tencent | 输出 | 3.92 | 3.36 | USD |
| MiniMax M2.7 | minimax | 输入 | 4.2 | 2.1 | CNY |
| MiniMax M2.7 | minimax | 输出 | 16.8 | 8.4 | CNY |

## 三、抓取状态

| 源 | 状态 | 记录数 | 说明 |
| --- | --- | ---: | --- |
| aliyun | 成功 | 2 | 抓取 2 条 |
| volcengine | 成功 | 18 | 抓取 18 条 |
| tencent | 成功 | 23 | 抓取 23 条 |
| bigmodel | 成功 | 14 | 抓取 14 条 |
| deepseek | 成功 | 2 | 抓取 2 条 |
| minimax | 成功 | 2 | 抓取 2 条 |
| kimi | 成功 | 4 | 抓取 4 条 |
| modelmesh | 成功 | 0 | 抓取 0 条 |