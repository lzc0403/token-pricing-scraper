## 🔔 Token 定价变动（2026-10-28 07:48:36）

| 模型 | 源 | 字段 | 旧值 | 新值 | 货币 |
| --- | --- | --- | ---: | ---: | --- |
| Kimi K3 | openrouter | 输入 | 0.169 | 0.2 | USD |
| Kimi K3 | openrouter | 输出 | 11.5 | 20 | USD |
| GLM-5.3 | openrouter | 输入 | 0.0769 | 0.0699 | USD |

## 🆕 新模型雷达（未登记候选，待人工确认）

扫描 OpenRouter 全量 464 个模型，发现 **11** 个未登记候选（疑似旗舰 **5** 个）：

| 模型 | 厂商 | 上架 | 距今 | 输入 $/1M | 输出 $/1M | 判定 |
|---|---|---|---|---|---|---|
| `mistralai/mistral-large-4-0`（Mistral Large 4） | Mistral | 2026-10-06 | 21 天 | $1.36 | $4.18 | 疑似旗舰 |
| `openai/gpt-6.1-sol-pro`（GPT-6.1 Sol Pro） | OpenAI | 2026-09-29 | 28 天 | $2 | $10 | 疑似旗舰 |
| `qwen/qwen3.8-max-prime`（Qwen3.8 Max Prime） | 通义千问 | 2026-09-23 | 34 天 | $4 | $12 | 疑似旗舰 |
| `openai/gpt-6-sol-pro`（GPT-6 Sol Pro） | OpenAI | 2026-09-22 | 35 天 | $2 | $10 | 疑似旗舰 |
| `anthropic/claude-fable-5.1`（Claude Fable 5.1） | Anthropic | 2026-09-01 | 56 天 | $10 | $50 | 疑似旗舰 |
| `openai/gpt-6.1-terra`（GPT-6.1 Terra） | OpenAI | 2026-10-26 | 1 天 | $1 | $5 | 新增档位 |
| `openai/gpt-6.1-terra-pro`（GPT-6.1 Terra Pro） | OpenAI | 2026-10-26 | 1 天 | $1 | $5 | 新增档位 |
| `anthropic/claude-sonnet-5.5`（Claude Sonnet 5.5） | Anthropic | 2026-09-28 | 29 天 | $2 | $10 | 新增档位 |
| `openai/gpt-6-luna-pro`（GPT-6 Luna Pro） | OpenAI | 2026-09-22 | 35 天 | $0.1 | $0.5 | 新增档位 |
| `qwen/qwen3.8-omni-flash`（Qwen3.8 Omni Flash） | 通义千问 | 2026-09-21 | 37 天 | $0.15 | $0.47 | 新增档位 |
| `qwen/qwen3.8-max-0902`（Qwen3.8 Max (0902)） | 通义千问 | 2026-09-03 | 54 天 | $2 | $6 | 新增档位 |

<details><summary>待登记 YAML（粘贴到 <code>config/new_models.yml</code>）</summary>

```yaml
models:
  - canonical: Mistral Large 4
    family: Mistral
    region: overseas
    status: tracking
    priority: high
    aliases: [Mistral Large 4, mistral-large-4-0, mistralai/mistral-large-4-0]
    note: 雷达自动发现（OpenRouter 2026-10-06 上架，$1.36/$4.18）；确认后补官网抓取/白名单并转 active
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
  - canonical: Claude Fable 5.1
    family: Anthropic
    region: overseas
    status: tracking
    priority: high
    aliases: [Claude Fable 5.1, claude-fable-5.1, anthropic/claude-fable-5.1]
    note: 雷达自动发现（OpenRouter 2026-09-01 上架，$10/$50）；确认后补官网抓取/白名单并转 active
```

</details>
