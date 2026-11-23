## 🔔 Token 定价变动（2026-11-23 10:05:18）

| 模型 | 源 | 字段 | 旧值 | 新值 | 货币 |
| --- | --- | --- | ---: | ---: | --- |
| DeepSeek V4 Pro | openrouter | 输入 | 0.95526 | 0.9 | USD |
| DeepSeek V4 Pro | openrouter | 输出 | 1.91052 | 1.5 | USD |
| DeepSeek V4 Pro 0813 | openrouter | 输入 | 0.111 | 1.32 | USD |
| DeepSeek V4 Pro 0813 | openrouter | 输出 | 4.44 | 3.96 | USD |
| DeepSeek V4 Flash | openrouter | 输入 | 0.091 | 0.09 | USD |
| DeepSeek V4 Flash | openrouter | 输出 | 0.182 | 0.18 | USD |
| GLM-5.3-Flash | openrouter | 输入 | 0.15 | 0.0399 | USD |
| GLM-5.3-Flash | openrouter | 输出 | 0.5 | 0.0784 | USD |
| DeepSeek V4.1 Flash | openrouter | 输入 | 0.006 | 0.0498 | USD |
| DeepSeek V4.1 Flash | openrouter | 输出 | 0.5 | 0.1992 | USD |

## 🆕 新模型雷达（未登记候选，待人工确认）

扫描 OpenRouter 全量 477 个模型，发现 **10** 个未登记候选（疑似旗舰 **4** 个）：

| 模型 | 厂商 | 上架 | 距今 | 输入 $/1M | 输出 $/1M | 判定 |
|---|---|---|---|---|---|---|
| `mistralai/pixtral-large-2502`（Pixtral Large 2502） | Mistral | 2026-11-20 | 3 天 | $2 | $6 | 疑似旗舰 |
| `openai/gpt-6.2-astra-pro`（GPT-6.2 Astra Pro） | OpenAI | 2026-11-17 | 5 天 | $8 | $40 | 疑似旗舰 |
| `anthropic/claude-fable-5.2`（Claude Fable 5.2） | Anthropic | 2026-11-09 | 13 天 | $8 | $40 | 疑似旗舰 |
| `qwen/qwen3.8-max-prime`（Qwen3.8 Max Prime） | 通义千问 | 2026-09-23 | 60 天 | $4 | $12 | 疑似旗舰 |
| `openai/gpt-6.2-sol-pro`（GPT-6.2 Sol Pro） | OpenAI | 2026-11-17 | 5 天 | $2 | $10 | 新增档位 |
| `qwen/qwen4-max`（Qwen4 Max） | 通义千问 | 2026-11-16 | 7 天 | $1.425 | $4.275 | 新增档位 |
| `openai/gpt-6.1-terra-pro`（GPT-6.1 Terra Pro） | OpenAI | 2026-10-26 | 27 天 | $1 | $5 | 新增档位 |
| `mistralai/mistral-large-4-0`（Mistral Large 4） | Mistral | 2026-10-06 | 47 天 | $0.7 | $2.1 | 新增档位 |
| `openai/gpt-6.1-sol-pro`（GPT-6.1 Sol Pro） | OpenAI | 2026-09-29 | 54 天 | $2 | $10 | 新增档位 |
| `anthropic/claude-sonnet-5.5`（Claude Sonnet 5.5） | Anthropic | 2026-09-28 | 55 天 | $2 | $10 | 新增档位 |

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
  - canonical: Claude Fable 5.2
    family: Anthropic
    region: overseas
    status: tracking
    priority: high
    aliases: [Claude Fable 5.2, claude-fable-5.2, anthropic/claude-fable-5.2]
    note: 雷达自动发现（OpenRouter 2026-11-09 上架，$8/$40）；确认后补官网抓取/白名单并转 active
  - canonical: Qwen3.8 Max Prime
    family: 通义千问
    region: domestic
    status: tracking
    priority: high
    aliases: [Qwen3.8 Max Prime, qwen3.8-max-prime, qwen/qwen3.8-max-prime]
    note: 雷达自动发现（OpenRouter 2026-09-23 上架，$4/$12）；确认后补官网抓取/白名单并转 active
```

</details>
