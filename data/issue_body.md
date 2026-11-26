## 🔔 Token 定价变动（2026-11-26 10:17:33）

| 模型 | 源 | 字段 | 旧值 | 新值 | 货币 |
| --- | --- | --- | ---: | ---: | --- |
| DeepSeek V4 Pro | openrouter | 输入 | 1.28 | 0.888188 | USD |
| DeepSeek V4 Pro | openrouter | 输出 | 2.56 | 1.5082 | USD |
| GLM-5.3-Flash | openrouter | 输入 | 0.12 | 0.15 | USD |
| GLM-5.3-Flash | openrouter | 输出 | 0.38 | 0.5 | USD |

## 🆕 新模型雷达（未登记候选，待人工确认）

扫描 OpenRouter 全量 474 个模型，发现 **8** 个未登记候选（疑似旗舰 **4** 个）：

| 模型 | 厂商 | 上架 | 距今 | 输入 $/1M | 输出 $/1M | 判定 |
|---|---|---|---|---|---|---|
| `mistralai/pixtral-large-2502`（Pixtral Large 2502） | Mistral | 2026-11-20 | 6 天 | $2 | $6 | 疑似旗舰 |
| `openai/gpt-6.2-astra-pro`（GPT-6.2 Astra Pro） | OpenAI | 2026-11-17 | 8 天 | $8 | $40 | 疑似旗舰 |
| `qwen/qwen4-max`（Qwen4 Max） | 通义千问 | 2026-11-16 | 10 天 | $1.425 | $4.275 | 疑似旗舰 |
| `anthropic/claude-fable-5.2`（Claude Fable 5.2） | Anthropic | 2026-11-09 | 16 天 | $8 | $40 | 疑似旗舰 |
| `openai/gpt-6.2-sol-pro`（GPT-6.2 Sol Pro） | OpenAI | 2026-11-17 | 8 天 | $2 | $10 | 新增档位 |
| `openai/gpt-6.1-terra-pro`（GPT-6.1 Terra Pro） | OpenAI | 2026-10-26 | 30 天 | $1 | $5 | 新增档位 |
| `mistralai/mistral-large-4-0`（Mistral Large 4） | Mistral | 2026-10-06 | 50 天 | $0.7 | $2.1 | 新增档位 |
| `openai/gpt-6.1-sol-pro`（GPT-6.1 Sol Pro） | OpenAI | 2026-09-29 | 57 天 | $2 | $10 | 新增档位 |

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
