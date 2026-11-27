# 大模型 Token 定价周报

> 生成时间：2026-11-27 10:23:51

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
| DeepSeek V4 Flash | atlascloud | 0.98 ¥ | 1.96 ¥ | 0.028 USD | USD | 0.14 USD / 0.28 USD | 1.04858M |
| DeepSeek V4 Flash | openrouter | 0.63 ¥ | 1.26 ¥ | 0.018 USD | USD | 0.09 USD / 0.18 USD | 1.04858M |
| DeepSeek V4 Pro | aliyun_bailian | 12 ¥ | 24 ¥ | 2.4 CNY | CNY | 12 CNY / 24 CNY | - |
| DeepSeek V4 Pro | atlascloud | 11.76 ¥ | 23.66 ¥ | 0.13 USD | USD | 1.68 USD / 3.38 USD | 1.04858M |
| DeepSeek V4 Pro | deepseek | 9 ¥ | 27 ¥ | 0.3 CNY | CNY | 9 CNY / 27 CNY | 1M |
| DeepSeek V4 Pro | deepseek_us | 9.24 ¥ | 27.72 ¥ | 0.044 USD | USD | 1.32 USD / 3.96 USD | 1M |
| DeepSeek V4 Pro | openrouter | 6.21732 ¥ | 10.5574 ¥ | 0.2 USD | USD | 0.888188 USD / 1.5082 USD | 1.04858M |
| DeepSeek V4 Pro 0813 | openrouter | 0.6993 ¥ | 35 ¥ | 0.0999 USD | USD | 0.0999 USD / 5 USD | 1.04858M |
| DeepSeek V4.1 Flash | aliyun_bailian | 2 ¥ | 8 ¥ | 0.4 CNY | CNY | 2 CNY / 8 CNY | - |
| DeepSeek V4.1 Flash | atlascloud | 2.1 ¥ | 8.4 ¥ | 0.03 USD | USD | 0.3 USD / 1.2 USD | 1.04858M |
| DeepSeek V4.1 Flash | deepseek | 2 ¥ | 8 ¥ | 0.04 CNY | CNY | 2 CNY / 8 CNY | 1M |
| DeepSeek V4.1 Flash | deepseek_us | 2.1 ¥ | 8.4 ¥ | 0.006 USD | USD | 0.3 USD / 1.2 USD | 1M |
| DeepSeek V4.1 Flash | openrouter | 0.98 ¥ | 2.94 ¥ | 0.0042 USD | USD | 0.14 USD / 0.42 USD | 1.04858M |
| Doubao Seed 2.1 Pro | atlascloud | 6.3 ¥ | 31.5 ¥ | 0.18 USD | USD | 0.9 USD / 4.5 USD | 262K |
| Doubao Seed 2.1 Turbo | atlascloud | 3.15 ¥ | 15.75 ¥ | 0.09 USD | USD | 0.45 USD / 2.25 USD | 262K |
| GLM-4.7 | zai | 4.2 ¥ | 15.4 ¥ | 0.11 USD | USD | 0.6 USD / 2.2 USD | - |
| GLM-5.1 | aliyun_bailian | 6 ¥ | 24 ¥ | 1.2 CNY | CNY | 6 CNY / 24 CNY | - |
| GLM-5.1 | atlascloud | 8.82 ¥ | 27.72 ¥ | 0.234 USD | USD | 1.26 USD / 3.96 USD | 202K |
| GLM-5.1 | zai | 9.8 ¥ | 30.8 ¥ | 0.26 USD | USD | 1.4 USD / 4.4 USD | - |
| GLM-5.2 | aliyun_bailian | 8 ¥ | 28 ¥ | 1.6 CNY | CNY | 8 CNY / 28 CNY | - |
| GLM-5.2 | atlascloud | 6.566 ¥ | 20.636 ¥ | 0.174 USD | USD | 0.938 USD / 2.948 USD | 1.04858M |
| GLM-5.2 | zai | 9.8 ¥ | 30.8 ¥ | 0.26 USD | USD | 1.4 USD / 4.4 USD | - |
| GLM-5.3 | aliyun_bailian | 8 ¥ | 28 ¥ | 1.6 CNY | CNY | 8 CNY / 28 CNY | - |
| GLM-5.3 | atlascloud | 9.8 ¥ | 30.8 ¥ | 0.26 USD | USD | 1.4 USD / 4.4 USD | 1.04858M |
| GLM-5.3 | openrouter | 0.4893 ¥ | 9.8 ¥ | 0.0689 USD | USD | 0.0699 USD / 1.4 USD | 1.04858M |
| GLM-5.3 | zai | 9.8 ¥ | 30.8 ¥ | 0.26 USD | USD | 1.4 USD / 4.4 USD | - |
| GLM-5.3-Flash | aliyun_bailian | 0.8 ¥ | 2.8 ¥ | 0.16 CNY | CNY | 0.8 CNY / 2.8 CNY | - |
| GLM-5.3-Flash | atlascloud | 1.05 ¥ | 3.5 ¥ | 0.03 USD | USD | 0.15 USD / 0.5 USD | 1.04858M |
| GLM-5.3-Flash | openrouter | 1.05 ¥ | 3.5 ¥ | 0.03 USD | USD | 0.15 USD / 0.5 USD | 1.04858M |
| GLM-5.3-Flash | zai | 1.05 ¥ | 3.5 ¥ | 0.03 USD | USD | 0.15 USD / 0.5 USD | - |
| GPT-5 | openrouter | 8.75 ¥ | 70 ¥ | 0.125 USD | USD | 1.25 USD / 10 USD | 400K |
| GPT-5.5 | openrouter | 35 ¥ | 210 ¥ | 0.5 USD | USD | 5 USD / 30 USD | 1.05M |
| GPT-5.5 Pro | openrouter | 210 ¥ | 1260 ¥ | - | USD | 30 USD / 180 USD | 1.05M |
| GPT-5.6 Luna | openrouter | 1.4 ¥ | 8.4 ¥ | 0.02 USD | USD | 0.2 USD / 1.2 USD | 1.05M |
| GPT-5.6 Terra | openrouter | 14 ¥ | 84 ¥ | 0.2 USD | USD | 2 USD / 12 USD | 1.05M |
| GPT-6 Astra | openrouter | 70 ¥ | 350 ¥ | 1 USD | USD | 10 USD / 50 USD | 1.05M |
| GPT-6 Astra Pro | openrouter | 70 ¥ | 350 ¥ | 1 USD | USD | 10 USD / 50 USD | 1.05M |
| Gemini 3.6 Flash | openrouter | 5.25 ¥ | 26.25 ¥ | 0.075 USD | USD | 0.75 USD / 3.75 USD | 1.04858M |
| Gemini 3.7 Flash | openrouter | 5.25 ¥ | 26.25 ¥ | 0.075 USD | USD | 0.75 USD / 3.75 USD | 1.04858M |
| Gemini 3.8 Flash | openrouter | 5.775 ¥ | 28.875 ¥ | 0.0825 USD | USD | 0.825 USD / 4.125 USD | 1.04858M |
| Grok 4.6 | grok | 14 ¥ | 42 ¥ | 0.5 USD | USD | 2 USD / 6 USD | 500K |
| Grok 4.6 | grok | 28 ¥ | 84 ¥ | 1 USD | USD | 4 USD / 12 USD | 500K |
| Grok 4.6 | openrouter | 14 ¥ | 42 ¥ | 0.5 USD | USD | 2 USD / 6 USD | 500K |
| Kimi K2.6 | aliyun_bailian | 6.5 ¥ | 27 ¥ | 1.3 CNY | CNY | 6.5 CNY / 27 CNY | - |
| Kimi K2.6 | atlascloud | 6.65 ¥ | 28 ¥ | 0.16 USD | USD | 0.95 USD / 4 USD | 262K |
| Kimi K2.6 | openrouter | 4.55 ¥ | 23.87 ¥ | 0.15 USD | USD | 0.65 USD / 3.41 USD | 262K |
| Kimi K2.7 Code | aliyun_bailian | 6.5 ¥ | 27 ¥ | 1.3 CNY | CNY | 6.5 CNY / 27 CNY | - |
| Kimi K2.7 Code | atlascloud | 6.65 ¥ | 28 ¥ | 0.16 USD | USD | 0.95 USD / 4 USD | 262K |
| Kimi K3 | aliyun_bailian | 20 ¥ | 100 ¥ | 4 CNY | CNY | 20 CNY / 100 CNY | - |
| Kimi K3 | atlascloud | 21 ¥ | 105 ¥ | 0.3 USD | USD | 3 USD / 15 USD | 1.04858M |
| Kimi K3 | openrouter | 1.344 ¥ | 112 ¥ | 0.182 USD | USD | 0.192 USD / 16 USD | 1.04858M |
| MiMo V2.5 | atlascloud | 0.98 ¥ | 1.96 ¥ | 0.003 USD | USD | 0.14 USD / 0.28 USD | 1.024M |
| MiMo V2.5 Pro | atlascloud | 3.045 ¥ | 6.09 ¥ | 0.004 USD | USD | 0.435 USD / 0.87 USD | 1.024M |
| MiniMax M2.7 | aliyun_bailian | 2.1 ¥ | 8.4 ¥ | 0.42 CNY | CNY | 2.1 CNY / 8.4 CNY | - |
| MiniMax M3 | openrouter | 2.1 ¥ | 8.4 ¥ | 0.06 USD | USD | 0.3 USD / 1.2 USD | 1.04858M |
| Qwen3.7 Max | aliyun | 14.4 ¥ | 43.2 ¥ | 2.88 CNY | CNY | 14.4 CNY / 43.2 CNY | - |
| Qwen3.7 Max | atlascloud | 17.5 ¥ | 52.5 ¥ | 0.5 USD | USD | 2.5 USD / 7.5 USD | 1M |
| Qwen3.7 Plus | aliyun | 2.4 ¥ | 9.6 ¥ | 0.48 CNY | CNY | 2.4 CNY / 9.6 CNY | - |
| Qwen3.7 Plus | atlascloud | 2.8 ¥ | 11.2 ¥ | 0.08 USD | USD | 0.4 USD / 1.6 USD | 1M |
| Qwen3.8 Flash | aliyun_bailian | 0.8 ¥ | 2.7 ¥ | 0.16 CNY | CNY | 0.8 CNY / 2.7 CNY | - |
| Qwen3.8 Max | atlascloud | 9.8 ¥ | 29.4 ¥ | 0.175 USD | USD | 1.4 USD / 4.2 USD | 1M |

## 二、周环比变动

| 模型 | 源 | 字段 | 旧值 | 新值 | 货币 |
| --- | --- | --- | ---: | ---: | --- |
| DeepSeek V4 Pro 0813 | openrouter | 输入 | 0.111 | 0.0999 | USD |
| DeepSeek V4 Pro 0813 | openrouter | 输出 | 4.44 | 5 | USD |

## 三、抓取状态

| 源 | 状态 | 记录数 | 说明 |
| --- | --- | ---: | --- |
| openai | 成功 | 0 | 抓取 0 条 |
| zai | 成功 | 15 | 抓取 15 条 |
| anthropic | 成功 | 0 | 抓取 0 条 |
| grok | 成功 | 2 | 抓取 2 条 |
| deepseek_us | 成功 | 2 | 抓取 2 条 |
| openrouter | 成功 | 41 | 抓取 41 条 |
| gemini | 成功 | 0 | 抓取 0 条 |
| deepseek | 成功 | 2 | 抓取 2 条 |
| aliyun_bailian | 成功 | 31 | 抓取 31 条 |
| aliyun | 成功 | 2 | 抓取 2 条 |
| atlascloud | 成功 | 143 | 抓取 143 条 |
| aliyun_intl | 成功 | 0 | 抓取 0 条 |
| volcengine | 成功 | 0 | 抓取 0 条 |
| volcengine_intl | 成功 | 0 | 抓取 0 条 |
| tencent | 成功 | 0 | 抓取 0 条 |
| tencent_cn | 成功 | 0 | 抓取 0 条 |
| bigmodel | 成功 | 0 | 抓取 0 条 |
| minimax | 成功 | 0 | 抓取 0 条 |
| kimi | 成功 | 0 | 抓取 0 条 |
| kimi_ai | 成功 | 0 | 抓取 0 条 |
| mimo | 成功 | 0 | 抓取 0 条 |
| mimo_intl | 成功 | 0 | 抓取 0 条 |
| modelmesh | 成功 | 0 | 抓取 0 条 |

## 四、新模型雷达（待人工登记）

扫描 OpenRouter 全量 477 个模型，发现 **8** 个未登记候选（疑似旗舰 **4** 个）：

| 模型 | 厂商 | 上架 | 距今 | 输入 $/1M | 输出 $/1M | 判定 |
|---|---|---|---|---|---|---|
| `mistralai/pixtral-large-2502`（Pixtral Large 2502） | Mistral | 2026-11-20 | 7 天 | $2 | $6 | 疑似旗舰 |
| `openai/gpt-6.2-astra-pro`（GPT-6.2 Astra Pro） | OpenAI | 2026-11-17 | 9 天 | $8 | $40 | 疑似旗舰 |
| `qwen/qwen4-max`（Qwen4 Max） | 通义千问 | 2026-11-16 | 11 天 | $1.425 | $4.275 | 疑似旗舰 |
| `anthropic/claude-fable-5.2`（Claude Fable 5.2） | Anthropic | 2026-11-09 | 17 天 | $8 | $40 | 疑似旗舰 |
| `openai/gpt-6.2-sol-pro`（GPT-6.2 Sol Pro） | OpenAI | 2026-11-17 | 9 天 | $2 | $10 | 新增档位 |
| `openai/gpt-6.1-terra-pro`（GPT-6.1 Terra Pro） | OpenAI | 2026-10-26 | 31 天 | $1 | $5 | 新增档位 |
| `mistralai/mistral-large-4-0`（Mistral Large 4） | Mistral | 2026-10-06 | 51 天 | $0.7 | $2.1 | 新增档位 |
| `openai/gpt-6.1-sol-pro`（GPT-6.1 Sol Pro） | OpenAI | 2026-09-29 | 58 天 | $2 | $10 | 新增档位 |

<details><summary>待登记 YAML（粘贴到 <code>config/new_models.yml</code>）</summary>

```yaml
models:
  - canonical: Pixtral Large 2502
    family: Mistral
    region: overseas
    status: tracking
    priority: high
    aliases: [Pixtral Large 2502, pixtral-large-2502, mistralai/pixtral-large-2502]
    note: 雷达自动发现（OpenRouter 2026-11-20 上架，$2/$6）；确认后补官网抓取/白名单并转 active
  - canonical: GPT-6.2 Astra Pro
    family: OpenAI
    region: overseas
    status: tracking
    priority: high
    aliases: [GPT-6.2 Astra Pro, gpt-6.2-astra-pro, openai/gpt-6.2-astra-pro]
    note: 雷达自动发现（OpenRouter 2026-11-17 上架，$8/$40）；确认后补官网抓取/白名单并转 active
  - canonical: Qwen4 Max
    family: 通义千问
    region: domestic
    status: tracking
    priority: high
    aliases: [Qwen4 Max, qwen4-max, qwen/qwen4-max]
    note: 雷达自动发现（OpenRouter 2026-11-16 上架，$1.425/$4.275）；确认后补官网抓取/白名单并转 active
  - canonical: Claude Fable 5.2
    family: Anthropic
    region: overseas
    status: tracking
    priority: high
    aliases: [Claude Fable 5.2, claude-fable-5.2, anthropic/claude-fable-5.2]
    note: 雷达自动发现（OpenRouter 2026-11-09 上架，$8/$40）；确认后补官网抓取/白名单并转 active
```

</details>
