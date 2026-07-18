# AGENTS.md — token 定价项目约定

## 红线

1. **不要手改 `site/index.html`**：一律改 `core/site.py` 再 `build_site`。
2. ModelMesh 展示名永远是 **胜算云**，内部 id 仍为 `modelmesh`。
3. 海外主力列表保持「热门精简」，**GPT-4o 必须在榜**；不要批量塞 mini/nano/lite。
4. OpenRouter：先写 `config/openrouter.yml`，再跑抓取；必须过 `openrouter_verify`。
5. 写任何自动生成数据前：二次验证失败时要在日志/报告中标出，禁止静默当成功。

## 常用命令

```bash
.venv\Scripts\python.exe main.py --dry-run
.venv\Scripts\python.exe -c "from core.site import build_site; print(build_site('data'))"
.venv\Scripts\python.exe -c "from core import openrouter_verify; print(openrouter_verify.verify('data'))"
```

## 配置入口

| 文件 | 用途 |
|------|------|
| config/sources.yml | 数据源 |
| config/models.yml | 国内匹配别名 |
| config/openrouter.yml | OpenRouter 白名单与验证阈值 |
| config/new_models.yml | 新品监听 |

## 模块地图

- scrapers/* — 解析器
- core/site.py — 站点
- core/audit.py — 全源核对
- core/openrouter_verify.py — OpenRouter 专用验证
- main.py — 编排

详细：docs/architecture.md
