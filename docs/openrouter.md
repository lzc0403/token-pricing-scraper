# OpenRouter 接入指南

## 端点

```
GET https://openrouter.ai/api/v1/models?sort=top-weekly
```

无需 API Key。返回 `data[]`，字段含：

- `id`：如 `openai/gpt-4o`
- `name`
- `pricing.prompt` / `pricing.completion`：**USD / token**
- `context_length`

解析时换算：

```
USD_per_1M = float(pricing.prompt) * 1_000_000
```

## 配置

### `config/sources.yml`

```yaml
- id: openrouter
  name: OpenRouter
  url: https://openrouter.ai/api/v1/models?sort=top-weekly
  parser: openrouter
  currency: USD
  js: false
  cache_path: data/openrouter_raw.json
  rules_path: config/openrouter.yml
```

### `config/openrouter.yml`

- `whitelist`：热门主力（GPT-4o、GPT-5、Claude Sonnet 5、Gemini 2.5、MiniMax M3、Kimi K3…）
- `top_weekly_extra`：额外收录的非免费文本模型数量
- `exclude_free`：跳过 0 价
- `verify.price_tol`：二次验证相对容差

## 代码入口

| 文件 | 职责 |
|------|------|
| `scrapers/openrouter.py` | 下载、缓存、解析 |
| `core/openrouter_verify.py` | 二次验证 |
| `main.py` | 白名单强制 canonical + 调验证 |

## 本地手动验证

```bash
.venv\Scripts\python.exe -c "from scrapers.openrouter import OpenrouterScraper; import yaml; s=next(x for x in yaml.safe_load(open('config/sources.yml',encoding='utf-8')) if x['id']=='openrouter'); recs=OpenrouterScraper(s).run(); print(len(recs)); print(recs[0])"
.venv\Scripts\python.exe -c "from core import openrouter_verify; print(openrouter_verify.verify('data'))"
```

## 产物

| 文件 | 说明 |
|------|------|
| `data/openrouter_raw.json` | 原始 API（含 fetched_at） |
| `data/openrouter_verify.json` | 机读验证结果 |
| `data/openrouter_verify.md` | 人类可读报告 |

## 错误码（验证）

| code | 含义 |
|------|------|
| OR_ID_MISSING | 解析记录找不到原始 id |
| OR_PRICE_MISMATCH | 换算价与 raw 不一致 |
| OR_WHITELIST_MISS | 白名单在 API 有但未解析进结果 |
| OR_WHITELIST_ABSENT | 白名单 id 在 API 中不存在（需更新 yml） |

## 更新白名单

1. 打开 OpenRouter Models 或查 raw JSON `id`
2. 写入 `config/openrouter.yml` whitelist
3. 如需进国内匹配，同步 `config/models.yml` / `new_models.yml`
4. 跑 `main.py` → 看 `openrouter_verify.md` 是否 ok
