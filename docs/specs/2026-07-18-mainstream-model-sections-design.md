# 国内与海外主流模型双专区设计规格

日期：2026-07-18  
状态：已获用户批准，待实施

## 1. 目标

在现有模型价格比价站中，将“快速认识主流模型”和“精确比较渠道价格”拆为两个层次：

1. 页面上方新增与海外专区同级的“国内主流大模型”专区；
2. 修正海外 Claude 型号层级、上下文和正式可用状态；
3. 国内、海外专区使用一致的卡片结构和交互；
4. 型号目录从 `core/site.py` 硬编码迁移为 YAML 配置，降低新品维护成本；
5. 修复豆包文本模型与 Seedance 视频模型混用的问题；
6. 保留现有官方原价、渠道报价、筛选、汇率换算和 Excel 导出能力。

## 2. 页面信息架构

页面自上而下：

1. 顶部摘要与更新时间；
2. 统一筛选栏：模型分类、渠道、人民币兑美元汇率、重置、Excel 导出；
3. 国内主流大模型专区；
4. 海外主流大模型专区；
5. 官方原价区；
6. 渠道报价区：中国大陆渠道与 OpenRouter 分区；
7. 数据源、校验状态和免责声明。

主流专区用于快速选型，不承载所有历史型号；报价表负责完整、精确的横向比较。

## 3. 国内主流专区

覆盖六大厂商：

- DeepSeek
- 通义千问
- 智谱 GLM
- Kimi
- MiniMax
- 豆包

每个厂商卡片只展示已经公开可用、仍属主力的旗舰或主力型号。默认每家 1–2 个；最多 3 个，防止卡片演变成型号列表。

初始 canonical 白名单以本项目当前官方源抓取结果为基线，并在实施时再次请求对应官方页面复核：

- DeepSeek：`DeepSeek V3.2`，卡片内区分 `deepseek-chat` 与 `deepseek-reasoner` 两种 API 模式；渠道中的 V4 在 DeepSeek 官网未确认前不得进入正式卡片；
- 通义千问：`Qwen3.7 Max`、`Qwen3.7 Plus`，必须拆分当前错误的合并 canonical `qwen3.7`；
- 智谱 GLM：`GLM-5.2`、`GLM-5.1`；
- Kimi：`Kimi K2.7 Code`、`Kimi K2.6`；K3 在 Kimi 官方源未确认前只保留在新品监听或渠道报价；
- MiniMax：`MiniMax M3`、`MiniMax M2.7`；
- 豆包：`Doubao Seed 2.1 Pro`、`Doubao Seed 2.1 Turbo`。

若实施日官方页面与上述基线不一致，以官方页面为准，但必须先更新本规格中的白名单和核验证据，不能由实现代码静默替换。

每个型号显示：

- 展示名称；
- 定位标签，如旗舰推理、主力通用、长上下文；
- 上下文窗口；
- 官方输入价和输出价；
- 币种与计价单位；
- 状态：正式、预览、监听中；
- 官方来源和核验日期。

点击型号后，与统一筛选栏联动，仅显示对应型号的官方价和渠道报价。

### 豆包与 Seedance 拆分

- `Doubao-Seed-*` 只归入文本/推理模型；
- `Seedance *` 归入视频生成模型，不进入文本 token 价格比较；
- 必须从 `config/models.yml` 删除 `Seedance 2.0` 下的 `Doubao-Seed-2.0` 别名，并为豆包文本模型建立独立 canonical；
- 由于 `core/matcher.py` 当前存在包含匹配，实施时必须增加 `modality` 边界或改为安全别名规则，禁止跨模态包含匹配；
- 正例：`doubao-seed-2.1-pro` → `Doubao Seed 2.1 Pro`，`seedance-2.0` → `Seedance 2.0`；
- 反例：`doubao-seed-2.0-pro` 不得 → `Seedance 2.0`，`doubao-seed-2.1-turbo` 不得 → 任意视频模型；
- 视频模型若未来展示，必须使用独立计价维度和专区，不能与元/百万 token 混表。

## 4. 海外主流专区

保留三大厂商：

- OpenAI：只展示热门主力，明确保留 GPT-4o；
- Anthropic Claude：展示正式公开主线；
- Google Gemini：只展示 Pro、Flash 等主力档位。

不堆叠 mini、nano、lite 等大量次级型号；它们可存在于底部完整报价表，但不进入顶部主流卡片。

### Claude 型号口径

截至本规格核验日，Claude 卡片按官方公开正式主线展示：

- Fable 5
- Opus 4.8
- Sonnet 5
- Haiku 4.5

规则：

- Fable 5、Opus 4.8、Sonnet 5 的上下文字段按官网核验值写入；当前核验结论为 1M；
- Haiku 4.5 当前核验结论为 200K；
- 每款 Claude 正式型号必须提供准确 `api_id`、字段级官方来源 URL、核验时间、上下文及价格；任一缺失都构建失败，不能降级为告警；
- 邀请制、限量开放、未公开 API 或仅有传闻的型号不混入正式主线；本次一律不渲染 `invite_only`；
- 展示名称、API ID、OpenRouter ID、价格和上下文必须分别存储，禁止从展示名称猜 API ID，也禁止用 `api_id` 代替精确 `openrouter_id`。

Claude 官方参考源：

- `https://claude.com/api`
- `https://docs.claude.com/zh-CN/docs/about-claude/models`

价格数据在实施时再次抓取并二次核验；规格不固化未经再次验证的具体金额。

## 5. 配置驱动的数据结构

新增 `config/mainstream_models.yml`，作为主流专区唯一型号目录。建议结构：

```yaml
updated_at: "2026-07-18"
sections:
  domestic:
    title: "国内主流大模型"
    vendors:
      - id: deepseek
        name: "DeepSeek"
        source_id: deepseek
        models:
          - canonical: "DeepSeek V3.2"
            display_name: "DeepSeek V3.2"
            api_id: "deepseek-chat"
            openrouter_id: null
            role: "主力通用"
            availability: official
            modality: text
            context_tokens: 131072
            pricing_kind: paid
            pricing:
              tiers:
                - condition: "default"
                  input_price: 2.0
                  output_price: 3.0
                  cache_input_price: 0.2
            currency: CNY
            unit: per_million_tokens
            source_url: "https://api-docs.deepseek.com/zh-cn/quick_start/pricing"
            verified_at: "2026-07-18T23:00:00+08:00"
  overseas:
    title: "海外主流大模型"
    vendors:
      - id: anthropic
        name: "Anthropic Claude"
        source_id: anthropic
        models: []
```

字段约束：

- `canonical` 必须能与 `config/models.yml` 及报价数据对齐；
- `source_id` 必须指向 `config/sources.yml` 的官方厂商源；
- `api_id` 可为空，但不得推测；Claude 的 `official` 型号例外，必须有准确 API ID；
- `openrouter_id` 与厂商 `api_id` 分开存储，可为空；
- `availability` 仅允许 `official`、`preview`、`invite_only`、`tracking`；
- `modality` 仅允许 `text`、`image`、`video`；本次主流专区只渲染 `text`；
- `context_tokens` 必须为正整数；正式文本型号不得使用 `0` 或 `null` 占位；
- `pricing_kind` 仅允许 `paid` 或 `free`；`paid` 的每个 tier 输入价、输出价不得为 `null`，且至少一个大于零；
- `pricing.tiers[]` 用于表达按输入长度、批量或其他条件分档，不能把多档价格压成单一标量；
- `cache_input_price`、价格生效期 `effective_from/effective_to` 可选，但一旦展示必须有字段级官方证据；
- `currency` 与 `unit` 必须明确，并与 `modality` 联合校验，避免 token、图片、秒数等计价单位混用；
- `source_url` 与带时区的 `verified_at` 必填；
- 正式页面只渲染 `official` 及用户明确批准的 `preview`；本次不渲染 `invite_only` 和 `tracking`。

`config/new_models.yml` 继续负责新品监听；确认正式发布并完成价格核验后，再晋升到 `mainstream_models.yml`。

## 6. 生成器改造

`core/site.py`：

- 移除或废弃 `OVERSEAS_OFFICIAL` 硬编码；
- 新增主流目录加载与 schema 校验；
- 新增统一的 `mainstream_section(section_id, vendors)` 渲染函数；
- 国内与海外调用同一套 HTML 组件；
- 主流目录中所有可渲染 canonical 必须合并进入 `filter_meta.models`，不能只依赖当前 watchlist；
- 卡片点击执行“清空当前模型选择并仅选中该 canonical”，然后复用现有 `state.models` 筛选逻辑；
- 若该 canonical 暂无渠道报价，保留官方卡片并显示“暂无渠道报价”的明确空态，不得静默无响应；
- 页面继续由 `build_site()` 生成，禁止手改 `site/index.html`。

建议增加 `core/mainstream_catalog.py`：

- 读取 YAML；
- 校验必填字段、状态枚举、价格非负和来源 URL；
- 检查 canonical 重复；
- 检查文本 token 模型与视频/图像模型单位是否混用；
- 输出供 `site.py` 使用的标准结构及校验告警。

## 7. 数据质量与防幻觉规则

构建失败条件：

- 正式型号缺少官方来源、字段级证据或核验日期；
- 同一专区 canonical 重复；
- `per_million_tokens` 型号被配置为视频模型，或 `text` 与非 token 单位混用；
- 正式文本型号上下文不是正整数；
- `paid` 型号价格为空或全部为零；
- 正式型号使用 `tracking` 状态；
- Claude 展示名称与配置中的正式主线不一致；
- 国内主流 canonical 未进入 `filter_meta.models`；
- 豆包文本型号被匹配到 Seedance canonical。

构建告警条件：

- 核验日期超过 30 天；
- 正式型号缺少 API ID；
- 新品监听已检测到发布，但尚未进入主流目录；
- 官方价与抓取数据偏差超过设定阈值。

数据可信度按以下顺序：官方定价页或官方 API > 官方文档 > 渠道 API > 第三方聚合页。OpenRouter 只作为渠道价，不替代厂商官方价。

## 8. 视觉与交互

- 国内和海外专区使用相同网格、卡片高度、字段顺序和响应式规则；
- 国内使用低饱和青绿色提示，海外使用低饱和蓝色提示；
- 浅色主题下保持白底、深色正文、细边框和大留白；
- 价格数字对齐，长模型名不挤压价格列；
- 卡片只显示核心字段，完整来源和更新时间可通过展开区或底部说明查看；
- 移动端由三列降为单列；
- 键盘可聚焦、回车可筛选，并提供明确的选中态。

## 9. 测试与验收

自动测试至少覆盖：

1. YAML schema 合法和非法样例；
2. DOM 中 `[data-section="domestic-mainstream"] [data-vendor]` 恰好出现六家厂商；
3. DOM 中 Claude 卡片出现 Fable 5、Opus 4.8、Sonnet 5、Haiku 4.5 四款，前三款 `data-context="1000000"`，Haiku 为 `200000`；
4. `invite_only`、`tracking` 型号不进入正式卡片；
5. 匹配矩阵验证豆包文本模型不会匹配 Seedance，且 Qwen Max/Plus canonical 不再合并；
6. 点击任一 `[data-canonical]` 卡片后，`state.models` 只含该 canonical；无渠道报价时出现 `[data-empty-state="no-channel-price"]`；
7. 国内/海外分页和中国大陆渠道/OpenRouter 渠道分区不被破坏；
8. Excel 导出只包含当前筛选结果；
9. 使用 Playwright 在 375×812 与 1440×900 视口检查 `document.documentElement.scrollWidth === window.innerWidth`；
10. 运行 `python -m unittest discover -s tests -p "test_*.py"` 通过；
11. 运行 `python main.py --dry-run` 后，`data/audit.json` 与 OpenRouter 验证结果的 `ok` 均为 `true`，且 high 风险项为 0。

验收标准：

- 国内六大主流专区与海外专区同级出现；
- Claude 型号、上下文、状态与核验日官方资料一致；
- 页面不再把 Seedance 当豆包文本模型；
- 主流型号更新不需要修改 `core/site.py`；
- 现有筛选、汇率、官方原价、渠道报价和 Excel 导出无回归；
- 部署页面可访问且关键 URL 核验通过。

## 10. 非本次范围

- 不把所有历史模型放入主流卡片；
- 不在浏览器运行时直接请求各厂商官网；
- 不新增视频生成模型比价表；
- 不展示传闻、邀请制或未公开 API 的型号为“正式可用”；
- 不改变 OpenRouter 作为美元渠道报价的定位。
