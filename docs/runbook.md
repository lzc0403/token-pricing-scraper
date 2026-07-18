# Runbook

## 日常抓取

```bash
.venv\Scripts\python.exe main.py --dry-run
```

检查：

1. 各源 `[ok]` / `[FAIL]` 日志
2. `data/audit_report.md` high 是否为 0
3. `data/openrouter_verify.md` 是否 ✅ 通过
4. 打开 `site/index.html`：OpenRouter pill、GPT-4o、新品雷达

## 常见故障

### OpenRouter HTTP 失败

- 检查网络能否访问 `openrouter.ai`
- 是否被代理拦截；可先 `curl` 端点
- 缓存旧文件：删除 `data/openrouter_raw.json` 后重跑

### 白名单缺失 `OR_WHITELIST_ABSENT`

- OpenRouter 改了 model id（版本号变化）
- 用 raw JSON 搜新 id，更新 `config/openrouter.yml`

### 价格错一个数量级

- 确认没有「二次 *1e6」；raw 已是 per-token
- 看 verify 报告 `OR_PRICE_MISMATCH`

### SPA 源全 0 条

- Playwright / Chromium 是否安装
- CI 地区是否被目标站拦截（已有 networkidle 回退）

### 页面无 OpenRouter

- 确认 `SOURCE_LABELS` 有 openrouter
- watchlist 里是否有 `source=openrouter` 且带 `canonical`
- 重新 `site.build_site('data')`

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `USD_CNY_RATE` | 7.2（currency 模块） | 抓取换算；网页交互默认 7.0 |

## 冒烟清单

- [ ] openrouter 记录数 > 0
- [ ] verify ok=true, high=0
- [ ] site 含 `OpenRouter` 与 `GPT-4o`
- [ ] 新品区含 MiniMax M3 / Kimi K3
- [ ] Excel 导出按钮可用
