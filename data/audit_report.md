# 数据核对报告（自我检查机制）

> 生成时间：2026-11-27 10:23:52

## 一、核对统计

- 门禁状态：**✅ 通过**
- 校验记录总数：**73**
- 可疑项总数：**24**（high 4 / med 18 / low 2）
- Tier1 结构性校验可疑：**20**
- Tier2 源页面核对可疑：**4**

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
| med | T1 | CACHE_SUSPECT | openrouter | DeepSeek V4 Pro 0813 | 缓存命中价(0.0999) 接近输入价(0.0999)，异常偏高 |
| med | T1 | CACHE_SUSPECT | openrouter | GLM-5.3 | 缓存命中价(0.0689) 接近输入价(0.0699)，异常偏高 |
| med | T1 | CACHE_SUSPECT | openrouter | Kimi K3 | 缓存命中价(0.182) 接近输入价(0.192)，异常偏高 |
| med | T1 | CACHE_RATIO_ANOMALY | aliyun_bailian | DeepSeek V3.2 | 缓存/输入比率(20%) 偏离同模型基准(50%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | aliyun_bailian | DeepSeek V4 Pro | 缓存/输入比率(20%) 偏离同模型基准(8%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | deepseek | DeepSeek V4 Pro | 缓存/输入比率(3%) 偏离同模型基准(8%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | deepseek_us | DeepSeek V4 Pro | 缓存/输入比率(3%) 偏离同模型基准(8%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | openrouter | DeepSeek V4 Pro | 缓存/输入比率(23%) 偏离同模型基准(8%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | aliyun_bailian | DeepSeek V4.1 Flash | 缓存/输入比率(20%) 偏离同模型基准(3%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | atlascloud | DeepSeek V4.1 Flash | 缓存/输入比率(10%) 偏离同模型基准(3%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | deepseek | DeepSeek V4.1 Flash | 缓存/输入比率(2%) 偏离同模型基准(3%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | deepseek_us | DeepSeek V4.1 Flash | 缓存/输入比率(2%) 偏离同模型基准(3%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | openrouter | GLM-5.3 | 缓存/输入比率(99%) 偏离同模型基准(20%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | atlascloud | Kimi K2.6 | 缓存/输入比率(17%) 偏离同模型基准(20%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | openrouter | Kimi K2.6 | 缓存/输入比率(23%) 偏离同模型基准(20%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | atlascloud | Kimi K2.7 Code | 缓存/输入比率(17%) 偏离同模型基准(20%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | atlascloud | Kimi K3 | 缓存/输入比率(10%) 偏离同模型基准(20%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| med | T1 | CACHE_RATIO_ANOMALY | openrouter | Kimi K3 | 缓存/输入比率(95%) 偏离同模型基准(20%) 超 15%，疑似缓存价缺失/估算口径不一致 |
| low | T1 | DIVERGE | - | GLM-5.3 | 跨源输入价离散 20.0× (最低 0.4893 / 最高 9.8)，建议人工核对是否同规格模型 |
| low | T1 | DIVERGE | - | Kimi K3 | 跨源输入价离散 15.6× (最低 1.344 / 最高 21.0)，建议人工核对是否同规格模型 |

> ⚠️ high 级别需立即人工核对并修正；med 级别建议复核；low 级别多为 SPA 渲染提示。
