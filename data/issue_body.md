## 🔔 Token 定价变动（2026-11-24 11:54:39）

| 模型 | 源 | 字段 | 旧值 | 新值 | 货币 |
| --- | --- | --- | ---: | ---: | --- |
| DeepSeek V4 Pro | openrouter | 输入 | 0.9 | 1.28 | USD |
| DeepSeek V4 Pro | openrouter | 输出 | 1.5 | 2.56 | USD |
| DeepSeek V4 Pro 0813 | openrouter | 输入 | 1.32 | 0.111 | USD |
| DeepSeek V4 Pro 0813 | openrouter | 输出 | 3.96 | 4.44 | USD |
| Kimi K3 | openrouter | 输入 | 0.192 | 0.2 | USD |
| GLM-5.3-Flash | openrouter | 输入 | 0.0399 | 0.12 | USD |
| GLM-5.3-Flash | openrouter | 输出 | 0.0784 | 0.38 | USD |
| DeepSeek V4.1 Flash | openrouter | 输入 | 0.0498 | 0.14 | USD |
| DeepSeek V4.1 Flash | openrouter | 输出 | 0.1992 | 0.42 | USD |

## 🆕 新模型雷达（未登记候选，待人工确认）

扫描 OpenRouter 全量 473 个模型，发现 **9** 个未登记候选（疑似旗舰 **4** 个）：

| 模型 | 厂商 | 上架 | 距今 | 输入 $/1M | 输出 $/1M | 判定 |
|---|---|---|---|---|---|---|
| `mistralai/pixtral-large-2502`（Pixtral Large 2502） | Mistral | 2026-11-20 | 4 天 | $2 | $6 | 疑似旗舰 |
| `openai/gpt-6.2-astra-pro`（GPT-6.2 Astra Pro） | OpenAI | 2026-11-17 | 6 天 | $8 | $40 | 疑似旗舰 |
| `qwen/qwen4-max`（Qwen4 Max） | 通义千问 | 2026-11-16 | 8 天 | $1.425 | $4.275 | 疑似旗舰 |
| `anthropic/claude-fable-5.2`（Claude Fable 5.2） | Anthropic | 2026-11-09 | 14 天 | $8 | $40 | 疑似旗舰 |
| `openai/gpt-6.2-sol-pro`（GPT-6.2 Sol Pro） | OpenAI | 2026-11-17 | 6 天 | $2 | $10 | 新增档位 |
| `openai/gpt-6.1-terra-pro`（GPT-6.1 Terra Pro） | OpenAI | 2026-10-26 | 28 天 | $1 | $5 | 新增档位 |
| `mistralai/mistral-large-4-0`（Mistral Large 4） | Mistral | 2026-10-06 | 48 天 | $0.7 | $2.1 | 新增档位 |
| `openai/gpt-6.1-sol-pro`（GPT-6.1 Sol Pro） | OpenAI | 2026-09-29 | 55 天 | $2 | $10 | 新增档位 |
| `anthropic/claude-sonnet-5.5`（Claude Sonnet 5.5） | Anthropic | 2026-09-28 | 56 天 | $2 | $10 | 新增档位 |

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
