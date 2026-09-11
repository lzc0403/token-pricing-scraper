## 🔔 Token 定价变动（2026-09-11 06:54:11）

| 模型 | 源 | 字段 | 旧值 | 新值 | 货币 |
| --- | --- | --- | ---: | ---: | --- |
| DeepSeek V4 Pro 0813 | openrouter | 输入 | 1.0494 | 0.66 | USD |
| DeepSeek V4 Pro 0813 | openrouter | 输出 | 3.1482 | 1.98 | USD |
| Kimi K3 | openrouter | 输入 | 3 | 2.34 | USD |
| Kimi K3 | openrouter | 输出 | 15 | 11.7 | USD |
| GLM-5.3-Flash | openrouter | 输入 | 0.075 | 0.15 | USD |
| GLM-5.3-Flash | openrouter | 输出 | 0.25 | 0.5 | USD |
| MiniMax M3 | minimax | 输入 | 4.2 | 2.1 | CNY |
| MiniMax M3 | minimax | 输出 | 16.8 | 8.4 | CNY |

## 🆕 新模型雷达（未登记候选，待人工确认）

扫描 OpenRouter 全量 439 个模型，发现 **1** 个未登记候选（疑似旗舰 **1** 个）：

| 模型 | 厂商 | 上架 | 距今 | 输入 $/1M | 输出 $/1M | 判定 |
|---|---|---|---|---|---|---|
| `qwen/qwen3.8-2.4t-a95b`（Qwen3.8 2.4T A95B） | 通义千问 | 2026-08-12 | 29 天 | $2 | $6 | 疑似旗舰 |

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
