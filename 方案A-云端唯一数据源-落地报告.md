# 方案 A 落地 + scrape.yml 故障排查报告

> 2026-08-22 · 目标：理顺本机 cron 与 GitHub Action 定位（消除双写竞争）+ 修复 scrape.yml 08-21 门禁误报根因 + 完成开发任务收尾

---

## 一、两手抓：故障排查 + 开发任务整理

按要求把「本轮开发任务」与「scrape.yml 故障」全部梳理、落地、验证完毕。

### 1. scrape.yml 08-21 两次 failure 根因（已闭环）

| 项 | 内容 |
|---|---|
| 现象 | `Run scraper` 失败、`deploy` 被跳过，开出 issue #28/#29「⛔ 数据门禁拦截」 |
| 根因 | `OUTLIER_PRICE` 误报：GPT-5.5 Pro 的 `output_rmb = 1260 > 1000` 阈值，被误判为 Tier1 high 阻断门禁（RMB 换算放大美元价） |
| 修复 | HEAD `core/audit.py` 已含 **USD 隔离逻辑**：用原始美元价（180）对比，`180 < 1000` 不再误报 |
| 验证 | 构造函数复现 GPT-5.5 Pro（out_rmb=1260）→ `tier1_high=0, gate: pass, OUTLIER_PRICE=0` ✅ |

**无需新代码**——HEAD 逻辑已兜住，构造数据证明不再误报。

### 2. 本机 cron vs GitHub Action 定位（方案 A 定稿）

用户三选一决策：**方案 A：云端唯一数据源**。

- **GitHub Action**（scrape.yml，UTC 17:00 = 北京时间 01:00）：唯一权威抓取源，负责抓取 + push `data/` + `site/` + 数据门禁。
- **本机 automation-1787338740315**（每日 10:40）：改为**纯只读消费**——`git pull` 云端 → `verify-only` 校验 → 异常上报。**绝不抓取、绝不写 data/、绝不 push**。

---

## 二、代码改动（commit `d94ad7f`）

| 文件 | 改动 |
|---|---|
| `main.py` | 新增 `--verify-only` 纯只读验证入口（不抓取、不写 data/，仅校验磁盘现有数据） |
| `core/audit.py` | `run()` 增加 `write_audit` 参数（默认 True 保持原行为；verify-only 传 False 不写 audit_report.md/audit.json） |
| `core/openrouter_verify.py` | `verify()` 增加 `write_audit` 参数（同上，纯只读跳过 `_write`） |
| `.gitignore` | 忽略 `.workbuddy/automations/`（WorkBuddy 运行时本地产物） |

---

## 三、验证结果（全套绿）

| 验证 | 结果 |
|---|---|
| **纯只读确认** | `verify-only` 运行前后 data/ 全部文件 mtime 完全一致（零写入）✅ |
| **verify-only 校验** | 可疑项 high 0 / med 29 / low 57，OpenRouter ok=True，退出码 0 ✅ |
| **真实全链路 dry-run**（17 源） | 全量 421 记录，命中 135，high 0 / med 29 / low 57，OpenRouter ok=True → **门禁彻底绿** ✅ |
| **mypy**（core/ scrapers/ main.py） | Success: no issues found in 31 source files ✅ |
| **pytest** | 100% 通过 ✅ |
| **构造数据复现误报**（GPT-5.5 Pro） | tier1_high=0, gate pass, OUTLIER_PRICE=0 → USD 隔离生效 ✅ |

---

## 四、自动化状态

`automation-1787338740315`（每日 Token 定价抓取）prompt 已改写为只读消费模式：

```
1. git pull --ff-only 拉取云端最新 data/ 与 site/
2. python main.py --verify-only 纯只读校验
3. 校验异常（Tier1 high）→ 报错用户；否则静默成功

铁律：绝不运行裸 python main.py（重抓写 data/），绝不 push。
push 与权威抓取只属于 GitHub Action。
```

---

## 五、提交历史

```
4845d9d chore(memory): 更新方案A定位与每日抓取只读消费说明
1a4ec76 chore(memory): 记录方案A落地与verify-only入口
d94ad7f feat(cli): 新增 --verify-only 纯只读验证入口，支撑方案A云端唯一数据源
3e0e874 chore: 提交抓取产物 + 构建产物 + 审计交付物
04daf39 fix(audit): 补提交 OPENAI_LONG_DEV 降级规则（此前从未进入 commit）
```

已全部推送 `origin/main`，本地与远程完全同步。

---

## 六、开发任务收尾

| 任务 | 状态 | 说明 |
|---|---|---|
| Claude 4.5+ 全系收录 | ✅ | `534dacc` 已推送（Opus 5 / Sonnet 5 等） |
| GPT-5.5+ 全系收录 | ✅ | `ea882b9` 已推送（GPT-5.5 / GPT-5.5 Pro 双档） |
| CI 门禁（mypy + pytest） | ✅ | push 触发 ci.yml 自动跑，本地等价验证全绿 |

> 注：本地无 `GITHUB_TOKEN`，无法手动 `workflow_dispatch` 触发 scrape.yml；但代码改动会触发 ci.yml 自动门禁，scrape.yml 每日 01:00 自动抓取。门禁健康性已通过等价逻辑 + 全链路 dry-run 充分证明。
