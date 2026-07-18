# 数据核对报告（自我检查机制）

> 生成时间：2026-07-17 23:46:44

## 一、核对统计

- 校验记录总数：**38**
- 可疑项总数：**37**（high 0 / med 0 / low 37）
- Tier1 结构性校验可疑：**1**
- Tier2 源页面核对可疑：**36**

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
| low | T1 | DIVERGE | - | Seedance 2.0 | 跨源输入价离散 16.0× (最低 0.2 / 最高 3.2)，建议人工核对是否同规格模型 |
| low | T2 | SPA_NEED_RENDER | aliyun | qwen3.7 | SPA 源静态 HTML 未含模型名「qwen3.7-max当」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | aliyun | qwen3.7 | SPA 源静态 HTML 未含模型名「qwen3.7-plus」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | bigmodel | GLM-5.1 | SPA 源静态 HTML 未含模型名「GLM-5.1」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | bigmodel | GLM-5.2 | SPA 源静态 HTML 未含模型名「GLM-5.2 新品」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | kimi | Kimi K2.6 | SPA 源静态 HTML 未含模型名「kimi-k2.6」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | minimax | MiniMax M2.7 | SPA 源静态 HTML 未含模型名「MiniMax-M2.7」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | minimax | MiniMax M2.7 | SPA 源静态 HTML 未含模型名「MiniMax-M2.7」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | modelmesh | DeepSeek V3.2 | SPA 源静态 HTML 未含模型名「DeepSeek V3.」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | modelmesh | DeepSeek V3.2 | SPA 源静态 HTML 未含模型名「Deepseek V3.」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | modelmesh | DeepSeek V4 Flash | SPA 源静态 HTML 未含模型名「DeepSeek-V4-」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | modelmesh | DeepSeek V4 Pro | SPA 源静态 HTML 未含模型名「DeepSeek-V4-」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | modelmesh | GLM-5.1 | SPA 源静态 HTML 未含模型名「GLM-5.1」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | modelmesh | GLM-5.2 | SPA 源静态 HTML 未含模型名「GLM-5.2」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | modelmesh | Kimi K2.6 | SPA 源静态 HTML 未含模型名「Kimi K2.6」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | modelmesh | MiniMax M2.7 | SPA 源静态 HTML 未含模型名「MiniMax M2.7」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | modelmesh | MiniMax M2.7 | SPA 源静态 HTML 未含模型名「MiniMax M2.7」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | modelmesh | Seedance 2.0 | SPA 源静态 HTML 未含模型名「Doubao-Seed-」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | modelmesh | Seedance 2.0 | SPA 源静态 HTML 未含模型名「Doubao-Seed-」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | modelmesh | Seedance 2.0 | SPA 源静态 HTML 未含模型名「Doubao-Seed-」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | modelmesh | Seedance 2.0 | SPA 源静态 HTML 未含模型名「Doubao-Seed-」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | modelmesh | qwen3.7 | SPA 源静态 HTML 未含模型名「Qwen3.7-Plus」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | modelmesh | qwen3.7 | SPA 源静态 HTML 未含模型名「Qwen3.7-Max」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | tencent | DeepSeek V3.2 | SPA 源静态 HTML 未含模型名「Deepseek-v3.」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | tencent | DeepSeek V4 Flash | SPA 源静态 HTML 未含模型名「DeepSeek-V4-」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | tencent | DeepSeek V4 Flash | SPA 源静态 HTML 未含模型名「DeepSeek-V4-」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | tencent | DeepSeek V4 Pro | SPA 源静态 HTML 未含模型名「DeepSeek-V4-」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | tencent | DeepSeek V4 Pro | SPA 源静态 HTML 未含模型名「DeepSeek-V4-」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | tencent | GLM-5.1 | SPA 源静态 HTML 未含模型名「GLM-5.1」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | tencent | GLM-5.1 | SPA 源静态 HTML 未含模型名「GLM-5.1」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | tencent | GLM-5.2 | SPA 源静态 HTML 未含模型名「GLM-5.2」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | tencent | Kimi K2.6 | SPA 源静态 HTML 未含模型名「kimi-k2.6」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | tencent | MiniMax M2.7 | SPA 源静态 HTML 未含模型名「MiniMax-M2.7」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | volcengine | Seedance 2.0 | SPA 源静态 HTML 未含模型名「doubao-seed-」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | volcengine | Seedance 2.0 | SPA 源静态 HTML 未含模型名「doubao-seed-」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | volcengine | Seedance 2.0 | SPA 源静态 HTML 未含模型名「doubao-seed-」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | volcengine | Seedance 2.0 | SPA 源静态 HTML 未含模型名「doubao-seed-」，需 Playwright 渲染核对 |

> ⚠️ high 级别需立即人工核对并修正；med 级别建议复核；low 级别多为 SPA 渲染提示。
