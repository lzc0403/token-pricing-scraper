# 数据核对报告（自我检查机制）

> 生成时间：2026-10-28 07:48:38

## 一、核对统计

- 门禁状态：**✅ 通过**
- 校验记录总数：**124**
- 可疑项总数：**34**（high 4 / med 26 / low 4）
- Tier1 结构性校验可疑：**28**
- Tier2 源页面核对可疑：**6**

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
| high | T2 | PRICE_NOT_FOUND | aliyun | Qwen3.7 Max | 静态源页面未找到input价数值「14.4」，疑似解析/幻觉错误 |
| high | T2 | PRICE_NOT_FOUND | aliyun | Qwen3.7 Max | 静态源页面未找到output价数值「43.2」，疑似解析/幻觉错误 |
| high | T2 | PRICE_NOT_FOUND | aliyun | Qwen3.7 Plus | 静态源页面未找到input价数值「2.4」，疑似解析/幻觉错误 |
| high | T2 | PRICE_NOT_FOUND | aliyun | Qwen3.7 Plus | 静态源页面未找到output价数值「9.6」，疑似解析/幻觉错误 |
| med | T1 | CACHE_SUSPECT | openrouter | GLM-5.3 | 缓存命中价(0.0689) 接近输入价(0.0699)，异常偏高 |
| med | T1 | CACHE_SUSPECT | openrouter | Kimi K3 | 缓存命中价(0.19) 接近输入价(0.2)，异常偏高 |
| med | T1 | CACHE_RATIO_ANOMALY | aliyun_bailian | DeepSeek V3.2 | 缓存/输入比率(20%) 偏离同模型基准(50%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | aliyun_bailian | DeepSeek V4 Pro | 缓存/输入比率(20%) 偏离同模型基准(8%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | deepseek | DeepSeek V4 Pro | 缓存/输入比率(3%) 偏离同模型基准(8%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | deepseek_us | DeepSeek V4 Pro | 缓存/输入比率(3%) 偏离同模型基准(8%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | aliyun_bailian | DeepSeek V4.1 Flash | 缓存/输入比率(20%) 偏离同模型基准(3%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | atlascloud | DeepSeek V4.1 Flash | 缓存/输入比率(10%) 偏离同模型基准(3%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | deepseek | DeepSeek V4.1 Flash | 缓存/输入比率(2%) 偏离同模型基准(3%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | deepseek_us | DeepSeek V4.1 Flash | 缓存/输入比率(2%) 偏离同模型基准(3%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | tencent_cn | DeepSeek V4.1 Flash | 缓存/输入比率(2%) 偏离同模型基准(3%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | openrouter | GLM-5.3 | 缓存/输入比率(99%) 偏离同模型基准(19%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | atlascloud | Kimi K2.6 | 缓存/输入比率(17%) 偏离同模型基准(20%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | openrouter | Kimi K2.6 | 缓存/输入比率(23%) 偏离同模型基准(20%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | tencent_cn | Kimi K2.6 | 缓存/输入比率(17%) 偏离同模型基准(20%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | atlascloud | Kimi K2.7 Code | 缓存/输入比率(17%) 偏离同模型基准(20%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | atlascloud | Kimi K3 | 缓存/输入比率(10%) 偏离同模型基准(20%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | openrouter | Kimi K3 | 缓存/输入比率(95%) 偏离同模型基准(20%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | tencent_cn | Kimi K3 | 缓存/输入比率(10%) 偏离同模型基准(20%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | DUPLICATE | tencent | - | 重复记录 ×2: DeepSeek-V4-Pro |
| med | T1 | DUPLICATE | tencent | - | 重复记录 ×2: DeepSeek-V4-Pro |
| med | T1 | OPENAI_LONG_DEV_CH | openai | GPT-5.6 Luna | OpenAI 长上下文input价(0.4) 与 OpenRouter 标准档(0.2) 偏差 100.0%，属渠道定价差异（OR 无长档可对标） |
| med | T1 | OPENAI_LONG_DEV_CH | openai | GPT-5.6 Luna | OpenAI 长上下文output价(1.8) 与 OpenRouter 标准档(1.2) 偏差 50.0%，属渠道定价差异（OR 无长档可对标） |
| med | T1 | OPENAI_LONG_NO_OR | openai | GPT-5.6 Sol | OpenAI 硬编码长上下文价 GPT-5.6 Sol 无对应 OpenRouter 记录可交叉校验 |
| med | T1 | OPENAI_LONG_DEV_CH | openai | GPT-5.6 Terra | OpenAI 长上下文input价(4.0) 与 OpenRouter 标准档(2.0) 偏差 100.0%，属渠道定价差异（OR 无长档可对标） |
| med | T1 | OPENAI_LONG_DEV_CH | openai | GPT-5.6 Terra | OpenAI 长上下文output价(18.0) 与 OpenRouter 标准档(12.0) 偏差 50.0%，属渠道定价差异（OR 无长档可对标） |
| low | T1 | DIVERGE | - | GLM-5.3 | 跨源输入价离散 20.6× (最低 0.4893 / 最高 10.07524)，建议人工核对是否同规格模型 |
| low | T1 | DIVERGE | - | Kimi K3 | 跨源输入价离散 15.7× (最低 1.4 / 最高 21.974)，建议人工核对是否同规格模型 |
| low | T2 | SPA_NEED_RENDER | volcengine | Doubao Seed 2.1 Pro | SPA 源静态 HTML 未含模型名「doubao-seed-」，需 Playwright 渲染核对 |
| low | T2 | SPA_NEED_RENDER | volcengine | Doubao Seed 2.1 Turbo | SPA 源静态 HTML 未含模型名「doubao-seed-」，需 Playwright 渲染核对 |

> ⚠️ high 级别需立即人工核对并修正；med 级别建议复核；low 级别多为 SPA 渲染提示。
