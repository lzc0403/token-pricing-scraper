## 🔔 Token 定价变动（2026-09-20 07:19:59）

| 模型 | 源 | 字段 | 旧值 | 新值 | 货币 |
| --- | --- | --- | ---: | ---: | --- |
| DeepSeek V4 Pro | openrouter | 输入 | 0.564282 | 0.422298 | USD |
| DeepSeek V4 Pro | openrouter | 输出 | 1.12856 | 0.844596 | USD |
| DeepSeek V4 Flash | openrouter | 输入 | 0.04732 | 0.03668 | USD |
| DeepSeek V4 Flash | openrouter | 输出 | 0.09464 | 0.07336 | USD |
| Kimi K3 | openrouter | 输入 | 1.875 | 1.7 | USD |
| Kimi K3 | openrouter | 输出 | 10.5 | 8.5 | USD |
| GLM-5.3 | openrouter | 输入 | 0.91 | 0.896 | USD |
| GLM-5.3 | openrouter | 输出 | 2.86 | 2.816 | USD |
| GLM-5.2 | openrouter | 输入 | 0.5544 | 0.6496 | USD |
| GLM-5.2 | openrouter | 输出 | 1.7424 | 2.0416 | USD |
| MiniMax M3 | minimax | 输入 | 4.2 | 2.1 | CNY |
| MiniMax M3 | minimax | 输出 | 16.8 | 8.4 | CNY |
| Kimi K3 | kimi_ai | 输入 | 3 | 0.3 | USD |

## 🆕 新模型雷达（未登记候选，待人工确认）

扫描 OpenRouter 全量 446 个模型，发现 **1** 个未登记候选（疑似旗舰 **1** 个）：

| 模型 | 厂商 | 上架 | 距今 | 输入 $/1M | 输出 $/1M | 判定 |
|---|---|---|---|---|---|---|
| `qwen/qwen3.8-2.4t-a95b`（Qwen3.8 2.4T A95B） | 通义千问 | 2026-08-12 | 38 天 | $2 | $6 | 疑似旗舰 |

<details><summary>待登记 YAML（粘贴到 <code>config/new_models.yml</code>）</summary>

```yaml
models:
  - canonical: Qwen3.8 2.4T A95B
    family: 通义千问
    region: domestic
    status: tracking
    priority: high
    aliases: [Qwen3.8 2.4T A95B, qwen3.8-2.4t-a95b, qwen/qwen3.8-2.4t-a95b]
    note: 雷达自动发现（OpenRouter 2026-08-12 上架，$2/$6）；确认后补官网抓取/白名单并转 active
```

</details>
