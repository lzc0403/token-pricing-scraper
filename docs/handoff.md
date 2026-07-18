# Handoff / 完成状态（2026-07-18）

## 已完成

- [x] 静态站点生成与多轮 UI 优化（筛选、汇率、Excel、国内/海外分页）
- [x] 数据源中文展示；ModelMesh → 胜算云
- [x] 海外主流专区（仅热门：GPT-5 / GPT-4o / Claude / Gemini）
- [x] 新品主动跟进：`config/new_models.yml` + 页面雷达
- [x] **OpenRouter 接入**：抓取 / 缓存 / 白名单 / 二次验证 / 站点展示
- [x] 全源 audit + OpenRouter verify
- [x] CloudStudio 部署：https://0946e061d8e1463e8946a119b5aa0afb.app.codebuddy.work

## 数据源一览

aliyun / volcengine / tencent / bigmodel / deepseek / minimax / kimi / modelmesh / **openrouter**

## 后续建议（未做）

- [ ] OpenRouter top-weekly 补充模型也做 canonical 自动学习
- [ ] audit 对 SPA 源升级 Playwright 权威核对
- [ ] 新品列表与 OpenRouter whitelist 单一配置源合并
- [ ] 历史价格 sparkline

## 接手注意

1. **别手改 `site/index.html`**，改 `core/site.py` 后 `build_site`
2. OpenRouter 规则以 `config/openrouter.yml` 为准
3. 二次验证报告在 `data/openrouter_verify.md`
4. 前端汇率默认 7.0，与后台 currency 默认 7.2 可能不同——页面以用户输入为准
