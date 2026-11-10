## 🔔 Token 定价变动（2026-11-10 09:02:13）

| 模型 | 源 | 字段 | 旧值 | 新值 | 货币 |
| --- | --- | --- | ---: | ---: | --- |
| GLM-5.3-Flash | openrouter | 输入 | 0.0335 | 0.15 | USD |
| GLM-5.3-Flash | openrouter | 输出 | 0.083 | 0.5 | USD |
| DeepSeek V4.1 Flash | openrouter | 输入 | 0.051 | 0.006 | USD |
| DeepSeek V4.1 Flash | openrouter | 输出 | 0.567 | 0.5 | USD |

## 🆕 新模型雷达（未登记候选，待人工确认）

扫描 OpenRouter 全量 465 个模型，发现 **10** 个未登记候选（疑似旗舰 **5** 个）：

| 模型 | 厂商 | 上架 | 距今 | 输入 $/1M | 输出 $/1M | 判定 |
|---|---|---|---|---|---|---|
| `anthropic/claude-fable-5.2`（Claude Fable 5.2） | Anthropic | 2026-11-09 | 0 天 | $8 | $40 | 疑似旗舰 |
| `mistralai/mistral-large-4-0`（Mistral Large 4） | Mistral | 2026-10-06 | 34 天 | $0.7 | $2.1 | 疑似旗舰 |
| `openai/gpt-6.1-sol-pro`（GPT-6.1 Sol Pro） | OpenAI | 2026-09-29 | 41 天 | $2 | $10 | 疑似旗舰 |
| `qwen/qwen3.8-max-prime`（Qwen3.8 Max Prime） | 通义千问 | 2026-09-23 | 47 天 | $4 | $12 | 疑似旗舰 |
| `openai/gpt-6-sol-pro`（GPT-6 Sol Pro） | OpenAI | 2026-09-22 | 48 天 | $2 | $10 | 疑似旗舰 |
| `openai/gpt-6.1-terra`（GPT-6.1 Terra） | OpenAI | 2026-10-26 | 14 天 | $1 | $5 | 新增档位 |
| `openai/gpt-6.1-terra-pro`（GPT-6.1 Terra Pro） | OpenAI | 2026-10-26 | 14 天 | $1 | $5 | 新增档位 |
| `anthropic/claude-sonnet-5.5`（Claude Sonnet 5.5） | Anthropic | 2026-09-28 | 42 天 | $2 | $10 | 新增档位 |
| `openai/gpt-6-luna-pro`（GPT-6 Luna Pro） | OpenAI | 2026-09-22 | 48 天 | $0.1 | $0.5 | 新增档位 |
| `qwen/qwen3.8-omni-flash`（Qwen3.8 Omni Flash） | 通义千问 | 2026-09-21 | 50 天 | $0.15 | $0.47 | 新增档位 |

<details><summary>待登记 YAML（粘贴到 <code>config/new_models.yml</code>）</summary>

```yaml
models:
  - canonical: Claude Fable 5.2
    family: Anthropic
    region: overseas
    status: tracking
    priority: high
    aliases: [Claude Fable 5.2, claude-fable-5.2, anthropic/claude-fable-5.2]
    note: 雷达自动发现（OpenRouter 2026-11-09 上架，$8/$40）；确认后补官网抓取/白名单并转 active
  - canonical: Mistral Large 4
    family: Mistral
    region: overseas
    status: tracking
    priority: high
    aliases: [Mistral Large 4, mistral-large-4-0, mistralai/mistral-large-4-0]
    note: 雷达自动发现（OpenRouter 2026-10-06 上架，$0.7/$2.1）；确认后补官网抓取/白名单并转 active
  - canonical: GPT-6.1 Sol Pro
    family: OpenAI
    region: overseas
    status: tracking
    priority: high
    aliases: [GPT-6.1 Sol Pro, gpt-6.1-sol-pro, openai/gpt-6.1-sol-pro]
    note: 雷达自动发现（OpenRouter 2026-09-29 上架，$2/$10）；确认后补官网抓取/白名单并转 active
  - canonical: Qwen3.8 Max Prime
    family: 通义千问
    region: domestic
    status: tracking
    priority: high
    aliases: [Qwen3.8 Max Prime, qwen3.8-max-prime, qwen/qwen3.8-max-prime]
    note: 雷达自动发现（OpenRouter 2026-09-23 上架，$4/$12）；确认后补官网抓取/白名单并转 active
  - canonical: GPT-6 Sol Pro
    family: OpenAI
    region: overseas
    status: tracking
    priority: high
    aliases: [GPT-6 Sol Pro, gpt-6-sol-pro, openai/gpt-6-sol-pro]
    note: 雷达自动发现（OpenRouter 2026-09-22 上架，$2/$10）；确认后补官网抓取/白名单并转 active
```

</details>
