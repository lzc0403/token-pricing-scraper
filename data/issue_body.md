## 🔔 Token 定价变动（2026-09-23 07:04:37）

| 模型 | 源 | 字段 | 旧值 | 新值 | 货币 |
| --- | --- | --- | ---: | ---: | --- |
| MiniMax M3 | minimax | 输入 | 4.2 | 2.1 | CNY |
| MiniMax M3 | minimax | 输出 | 16.8 | 8.4 | CNY |

## 🆕 新模型雷达（未登记候选，待人工确认）

扫描 OpenRouter 全量 454 个模型，发现 **10** 个未登记候选（疑似旗舰 **6** 个）：

| 模型 | 厂商 | 上架 | 距今 | 输入 $/1M | 输出 $/1M | 判定 |
|---|---|---|---|---|---|---|
| `openai/gpt-6-sol`（GPT-6 Sol） | OpenAI | 2026-09-22 | 0 天 | $2 | $10 | 疑似旗舰 |
| `openai/gpt-6-sol-pro`（GPT-6 Sol Pro） | OpenAI | 2026-09-22 | 0 天 | $2 | $10 | 疑似旗舰 |
| `x-ai/grok-4.7`（Grok 4.7） | xAI | 2026-09-21 | 1 天 | $1.6 | $4.8 | 疑似旗舰 |
| `qwen/qwen3.8-max-0902`（Qwen3.8 Max (0902)） | 通义千问 | 2026-09-03 | 19 天 | $2 | $6 | 疑似旗舰 |
| `anthropic/claude-fable-5.1`（Claude Fable 5.1） | Anthropic | 2026-09-01 | 21 天 | $10 | $50 | 疑似旗舰 |
| `qwen/qwen3.8-2.4t-a95b`（Qwen3.8 2.4T A95B） | 通义千问 | 2026-08-12 | 41 天 | $2 | $6 | 疑似旗舰 |
| `anthropic/claude-opus-5.5`（Claude Opus 5.5） | Anthropic | 2026-09-22 | 0 天 | $4 | $20 | 新增档位 |
| `openai/gpt-6-luna`（GPT-6 Luna） | OpenAI | 2026-09-22 | 0 天 | $0.1 | $0.5 | 新增档位 |
| `openai/gpt-6-luna-pro`（GPT-6 Luna Pro） | OpenAI | 2026-09-22 | 0 天 | $0.1 | $0.5 | 新增档位 |
| `qwen/qwen3.8-omni-flash`（Qwen3.8 Omni Flash） | 通义千问 | 2026-09-21 | 2 天 | $0.15 | $0.47 | 新增档位 |

<details><summary>待登记 YAML（粘贴到 <code>config/new_models.yml</code>）</summary>

```yaml
models:
  - canonical: GPT-6 Sol
    family: OpenAI
    region: overseas
    status: tracking
    priority: high
    aliases: [GPT-6 Sol, gpt-6-sol, openai/gpt-6-sol]
    note: 雷达自动发现（OpenRouter 2026-09-22 上架，$2/$10）；确认后补官网抓取/白名单并转 active
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
    note: 雷达自动发现（OpenRouter 2026-09-21 上架，$1.6/$4.8）；确认后补官网抓取/白名单并转 active
  - canonical: Qwen3.8 Max (0902)
    family: 通义千问
    region: domestic
    status: tracking
    priority: high
    aliases: [Qwen3.8 Max (0902), qwen3.8-max-0902, qwen/qwen3.8-max-0902]
    note: 雷达自动发现（OpenRouter 2026-09-03 上架，$2/$6）；确认后补官网抓取/白名单并转 active
  - canonical: Claude Fable 5.1
    family: Anthropic
    region: overseas
    status: tracking
    priority: high
    aliases: [Claude Fable 5.1, claude-fable-5.1, anthropic/claude-fable-5.1]
    note: 雷达自动发现（OpenRouter 2026-09-01 上架，$10/$50）；确认后补官网抓取/白名单并转 active
  - canonical: Qwen3.8 2.4T A95B
    family: 通义千问
    region: domestic
    status: tracking
    priority: high
    aliases: [Qwen3.8 2.4T A95B, qwen3.8-2.4t-a95b, qwen/qwen3.8-2.4t-a95b]
    note: 雷达自动发现（OpenRouter 2026-08-12 上架，$2/$6）；确认后补官网抓取/白名单并转 active
```

</details>
