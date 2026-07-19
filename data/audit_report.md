# 数据核对报告（自我检查机制）

> 生成时间：2026-07-19 17:02:39

## 一、核对统计

- 校验记录总数：**26**
- 可疑项总数：**16**（high 8 / med 0 / low 8）
- Tier1 结构性校验可疑：**1**
- Tier2 源页面核对可疑：**15**

## 二、核对维度

| 层级 | 维度 | 说明 |
| --- | --- | --- |
| Tier1 | EMPTY_MODEL/INPUT/OUTPUT | 关键字段空值 |
| Tier1 | NEG_PRICE / OUTLIER_PRICE | 负值或超 1000 ¥/1M 的离谱价 |
| Tier1 | RATE_MISMATCH | USD 换算 input_rmb ≠ input×rate（容差 1%） |
| Tier1 | DUPLICATE | 同源同模型同价重复 |
| Tier1 | LOWEST_MISMATCH | is_lowest_input 标注与实际不符 |
| Tier1 | DIVERGE | 同模型跨源输入价 >10× 离散 |
| Tier2 | MODEL_NOT_FOUND | 静态源页面未找到模型名（疑似幻觉） |
| Tier2 | PRICE_NOT_FOUND | 静态源页面未找到价格数值（疑似解析错） |
| Tier2 | SPA_NEED_RENDER | SPA 源需 Playwright 渲染才能核对 |
| Tier2 | SRC_UNREACHABLE | 源页面抓取失败 |

## 三、可疑项明细（按严重度排序）

| 严重度 | 层级 | 代码 | 源 | 模型 | 说明 |
| --- | --- | --- | --- | --- | --- |
| high | T2 | PRICE_NOT_FOUND | openrouter | DeepSeek V4 Flash | 静态源页面未找到input价数值「0.098」，疑似解析/幻觉错误 |
| high | T2 | PRICE_NOT_FOUND | openrouter | DeepSeek V4 Flash | 静态源页面未找到output价数值「0.196」，疑似解析/幻觉错误 |
| high | T2 | PRICE_NOT_FOUND | openrouter | DeepSeek V4 Pro | 静态源页面未找到input价数值「0.435」，疑似解析/幻觉错误 |
| high | T2 | PRICE_NOT_FOUND | openrouter | DeepSeek V4 Pro | 静态源页面未找到output价数值「0.87」，疑似解析/幻觉错误 |
| high | T2 | PRICE_NOT_FOUND | openrouter | GLM-5.2 | 静态源页面未找到input价数值「0.2716」，疑似解析/幻觉错误 |
| high | T2 | PRICE_NOT_FOUND | openrouter | GLM-5.2 | 静态源页面未找到output价数值「0.8536」，疑似解析/幻觉错误 |
| high | T2 | PRICE_NOT_FOUND | openrouter | Kimi K2.6 | 静态源页面未找到input价数值「0.684」，疑似解析/幻觉错误 |
| high | T2 | PRICE_NOT_FOUND | openrouter | Kimi K2.6 | 静态源页面未找到output价数值「3.42」，疑似解析/幻觉错误 |
| low | T1 | DIVERGE | - | Kimi K3 | 跨源输入价离散 10.8× (最低 2.0 / 最高 21.6)，建议人工核对是否同规格模型 |
| low | T2 | SPA_NEED_RENDER | bigmodel | GLM-5.1 | SPA 源静态 HTML 未含模型名「GLM-5.1」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | kimi | Kimi K2.6 | SPA 源静态 HTML 未含模型名「kimi-k2.6」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | kimi | Kimi K2.7 Code | SPA 源静态 HTML 未含模型名「kimi-k2.7-co」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | kimi | Kimi K3 | SPA 源静态 HTML 未含模型名「kimi-k3」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | minimax | MiniMax M2.7 | SPA 源静态 HTML 未含模型名「MiniMax-M2.7」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | volcengine | Doubao Seed 2.1 Pro | SPA 源静态 HTML 未含模型名「doubao-seed-」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | volcengine | Doubao Seed 2.1 Turbo | SPA 源静态 HTML 未含模型名「doubao-seed-」，需 Playwright 渲染核对 |

> ⚠️ high 级别需立即人工核对并修正；med 级别建议复核；low 级别多为 SPA 渲染提示。
