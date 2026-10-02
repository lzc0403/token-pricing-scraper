## 🔔 Token 定价变动（2026-10-02 07:49:23）

| 模型 | 源 | 字段 | 旧值 | 新值 | 货币 |
| --- | --- | --- | ---: | ---: | --- |
| DeepSeek V4 Pro | openrouter | 输入 | 0.216282 | 0.2088 | USD |
| DeepSeek V4 Pro | openrouter | 输出 | 0.432564 | 0.4176 | USD |
| Kimi K2.6 | openrouter | 输入 | 0.65 | 0.43415 | USD |
| Kimi K2.6 | openrouter | 输出 | 3.41 | 1.828 | USD |
| Kimi K3 | openrouter | 输入 | 0.6789 | 2.7 | USD |
| Kimi K3 | openrouter | 输出 | 10 | 13.5 | USD |
| GLM-5.3 | openrouter | 输入 | 0.2219 | 1.4 | USD |
| DeepSeek V4.1 Flash | openrouter | 输入 | 0.027 | 0.015 | USD |
| DeepSeek V4.1 Flash | openrouter | 输出 | 0.6 | 1.2 | USD |
| GLM-5.2 | openrouter | 输入 | 1.4 | 0.41 | USD |
| GLM-5.2 | openrouter | 输出 | 4.4 | 3.99 | USD |

## 🆕 新模型雷达（未登记候选，待人工确认）

扫描 OpenRouter 全量 464 个模型，发现 **11** 个未登记候选（疑似旗舰 **6** 个）：

| 模型 | 厂商 | 上架 | 距今 | 输入 $/1M | 输出 $/1M | 判定 |
|---|---|---|---|---|---|---|
| `openai/gpt-6.1-sol-pro`（GPT-6.1 Sol Pro） | OpenAI | 2026-09-29 | 2 天 | $2 | $10 | 疑似旗舰 |
| `qwen/qwen3.8-max-prime`（Qwen3.8 Max Prime） | 通义千问 | 2026-09-23 | 8 天 | $4 | $12 | 疑似旗舰 |
| `z-ai/glm-5.3-prime`（GLM 5.3 Prime） | GLM | 2026-09-23 | 8 天 | $2.8 | $8.8 | 疑似旗舰 |
| `openai/gpt-6-sol-pro`（GPT-6 Sol Pro） | OpenAI | 2026-09-22 | 9 天 | $2 | $10 | 疑似旗舰 |
| `x-ai/grok-4.7`（Grok 4.7） | xAI | 2026-09-21 | 10 天 | $2 | $6 | 疑似旗舰 |
| `anthropic/claude-fable-5.1`（Claude Fable 5.1） | Anthropic | 2026-09-01 | 30 天 | $10 | $50 | 疑似旗舰 |
| `anthropic/claude-sonnet-5.5`（Claude Sonnet 5.5） | Anthropic | 2026-09-28 | 3 天 | $2 | $10 | 新增档位 |
| `openai/gpt-6-luna-pro`（GPT-6 Luna Pro） | OpenAI | 2026-09-22 | 9 天 | $0.1 | $0.5 | 新增档位 |
| `qwen/qwen3.8-omni-flash`（Qwen3.8 Omni Flash） | 通义千问 | 2026-09-21 | 11 天 | $0.15 | $0.47 | 新增档位 |
| `qwen/qwen3.8-max-0902`（Qwen3.8 Max (0902)） | 通义千问 | 2026-09-03 | 28 天 | $2 | $6 | 新增档位 |
| `qwen/qwen3.8-2.4t-a95b`（Qwen3.8 2.4T A95B） | 通义千问 | 2026-08-12 | 50 天 | $2 | $6 | 新增档位 |

<details><summary>待登记 YAML（粘贴到 <code>config/new_models.yml</code>）</summary>

```yaml
models:
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
  - canonical: GLM 5.3 Prime
    family: GLM
    region: domestic
    status: tracking
    priority: high
    aliases: [GLM 5.3 Prime, glm-5.3-prime, z-ai/glm-5.3-prime]
    note: 雷达自动发现（OpenRouter 2026-09-23 上架，$2.8/$8.8）；确认后补官网抓取/白名单并转 active
  - canonical: GPT-6 Sol Pro
    family: OpenAI
    region: overseas
    status: tracking
    priority: high
    aliases: [GPT-6 Sol Pro, gpt-6-sol-pro, openai/gpt-6-sol-pro]
    note: 雷达自动发现（OpenRouter 2026-09-22 上架，$2/$10）；确认后补官网抓取/白名单并转 active
  - canonical: Grok 4.7
    family: xAI
    region: overseas
    status: tracking
    priority: high
    aliases: [Grok 4.7, grok-4.7, x-ai/grok-4.7]
    note: 雷达自动发现（OpenRouter 2026-09-21 上架，$2/$6）；确认后补官网抓取/白名单并转 active
  - canonical: Claude Fable 5.1
    family: Anthropic
    region: overseas
    status: tracking
    priority: high
    aliases: [Claude Fable 5.1, claude-fable-5.1, anthropic/claude-fable-5.1]
    note: 雷达自动发现（OpenRouter 2026-09-01 上架，$10/$50）；确认后补官网抓取/白名单并转 active
```

</details>
