# 国内与海外主流模型双专区实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为价格比价站增加配置驱动的国内/海外主流模型双专区，修正 Claude 正式主线，并彻底消除豆包文本模型误映射 Seedance 视频模型的问题。

**Architecture:** 新建 `core/mainstream_catalog.py` 作为 YAML 目录的唯一读取、校验和标准化边界；`core/site.py` 只消费标准目录并复用同一套国内/海外卡片渲染器。`config/models.yml` 继续负责抓取记录的 canonical 匹配，但改为安全别名和明确的文本模型 canonical；主流卡片 canonical 与 watchlist 合并进入前端筛选状态。

**Tech Stack:** Python 3.13、PyYAML、pytest、原生 HTML/CSS/JavaScript、Playwright、Chart.js、SheetJS。

## Global Constraints

- `site/index.html` 必须由 `core/site.py::build_site()` 生成，禁止直接编辑生成文件。
- 页面汇率交互默认值保持 `7.0`。
- 国内主流厂商固定为 DeepSeek、通义千问、智谱 GLM、Kimi、MiniMax、豆包。
- 海外主流厂商固定为 OpenAI、Anthropic Claude、Google Gemini；GPT-4o 必须保留。
- Claude 正式主线固定为 Fable 5、Opus 4.8、Sonnet 5、Haiku 4.5；本次不渲染邀请制 Mythos。
- OpenRouter 只属于渠道报价，不得替代厂商官方价格或官方 API ID。
- 正式卡片缺少官方字段级证据时必须构建失败或降为监听状态，禁止从第三方渠道补猜。
- 豆包文本模型与 Seedance 视频模型不得共享 canonical 或通过包含匹配互相命中。
- 不新增前端框架或运行时依赖。

## File map

- Create: `config/mainstream_models.yml` — 国内/海外主流型号目录与官方字段证据。
- Create: `core/mainstream_catalog.py` — 目录读取、schema 校验、标准化与可渲染筛选。
- Create: `tests/test_mainstream_catalog.py` — 目录合法性和错误样例单元测试。
- Create: `tests/test_site_mainstream.py` — 双专区 HTML、筛选元数据、空态和 Excel 数据测试。
- Create: `tests/test_mainstream_ui.py` — Playwright 卡片联动和双视口溢出测试。
- Modify: `config/models.yml` — 拆分 Qwen、豆包、Kimi、MiniMax canonical，删除 Seedance 错误别名。
- Modify: `core/matcher.py` — 为 alias 增加匹配模式，移除危险的无条件双向包含匹配。
- Modify: `tests/test_parsers.py` — 更新目标数量断言并增加正反匹配矩阵。
- Modify: `core/site.py` — 移除 `OVERSEAS_OFFICIAL` 硬编码；加载目录、构建双专区、合并筛选模型、绑定卡片交互。
- Modify: `main.py` — 在站点生成前校验主流目录并输出校验摘要。
- Modify: `README.md` — 更新配置、布局、运行和数据口径说明。
- Modify: `docs/architecture.md`、`docs/runbook.md` — 记录新数据流与更新流程。

---

### Task 1: 修复 canonical 与安全匹配边界

**Files:**
- Modify: `config/models.yml`
- Modify: `core/matcher.py:15-49`
- Modify: `tests/test_parsers.py:121-126,208-210`

**Interfaces:**
- Consumes: `models_cfg: dict`，每个模型包含 `canonical` 与 `aliases`；alias 可以是字符串或 `{name, match}` 对象。
- Produces: `matcher.match(model_raw: Optional[str], models_cfg: Dict[str, Any]) -> Optional[str]`，只允许 `exact` 或显式 `prefix`，不再执行双向包含匹配。

- [ ] **Step 1: 写出会失败的匹配测试**

在 `tests/test_parsers.py` 追加：

```python
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("qwen3.7-max", "Qwen3.7 Max"),
        ("Qwen3.7-Plus", "Qwen3.7 Plus"),
        ("doubao-seed-2.1-pro", "Doubao Seed 2.1 Pro"),
        ("doubao-seed-2.1-turbo", "Doubao Seed 2.1 Turbo"),
        ("kimi-k2.7-code", "Kimi K2.7 Code"),
        ("MiniMax-M3", "MiniMax M3"),
        ("seedance-2.0", "Seedance 2.0"),
    ],
)
def test_matcher_safe_positive_matrix(raw, expected):
    assert matcher.match(raw, MODELS_CFG) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "doubao-seed-2.0-pro",
        "doubao-seed-2.0-code",
        "doubao-seed-2.1-turbo",
    ],
)
def test_doubao_text_never_matches_seedance(raw):
    assert matcher.match(raw, MODELS_CFG) != "Seedance 2.0"


def test_qwen_max_plus_are_distinct():
    assert matcher.match("qwen3.7-max", MODELS_CFG) != matcher.match("qwen3.7-plus", MODELS_CFG)
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
"/c/Users/昊哥/.workbuddy/binaries/python/versions/3.13.12/python.exe" -m pytest "D:/Projects/WorkBuddy/token 定价/tests/test_parsers.py" -k "safe_positive or doubao_text or qwen_max" -v
```

Expected: 豆包仍命中 `Seedance 2.0`，Qwen Max/Plus 仍同为 `qwen3.7`。

- [ ] **Step 3: 改写 `config/models.yml` 的相关条目**

用以下 canonical 取代旧 Qwen/Seedance/Kimi/MiniMax 条目：

```yaml
  - canonical: Qwen3.7 Max
    aliases: [qwen3.7-max, Qwen3.7-Max]
  - canonical: Qwen3.7 Plus
    aliases: [qwen3.7-plus, Qwen3.7-Plus]
  - canonical: Kimi K2.7 Code
    aliases: [kimi-k2.7-code, Kimi K2.7 Code]
  - canonical: MiniMax M3
    aliases: [MiniMax-M3, minimax-m3, MiniMax M3]
  - canonical: Doubao Seed 2.1 Pro
    aliases: [doubao-seed-2.1-pro, Doubao-Seed-2.1-Pro]
  - canonical: Doubao Seed 2.1 Turbo
    aliases: [doubao-seed-2.1-turbo, Doubao-Seed-2.1-Turbo]
  - canonical: Seedance 2.0
    aliases: [Seedance 2.0, Seedance-2.0]
```

必须删除 `Seedance 2.0` 下的 `Doubao-Seedance` 与 `Doubao-Seed-2.0`。

- [ ] **Step 4: 将 matcher 改为安全规则**

将 `_alias_norms` 和 `match` 改为：

```python
def _alias_specs(model: Dict[str, Any]) -> List[Tuple[str, str]]:
    aliases = [model["canonical"]] + list(model.get("aliases", []))
    specs: List[Tuple[str, str]] = []
    for alias in aliases:
        if isinstance(alias, dict):
            name = alias.get("name")
            mode = alias.get("match", "exact")
        else:
            name = alias
            mode = "exact"
        norm = normalize(name)
        if norm and mode in {"exact", "prefix"}:
            specs.append((norm, mode))
    return specs


def match(model_raw: Optional[str], models_cfg: Dict[str, Any]) -> Optional[str]:
    raw_n = normalize(model_raw)
    if not raw_n:
        return None
    for model in models_cfg.get("models", []):
        for alias_n, mode in _alias_specs(model):
            if mode == "exact" and raw_n == alias_n:
                return model["canonical"]
            if mode == "prefix" and raw_n.startswith(alias_n):
                return model["canonical"]
    return None
```

- [ ] **Step 5: 运行匹配与 parser 回归测试**

Run:

```bash
"/c/Users/昊哥/.workbuddy/binaries/python/versions/3.13.12/python.exe" -m pytest "D:/Projects/WorkBuddy/token 定价/tests/test_parsers.py" -v
```

Expected: 全部 PASS；若原 `test_watchlist_all_nine_matched` 名称过时，改名为 `test_watchlist_all_configured_targets_matched`，但保留 `targets <= canons` 断言。

- [ ] **Step 6: 提交**

```bash
git add config/models.yml core/matcher.py tests/test_parsers.py
git commit -m "fix: separate text model canonical mappings"
```

---

### Task 2: 建立主流模型目录校验层

**Files:**
- Create: `core/mainstream_catalog.py`
- Create: `tests/test_mainstream_catalog.py`

**Interfaces:**
- Produces: `load_catalog(path: str) -> Dict[str, Any]`
- Produces: `validate_catalog(catalog: Dict[str, Any]) -> List[Dict[str, str]]`
- Produces: `renderable_sections(catalog: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]`
- Produces: `catalog_canons(catalog: Dict[str, Any], section: Optional[str] = None) -> List[str]`

- [ ] **Step 1: 写 schema 失败测试**

新建 `tests/test_mainstream_catalog.py`，至少覆盖：合法目录、重复 canonical、付费价为空、文本模型使用视频单位、正式 Claude 缺 API ID、tracking 不可渲染。

```python
from core.mainstream_catalog import catalog_canons, renderable_sections, validate_catalog


def _valid_catalog():
    return {
        "updated_at": "2026-07-18",
        "sections": {
            "overseas": {
                "title": "海外主流大模型",
                "vendors": [{
                    "id": "anthropic",
                    "name": "Anthropic Claude",
                    "source_id": "anthropic",
                    "models": [{
                        "canonical": "Claude Fable 5",
                        "display_name": "Fable 5",
                        "api_id": "claude-fable-5",
                        "openrouter_id": None,
                        "role": "旗舰代理",
                        "availability": "official",
                        "modality": "text",
                        "context_tokens": 1_000_000,
                        "pricing_kind": "paid",
                        "pricing": {"tiers": [{"condition": "default", "input_price": 10.0, "output_price": 50.0}]},
                        "currency": "USD",
                        "unit": "per_million_tokens",
                        "source_url": "https://platform.claude.com/docs/zh-TW/about-claude/models/overview",
                        "verified_at": "2026-07-18T23:00:00+08:00",
                    }],
                }],
            }
        },
    }


def test_valid_catalog_has_no_errors():
    assert validate_catalog(_valid_catalog()) == []


def test_tracking_model_not_rendered():
    data = _valid_catalog()
    data["sections"]["overseas"]["vendors"][0]["models"][0]["availability"] = "tracking"
    assert renderable_sections(data)["overseas"][0]["models"] == []


def test_paid_model_requires_positive_price():
    data = _valid_catalog()
    tier = data["sections"]["overseas"]["vendors"][0]["models"][0]["pricing"]["tiers"][0]
    tier["input_price"] = 0
    tier["output_price"] = 0
    assert any(e["code"] == "paid_price_required" for e in validate_catalog(data))
```

- [ ] **Step 2: 运行测试确认模块不存在**

```bash
"/c/Users/昊哥/.workbuddy/binaries/python/versions/3.13.12/python.exe" -m pytest "D:/Projects/WorkBuddy/token 定价/tests/test_mainstream_catalog.py" -v
```

Expected: FAIL with `ModuleNotFoundError`。

- [ ] **Step 3: 实现目录模块**

`core/mainstream_catalog.py` 的规则：

```python
RENDERABLE = {"official", "preview"}
AVAILABILITY = RENDERABLE | {"invite_only", "tracking"}
MODALITIES = {"text", "image", "video"}
TEXT_UNIT = "per_million_tokens"


def load_catalog(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    errors = validate_catalog(data)
    if errors:
        detail = "; ".join(f"{item['code']}: {item['message']}" for item in errors)
        raise ValueError(f"mainstream catalog invalid: {detail}")
    return data
```

`validate_catalog` 必须返回稳定的 `{code, path, message}` 列表；检查规格中的全部构建失败条件。`renderable_sections` 保留 vendor 结构但过滤非 `official/preview` 型号。`catalog_canons` 去重并保持配置顺序。

- [ ] **Step 4: 运行目录单测**

```bash
"/c/Users/昊哥/.workbuddy/binaries/python/versions/3.13.12/python.exe" -m pytest "D:/Projects/WorkBuddy/token 定价/tests/test_mainstream_catalog.py" -v
```

Expected: 全部 PASS。

- [ ] **Step 5: 提交**

```bash
git add core/mainstream_catalog.py tests/test_mainstream_catalog.py
git commit -m "feat: validate mainstream model catalog"
```

---

### Task 3: 写入经过官方证据约束的 YAML 目录

**Files:**
- Create: `config/mainstream_models.yml`
- Modify: `tests/test_mainstream_catalog.py`

**Interfaces:**
- Consumes: Task 2 的 `load_catalog` 与 schema。
- Produces: `config/mainstream_models.yml`，供 `site.py` 和 `main.py` 使用。

- [ ] **Step 1: 添加真实配置加载测试**

```python
from pathlib import Path
from core.mainstream_catalog import catalog_canons, load_catalog

ROOT = Path(__file__).resolve().parents[1]


def test_project_catalog_is_valid_and_has_required_vendors():
    catalog = load_catalog(str(ROOT / "config" / "mainstream_models.yml"))
    domestic = catalog["sections"]["domestic"]["vendors"]
    overseas = catalog["sections"]["overseas"]["vendors"]
    assert [v["id"] for v in domestic] == ["deepseek", "qwen", "glm", "kimi", "minimax", "doubao"]
    assert [v["id"] for v in overseas] == ["openai", "anthropic", "google"]
    assert {
        "Claude Fable 5", "Claude Opus 4.8", "Claude Sonnet 5", "Claude Haiku 4.5"
    } <= set(catalog_canons(catalog, "overseas"))
```

- [ ] **Step 2: 运行测试确认配置不存在**

Expected: FAIL with `FileNotFoundError`。

- [ ] **Step 3: 创建目录并只写有官方证据的字段**

必须准确写入 Claude 四款：

| canonical | api_id | input/output USD/MTok | context | cache write/read |
|---|---|---:|---:|---:|
| Claude Fable 5 | `claude-fable-5` | 10 / 50 | 1,000,000 | 12.5 / 1.0 |
| Claude Opus 4.8 | `claude-opus-4-8` | 5 / 25 | 1,000,000 | 6.25 / 0.5 |
| Claude Sonnet 5 | `claude-sonnet-5` | 2 / 10 至 2026-08-31；3 / 15 自 2026-09-01 | 1,000,000 | 2.5 / 0.2（介绍价） |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | 1 / 5 | 200,000 | 1.25 / 0.1 |

来源必须分别写：

```yaml
source_url: https://platform.claude.com/docs/zh-TW/about-claude/models/overview
pricing_source_url: https://claude.com/api
```

国内目录执行以下证据门槛：

- DeepSeek V3.2：可以写 `deepseek-chat` 和 `deepseek-reasoner`，官网价 2/3、缓存命中 0.2、128K；
- MiniMax M3：按官方页写两档，≤512K 为 2.1/8.4/缓存0.42，512K–1M 为 4.2/16.8/缓存0.84；M2.7 为 2.1/8.4；
- 豆包 2.1 Pro 为 6/30/缓存1.2、Turbo 为 3/15/缓存0.6，上下文条件 [0,256K]；
- Kimi K2.7 Code：官方页确认 256K，但价格字段若抓取结果未明确给出，则先设 `availability: tracking`，不得把腾讯云或胜算云价格当官方价；
- Qwen3.7 Max/Plus：当前主 URL 404；在修复 `sources.yml` 的官方价格 URL前设 `availability: tracking`；
- GLM-5.2/5.1：若官方 `open.bigmodel.cn/pricing` 当前正文无法证明型号和字段，则设 `availability: tracking`，不能用渠道数据补齐。

OpenAI 与 Gemini 沿用现有已核验主力，但必须迁移进 YAML；若实施日官方页面不支持既有字段，先设 `tracking` 并保留 GPT-4o 卡片的展示要求，直到完成官方核验。

- [ ] **Step 4: 运行目录测试**

```bash
"/c/Users/昊哥/.workbuddy/binaries/python/versions/3.13.12/python.exe" -m pytest "D:/Projects/WorkBuddy/token 定价/tests/test_mainstream_catalog.py" -v
```

Expected: 全部 PASS；六家国内 vendor 必须存在，但证据不足型号可暂不进入 `renderable_sections`。

- [ ] **Step 5: 提交**

```bash
git add config/mainstream_models.yml tests/test_mainstream_catalog.py
git commit -m "data: add verified mainstream model catalog"
```

---

### Task 4: 将站点数据层迁移到目录驱动

**Files:**
- Modify: `core/site.py:81-107,297-334,334-480`
- Create: `tests/test_site_mainstream.py`

**Interfaces:**
- Consumes: `mainstream_catalog.load_catalog()`、`renderable_sections()`、`catalog_canons()`。
- Produces: `_build_site_data(data_dir)` 新增 `mainstream_sections`、`has_domestic_mainstream`、`has_overseas_mainstream`。

- [ ] **Step 1: 写数据层失败测试**

```python
from pathlib import Path
from core import site

ROOT = Path(__file__).resolve().parents[1]


def test_site_data_merges_catalog_canons_into_filters():
    data = site._build_site_data(str(ROOT / "data"))
    catalog_canons = {
        m["canonical"]
        for vendors in data["mainstream_sections"].values()
        for vendor in vendors
        for m in vendor["models"]
    }
    assert catalog_canons <= set(data["filter_meta"]["models"])


def test_site_data_has_six_domestic_vendor_slots():
    data = site._build_site_data(str(ROOT / "data"))
    assert [v["id"] for v in data["mainstream_sections"]["domestic"]] == [
        "deepseek", "qwen", "glm", "kimi", "minimax", "doubao"
    ]
```

- [ ] **Step 2: 运行测试确认失败**

Expected: FAIL，缺少 `mainstream_sections`。

- [ ] **Step 3: 移除硬编码并加载目录**

删除 `OVERSEAS_OFFICIAL` 和 `_overseas_official_rows()`；新增：

```python
from core import mainstream_catalog

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(ROOT_DIR, "config", "mainstream_models.yml")
```

在 `_build_site_data` 中：

```python
catalog = mainstream_catalog.load_catalog(CATALOG_PATH)
mainstream_sections = mainstream_catalog.renderable_sections(catalog)
catalog_all = mainstream_catalog.catalog_canons(catalog)
domestic_catalog = mainstream_catalog.catalog_canons(catalog, "domestic")
overseas_catalog = mainstream_catalog.catalog_canons(catalog, "overseas")
all_canons = _sort_canons(list(dict.fromkeys(canons + catalog_all)))
```

`domestic_models` 与 `overseas_models` 必须分别合并目录 canonical；channel options 不再强塞 `openai/anthropic/google`，而是从可渲染 vendor 的 `source_id` 合并。

- [ ] **Step 4: 为卡片构造统一价格视图**

为每个 model 增加 `display_tier = pricing.tiers[0]`、`context_label`、`source_label`、`has_channel_price`。`has_channel_price` 依据 watchlist 中同 canonical 是否存在非官方行计算，不改变官方目录价格。

- [ ] **Step 5: 运行数据层测试与 parser 回归**

```bash
"/c/Users/昊哥/.workbuddy/binaries/python/versions/3.13.12/python.exe" -m pytest "D:/Projects/WorkBuddy/token 定价/tests/test_site_mainstream.py" "D:/Projects/WorkBuddy/token 定价/tests/test_parsers.py" -v
```

Expected: 全部 PASS。

- [ ] **Step 6: 提交**

```bash
git add core/site.py tests/test_site_mainstream.py
git commit -m "refactor: drive mainstream site data from catalog"
```

---

### Task 5: 渲染国内/海外统一卡片专区

**Files:**
- Modify: `core/site.py:675-775, CSS 常量, build_site()`
- Modify: `tests/test_site_mainstream.py`

**Interfaces:**
- Produces: `_mainstream_section(section_id: str, title: str, vendors: List[Dict[str, Any]]) -> str`
- 每个可点击型号必须输出 `data-canonical`、`data-context`、`data-source`。

- [ ] **Step 1: 写 HTML 结构失败测试**

```python
def test_generated_html_has_symmetric_mainstream_sections(tmp_path):
    out = tmp_path / "index.html"
    site.build_site(str(ROOT / "data"), str(out))
    html = out.read_text(encoding="utf-8")
    assert 'data-section="domestic-mainstream"' in html
    assert 'data-section="overseas-mainstream"' in html
    assert html.count('data-vendor="') >= 9
    for name in ["Fable 5", "Opus 4.8", "Sonnet 5", "Haiku 4.5"]:
        assert name in html
    assert 'data-empty-state="no-channel-price"' in html
```

- [ ] **Step 2: 运行测试确认失败**

Expected: FAIL，尚无国内主流 section。

- [ ] **Step 3: 实现统一 renderer**

`_mainstream_section` 必须：

- 保留六家国内 vendor 卡位；无正式型号的 vendor 显示“官方资料待核验”，不伪造价格；
- 海外 Claude 四款完整显示；
- 第一档价格、上下文、状态、核验日期使用相同字段顺序；
- 多档价格显示“分档计费”并列出 tier 条件；
- `article.model-pick` 使用 `tabindex="0"`、`role="button"`；
- 无渠道报价时输出 `<span data-empty-state="no-channel-price">暂无渠道报价</span>`；
- 国内采用低饱和青绿色提示，海外采用低饱和蓝色提示，正文仍为白底深色字。

- [ ] **Step 4: 替换页面装配顺序**

`build_site()` 中顺序固定为：筛选栏 → 国内主流 → 海外主流 → 官方原价 → 新品雷达 → 渠道报价 → 图表。

删除旧 `_overseas_section` 调用和不再使用的 `.hot-*` CSS；保留 GPT-4o 的 `hot` 标签能力，由 YAML 字段 `featured: true` 驱动。

- [ ] **Step 5: 运行 HTML 测试**

```bash
"/c/Users/昊哥/.workbuddy/binaries/python/versions/3.13.12/python.exe" -m pytest "D:/Projects/WorkBuddy/token 定价/tests/test_site_mainstream.py" -v
```

Expected: 全部 PASS。

- [ ] **Step 6: 提交**

```bash
git add core/site.py tests/test_site_mainstream.py
git commit -m "feat: render domestic and overseas mainstream sections"
```

---

### Task 6: 接通卡片筛选、键盘操作与无报价空态

**Files:**
- Modify: `core/site.py` 的 `_JS`
- Create: `tests/test_mainstream_ui.py`

**Interfaces:**
- 点击或回车 `.model-pick[data-canonical]` 后：清空 `state.models` → 只打开目标 canonical → `renderChips()` → `bindChips()` → `applyFilter()`。

- [ ] **Step 1: 写 Playwright 失败测试**

```python
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright
from core import site

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def page(tmp_path):
    out = tmp_path / "index.html"
    site.build_site(str(ROOT / "data"), str(out))
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(out.as_uri())
        yield page
        browser.close()


def test_model_card_selects_only_one_model(page):
    card = page.locator('.model-pick[data-canonical="Claude Fable 5"]')
    card.click()
    selected = page.locator('#modelChips .chip.is-on')
    assert selected.count() == 1
    assert selected.first.inner_text() == "Claude Fable 5"


@pytest.mark.parametrize("width,height", [(375, 812), (1440, 900)])
def test_no_horizontal_overflow(tmp_path, width, height):
    out = tmp_path / "index.html"
    site.build_site(str(ROOT / "data"), str(out))
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(out.as_uri())
        assert page.evaluate("document.documentElement.scrollWidth === window.innerWidth")
        browser.close()
```

- [ ] **Step 2: 运行 UI 测试确认失败**

```bash
"/c/Users/昊哥/.workbuddy/binaries/python/versions/3.13.12/python.exe" -m pytest "D:/Projects/WorkBuddy/token 定价/tests/test_mainstream_ui.py" -v
```

Expected: 卡片点击测试失败。

- [ ] **Step 3: 实现统一选择函数**

在 `_JS` 中添加：

```javascript
function selectOnlyModel(canonical){
  Object.keys(state.models).forEach(function(key){ state.models[key] = key === canonical; });
  renderChips();
  bindChips();
  applyFilter();
  var filterBar = document.getElementById('filterBar');
  if (filterBar) filterBar.scrollIntoView({behavior:'smooth', block:'start'});
}
```

绑定 `.model-pick[data-canonical]` 的 click 与 Enter/Space 键。重复绑定前使用 `data-bound="1"` 防止 `renderChips()` 后事件重复。

- [ ] **Step 4: 修正无报价状态**

如果选中的主流 canonical 在表格中完全无行，顶部卡片保留自身的 `data-empty-state`；过滤摘要显示“暂无渠道报价”，而不是把它误计为筛选错误。

- [ ] **Step 5: 运行 UI 和 HTML 测试**

```bash
"/c/Users/昊哥/.workbuddy/binaries/python/versions/3.13.12/python.exe" -m pytest "D:/Projects/WorkBuddy/token 定价/tests/test_mainstream_ui.py" "D:/Projects/WorkBuddy/token 定价/tests/test_site_mainstream.py" -v
```

Expected: 全部 PASS。

- [ ] **Step 6: 提交**

```bash
git add core/site.py tests/test_mainstream_ui.py
git commit -m "feat: link mainstream cards to price filters"
```

---

### Task 7: 将目录校验接入抓取主流程并保持导出一致

**Files:**
- Modify: `main.py:78-82,136-150`
- Modify: `core/site.py` 的 Excel 导出逻辑
- Modify: `tests/test_site_mainstream.py`

**Interfaces:**
- `main.py` 构建站点前调用 `load_catalog()`；非法目录返回非零退出码。
- Excel 新增或更新“国内主流”“海外主流”sheet，数据来自同一 YAML 目录，不再引用旧 `OVERSEAS_OFFICIAL`。

- [ ] **Step 1: 写 Excel 数据源测试**

对 `SITE_DATA` 的导出数据断言：国内/海外主流 sheet 使用 `mainstream_sections`，Claude 四款均在海外 sheet，`Seedance 2.0` 不在国内文本主流 sheet。

- [ ] **Step 2: 运行测试确认失败**

Expected: 旧导出仍读取 `overseas_rows`。

- [ ] **Step 3: 在主流程加载并报告目录**

```python
from core import mainstream_catalog

catalog_path = os.path.join(CONFIG_DIR, "mainstream_models.yml")
catalog = mainstream_catalog.load_catalog(catalog_path)
print(
    "  主流目录:",
    len(mainstream_catalog.catalog_canons(catalog, "domestic")),
    "国内 /",
    len(mainstream_catalog.catalog_canons(catalog, "overseas")),
    "海外",
)
```

必须在抓取前或站点生成前执行，不能吞掉 `ValueError`。

- [ ] **Step 4: 改造 Excel 数据拼装**

从 `SITE_DATA.mainstream_sections` 扁平化输出字段：区域、厂商、型号、API ID、定位、状态、上下文、输入价、输出价、缓存读取价、币种、来源、核验时间。渠道 sheet 继续只导出当前筛选后可见表格行。

- [ ] **Step 5: 运行全量离线测试**

```bash
"/c/Users/昊哥/.workbuddy/binaries/python/versions/3.13.12/python.exe" -m pytest "D:/Projects/WorkBuddy/token 定价/tests" -v
```

Expected: 全部 PASS。

- [ ] **Step 6: 提交**

```bash
git add main.py core/site.py tests/test_site_mainstream.py
git commit -m "feat: validate and export mainstream catalog"
```

---

### Task 8: 运行全链路抓取、核对并修复回归

**Files:**
- Generated: `data/prices.json`, `data/watchlist.json`, `data/audit.json`, `data/openrouter_verify.md`, `site/index.html`
- Modify as needed: official source URLs/parsers only when official fetch failures prove necessary.

**Interfaces:**
- Produces: 可部署的 `site/index.html` 与通过核验的数据产物。

- [ ] **Step 1: 运行离线测试基线**

```bash
"/c/Users/昊哥/.workbuddy/binaries/python/versions/3.13.12/python.exe" -m pytest "D:/Projects/WorkBuddy/token 定价/tests" -v
```

Expected: 全部 PASS。

- [ ] **Step 2: 运行真实抓取和构建**

```bash
"/c/Users/昊哥/.workbuddy/binaries/python/versions/3.13.12/python.exe" "D:/Projects/WorkBuddy/token 定价/main.py" --dry-run
```

Expected: 程序退出码 0，生成 `site/index.html`；单源失败必须明确输出，不允许静默。

- [ ] **Step 3: 核查审计 JSON**

用 Python 读取：

```python
import json
from pathlib import Path
root = Path(r"D:/Projects/WorkBuddy/token 定价")
audit = json.loads((root / "data/audit.json").read_text(encoding="utf-8"))
assert audit["ok"] is True
assert audit["stats"]["high"] == 0
```

同时检查 OpenRouter verify 的 `ok == true`、`high == 0`。若失败，修根因后重新运行，不得只改报告。

- [ ] **Step 4: 核查 canonical 产物**

断言所有 `doubao-seed-*` 记录的 canonical 都不是 `Seedance 2.0`；Qwen Max/Plus 分开；`filter_meta.models` 包含所有可渲染主流 canonical。

- [ ] **Step 5: 运行最终 UI 测试**

```bash
"/c/Users/昊哥/.workbuddy/binaries/python/versions/3.13.12/python.exe" -m pytest "D:/Projects/WorkBuddy/token 定价/tests/test_mainstream_ui.py" -v
```

Expected: 375×812 与 1440×900 均无横向溢出，卡片筛选通过。

- [ ] **Step 6: 提交生成结果**

```bash
git add data site/index.html
git commit -m "build: refresh verified pricing site"
```

---

### Task 9: 更新文档并部署 CloudStudio

**Files:**
- Modify: `README.md:23-49,86-95`
- Modify: `docs/architecture.md`
- Modify: `docs/runbook.md`
- Deploy: `site/`

**Interfaces:**
- Produces: 文档与线上页面，部署 URL 沿用 CloudStudio 工作区返回地址。

- [ ] **Step 1: 更新 README**

目录结构加入 `config/mainstream_models.yml` 和 `core/mainstream_catalog.py`；网页布局改为“国内主流 → 海外主流 → 官方价 → 渠道价”；说明渠道先行型号不等于官方正式型号。

- [ ] **Step 2: 更新架构与运维文档**

`docs/architecture.md` 增加数据流：官方源/主流目录/渠道记录 → canonical → 页面。`docs/runbook.md` 增加新品晋升流程：tracking → 官方核验 → YAML → 测试 → 构建 → 部署。

- [ ] **Step 3: 做文档一致性搜索**

Run:

```bash
rg -n "OVERSEAS_OFFICIAL|Seedance 2\.0|qwen3\.7|Claude.*200K|海外主流" "D:/Projects/WorkBuddy/token 定价" -g "*.py" -g "*.yml" -g "*.md"
```

Expected: 无旧硬编码；`Seedance 2.0` 仅作为视频模型存在；Claude 200K 只对应 Haiku 4.5。

- [ ] **Step 4: 提交文档**

```bash
git add README.md docs/architecture.md docs/runbook.md
git commit -m "docs: document mainstream catalog workflow"
```

- [ ] **Step 5: 部署 `site/`**

使用 CloudStudio 静态站部署，入口 `index.html`，端口 3000。部署完成后打开返回 URL。

- [ ] **Step 6: 线上验收**

确认 HTTP 200；页面出现国内六家卡位、海外三家、Claude 四款、GPT-4o；点击卡片能联动；Excel 可下载；控制台无错误。

- [ ] **Step 7: 记录部署结果**

把最终 URL、测试摘要、官方资料未齐而保持 tracking 的型号写入项目当日日志；不要把临时错误或敏感信息写入记忆。

---

## Self-review result

- Spec coverage: 双专区、Claude 四款、YAML 配置、筛选联动、无报价空态、豆包/Seedance 拆分、OpenRouter 定位、Excel、响应式、审计和部署均有对应任务。
- Completeness scan: 所有步骤均给出具体文件、代码、命令和预期结果；证据不足的型号有明确 `tracking` 降级规则，不要求实现者猜价格。
- Type consistency: 所有任务统一使用 `load_catalog`、`validate_catalog`、`renderable_sections`、`catalog_canons`；前端统一使用 `data-canonical` 与 `state.models`。
- Scope: 保持单一可测试子系统“主流目录 + 双专区”，不新增视频比价表，不改用前端框架。
