# 技术文档 — 微信公众号文章采集与理论收敛分析工具

## 1. 系统架构

### 1.1 分层架构

系统采用四层分层架构，各层单向依赖：

```
┌─────────────────────────────────────────────────────────┐
│                    CLI 交互层 (main.py)                    │
│        login / crawl / analyze / report / graph          │
│              status / config                              │
├──────────────┬──────────────┬───────────────────────────┤
│   采集模块    │   分析模块    │      报告与图谱模块        │
│  (crawler/)  │ (analyzer/)  │      (report/)            │
│              │              │                           │
│ BrowserMgr   │ DeepSeekClnt │ ConvergenceReport         │
│ LoginHandler │ ArticleAnlzr │ ConceptGraph              │
│ ListCrawler  │ ConceptProc  │ EvolutionTracker          │
│ ContentCrawl │              │                           │
├──────────────┴──────────────┴───────────────────────────┤
│                   数据层 (database + models)              │
│            ArticleRepository / SQLite                     │
├───────────────────────────────────────────────────────────┤
│                   基础设施层 (utils + config)              │
│      Logger / Progress / HtmlCleaner / Config             │
└─────────────────────────────────────────────────────────┘
```

**设计原则**：
- **单一职责**：每个模块只负责一个功能域
- **依赖单向**：采集/分析/报告模块互不直接依赖，仅通过数据层共享数据
- **Repository 模式**：所有数据库操作通过 `ArticleRepository` 封装，上层不直接执行 SQL

### 1.2 模块依赖关系

```
Config ──→ Database ──→ ArticleRepository
                            ↑
              ┌─────────────┼─────────────┐
              │             │             │
        crawler/      analyzer/      report/
         模块           模块           模块
              │             │             │
              └─────────────┼─────────────┘
                            ↑
                         main.py (CLI)
```

---

## 2. 核心模块详解

### 2.1 采集模块 (src/crawler/)

#### BrowserManager (`browser.py`)

管理 Playwright 浏览器生命周期，提供浏览器启动、Cookie 持久化、页面导航能力。

```python
class BrowserManager:
    def launch(self, headless: bool = False) -> None
    def save_cookies(self, path: str) -> None
    def load_cookies(self, path: str) -> bool
    def navigate(self, url: str) -> Page
    def close(self) -> None
```

**关键技术决策**：
- 使用 Playwright **sync API**（非 async），CLI 线性流程更简单
- 使用**持久化浏览器上下文**（`user_data_dir`），保留登录态和浏览器指纹
- Cookie 导出为 JSON 文件，支持跨会话复用

#### LoginHandler (`login.py`)

处理微信公众号后台扫码登录。

```python
class LoginHandler:
    def login(self, timeout: int = 300) -> bool
    def check_login_status(self) -> bool
    def wait_for_login(self, timeout: int) -> bool
```

**登录流程**：
1. 加载已保存的 Cookie → 尝试直接访问后台
2. Cookie 无效 → 显示二维码页面，等待用户扫码
3. 轮询检测 URL 是否从登录页跳转（登录成功后 URL 会变化）
4. 登录成功 → 保存 Cookie 到 `data/cookies.json`

#### ArticleListCrawler (`article_list.py`)

从微信公众号后台批量获取文章列表。

```python
class ArticleListCrawler:
    def fetch_article_list(self, resume: bool, limit: int) -> list[Article]
    def scroll_to_load_all(self) -> None
    def parse_article_items(self) -> list[Article]
```

**采集策略**：
- 微信公众号后台文章列表通过 AJAX API 返回 JSON
- API 端点：`/cgi-bin/appmsg?sub=list&action=list_ex&token=XXX&f=json&ajax=1`
- 自动提取 `token` 参数，分页请求全部文章
- 每页返回后立即 upsert 到数据库

#### ArticleContentCrawler (`article_content.py`)

逐篇抓取文章正文内容。

```python
class ArticleContentCrawler:
    def fetch_all_content(self, resume: bool, limit: int) -> None
    def fetch_content(self, article: Article) -> Article
    def extract_html(self, page: Page) -> str
    def extract_cover_image(self, page: Page) -> str
```

**抓取流程**：
1. 导航到文章 URL
2. 等待页面渲染完成
3. 提取正文 HTML（`#js_content` 容器）
4. 调用 `HtmlCleaner` 转换为纯文本
5. 提取封面图 URL（`meta[property="og:image"]`）
6. 更新数据库，状态置 `complete`
7. 随机延迟 2-3 秒（防风控）

### 2.2 分析模块 (src/analyzer/)

#### DeepSeekClient (`deepseek_client.py`)

DeepSeek API 客户端封装，兼容 OpenAI SDK 格式。

```python
class DeepSeekClient:
    def __init__(self, api_key: str, model: str, base_url: str)
    def chat(self, messages: list[dict], temperature: float = 0.3) -> str
    def chat_json(self, messages: list[dict], temperature: float = 0.3) -> dict
```

**API 调用策略**：
- 使用 `openai` SDK，`base_url` 设为 `https://api.deepseek.com/v1`
- `chat_json` 方法在请求中设置 `response_format={"type": "json_object"}`
- **重试机制**：指数退避（1s → 2s → 4s），最多 3 次
- **文本截断**：单篇文章正文截断至 8000 字符，防止 token 超限

#### ArticleAnalyzer (`article_analyzer.py`)

单篇文章深度分析。

```python
class ArticleAnalyzer:
    def analyze_all(self, resume: bool, article_id: int) -> None
    def analyze_article(self, article: Article) -> AnalysisResult
    def build_analysis_prompt(self, article: Article) -> list[dict]
    def parse_analysis_response(self, response: str) -> AnalysisResult
```

**分析 Prompt 设计**：

```
System: 你是理论分析专家。分析文章并提取核心概念、关键词，
标注所属理论支柱（从预定义列表选择，可多选），
判断是否与TOMAS-AGI或太极OS项目相关。
预定义理论支柱：[刘原理, 三视界法, 太乙预言机, 全息拓扑动力学]
严格以JSON格式返回。

User: 文章标题：{title}
发布时间：{publish_time}
正文内容：{content_text[:8000]}
```

**期望 JSON 响应**：
```json
{
    "concepts": ["概念1", "概念2", "概念3"],
    "keywords": ["关键词1", "关键词2"],
    "theory_pillars": ["刘原理", "三视界法"],
    "summary": "本文探讨了...",
    "tomas_agi_related": false,
    "taiji_os_related": true
}
```

#### ConceptProcessor (`concepts.py`)

概念统计分析引擎。

```python
class ConceptProcessor:
    def get_concept_frequency(self) -> dict[str, int]
    def build_co_occurrence_matrix(self) -> dict[tuple[str, str], int]
    def get_pillar_distribution(self) -> dict[str, int]
    def get_concept_evolution(self) -> list[dict]
    def get_top_concepts(self, n: int) -> list[tuple[str, int]]
```

**核心算法**：

1. **概念频次统计**：遍历所有 `analysis_results.concepts` 字段，统计每个概念出现次数
2. **共现矩阵**：对每篇文章的概念列表，生成所有两两组合 `(concept_a, concept_b)`，按字典序排列保证唯一性，统计共现次数
3. **理论支柱分布**：统计四大支柱各自标注的文章数量
4. **概念演化**：按 `publish_time` 排序文章，计算每个时间窗口内概念出现频率

### 2.3 报告模块 (src/report/)

#### ConvergenceReportGenerator (`convergence_report.py`)

理论收敛报告生成器。

```python
class ConvergenceReportGenerator:
    def generate_report(self, output_path: str) -> str
    def generate_json_report(self, output_path: str) -> dict
    def build_report_prompt(self, summary_data: dict) -> list[dict]
```

**报告生成流程**：
1. 收集全量分析结果
2. 调用 `ConceptProcessor` 计算概念频次 Top50、理论支柱分布、演化时间线
3. 构建 Prompt，包含统计摘要（非全文），发送给 DeepSeek
4. AI 生成 Markdown 格式报告
5. 同时输出 JSON 结构化数据

**报告 Prompt 包含**：
- 概念频次 Top50
- 理论支柱分布
- 概念演化时间线摘要
- TOMAS-AGI / 太极OS 相关文章清单

#### ConceptGraphBuilder (`concept_graph.py`)

概念关系图谱构建。

```python
class ConceptGraphBuilder:
    def build_graph(self, top_n: int = 50) -> dict
    def generate_mermaid(self, graph_data: dict) -> str
    def export_json(self, graph_data: dict, path: str) -> None
```

**图谱构建算法**：
1. 从 `ConceptProcessor` 获取共现矩阵
2. 按共现次数降序排列，取 Top N 关系
3. 提取涉及的概念作为节点
4. 生成 Mermaid `graph` 格式文本
5. 导出 JSON（nodes + edges + weights）

#### EvolutionTracker (`evolution_tracker.py`)

理论演化脉络追踪。

```python
class EvolutionTracker:
    def track_evolution(self, top_concepts: list[str]) -> dict
    def generate_timeline(self, concepts: list[str]) -> list[dict]
```

**演化追踪逻辑**：
1. 按发布时间排序所有已分析文章
2. 对每个核心概念，记录首次出现时间、高频期、最近出现
3. 生成时间线数据：`[{concept, first_seen, peak_time, frequency_over_time}]`

---

## 3. 数据库设计

### 3.1 ER 图

```
┌──────────────────┐         ┌──────────────────────┐
│    articles      │         │  analysis_results    │
├──────────────────┤         ├──────────────────────┤
│ id (PK)          │◄───FK───│ id (PK)              │
│ title            │         │ article_id (FK)      │
│ url (UNIQUE)     │         │ concepts (JSON)      │
│ publish_time     │         │ keywords (JSON)      │
│ cover_image_url  │         │ theory_pillars (JSON)│
│ content_html     │         │ summary              │
│ content_text     │         │ tomas_agi_related    │
│ crawl_status     │         │ taiji_os_related     │
│ crawl_time       │         │ analysis_status      │
│ crawl_error      │         │ analysis_time        │
│ created_at       │         │ analysis_error       │
│ updated_at       │         │ created_at           │
└──────────────────┘         │ updated_at           │
                             └──────────────────────┘

┌──────────────────────┐
│  concept_relations   │
├──────────────────────┤
│ id (PK)              │
│ concept_a            │
│ concept_b            │
│ co_occurrence_count  │
│ UNIQUE(a, b)         │
│ CHECK(a < b)         │
└──────────────────────┘
```

### 3.2 状态机

**采集状态**：
```
pending → in_progress → complete
                    └──→ failed
```

**分析状态**：
```
pending → in_progress → complete
                    └──→ failed
```

**断点续抓**：`--resume` 模式下跳过 `complete` 状态，仅处理 `pending` 和 `failed`。

### 3.3 JSON 字段约定

| 字段 | 表 | 存储格式 | 示例 |
|------|-----|---------|------|
| `concepts` | analysis_results | JSON array | `["刘原理", "三视界法", "δ-mem"]` |
| `keywords` | analysis_results | JSON array | `["AGI", "非冯诺依曼", "六代机"]` |
| `theory_pillars` | analysis_results | JSON array | `["刘原理", "太乙预言机"]` |

读取时使用 `json.loads()` 反序列化。

---

## 4. 关键技术决策

### 4.1 为什么选 Playwright 而非 Selenium？

| 维度 | Playwright | Selenium |
|------|-----------|----------|
| 反检测 | 原生反检测，指纹更接近真实浏览器 | 易被识别 |
| SPA 支持 | 内置自动等待，SPA 渲染好 | 需手动 WebDriverWait |
| Cookie 持久化 | 持久化上下文，开箱即用 | 需手动管理 |
| 安装 | `pip install playwright` + `playwright install` | 需管理 WebDriver 版本 |
| API 风格 | sync/async 双模式 | 同步为主 |

### 4.2 为什么用 DeepSeek 而非 GPT-4？

| 维度 | DeepSeek | GPT-4 |
|------|---------|-------|
| 中文理解 | 强，原生中文训练 | 强 |
| 成本 | ~¥0.001/千token | ~¥0.15/千token |
| 2000篇成本 | ~¥20-50 | ~¥500-1500 |
| API 兼容 | OpenAI 格式 | 原生 |
| JSON 输出 | 支持 `response_format` | 支持 |

### 4.3 文本截断策略

单篇文章正文截断至 **8000 字符**（约 4000-5000 中文字），原因：
- DeepSeek API 上下文窗口 64K tokens，但输入越长成本越高
- 8000 字符足以覆盖大部分文章的核心内容
- 截断保留文章开头（通常包含摘要和核心论点）

### 4.4 概念共现矩阵算法

```
对于每篇文章 A，其概念列表为 [c1, c2, c3, ...]：
  生成所有两两组合: (c1,c2), (c1,c3), (c2,c3), ...
  对每个组合 (a, b)：
    确保 a < b（字典序，保证唯一性）
    matrix[(a, b)] += 1
```

共现次数越高，说明两个概念关联越紧密。

---

## 5. 错误处理策略

### 5.1 采集错误

| 错误类型 | 处理方式 |
|---------|---------|
| 页面加载超时 | 记录 `crawl_error`，状态置 `failed`，继续下一篇 |
| 正文选择器未找到 | 记录错误，状态置 `failed` |
| 网络中断 | 捕获异常，状态置 `failed`，可通过 `--resume` 重试 |

### 5.2 分析错误

| 错误类型 | 处理方式 |
|---------|---------|
| API 调用失败 | 指数退避重试 3 次，仍失败则记录 `analysis_error` |
| JSON 解析失败 | 尝试从响应文本中提取 JSON，失败则记录错误 |
| API 额度不足 | 记录错误，建议用户检查额度 |

### 5.3 全局异常

CLI 层捕获所有未处理异常，打印友好错误信息，记录日志，非零退出码。

---

## 6. 性能考量

### 6.1 预估耗时

| 阶段 | 文章数 | 单篇耗时 | 总耗时 |
|------|--------|---------|--------|
| 采集 | 2000 | ~3s（含延迟） | ~100 分钟 |
| 分析 | 2000 | ~5s（API 调用） | ~170 分钟 |
| 报告 | 1 | ~30s | 30 秒 |
| 图谱 | 1 | ~5s | 5 秒 |

### 6.2 API 调用成本

- 单篇分析：输入 ~4000 tokens，输出 ~500 tokens
- 2000 篇：约 800 万输入 + 100 万输出 tokens
- DeepSeek 定价：输入 ¥0.001/千token，输出 ¥0.002/千token
- **预估总成本：约 ¥10-20**

### 6.3 存储

- SQLite 数据库：2000 篇文章 × ~10KB/篇 ≈ 20MB
- 日志：每天 ~1MB，保留 7 天
- 总磁盘占用：~50MB

---

## 7. 扩展性

### 7.1 增量采集

通过 `articles.url` 的 UNIQUE 约束，重复采集时自动跳过已存在文章。`--resume` 模式仅处理 `pending`/`failed` 状态。

### 7.2 自定义理论支柱

修改 `config.json` 的 `theory_pillars` 字段即可自定义分析标签：

```json
{
    "theory_pillars": ["你的理论1", "你的理论2", "你的理论3"]
}
```

### 7.3 自定义项目标注

修改 `tomas_agi_keywords` 和 `taiji_os_keywords` 可自定义项目关联关键词。

### 7.4 更换 AI 模型

修改 `config.json`：
```json
{
    "deepseek_model": "deepseek-reasoner",
    "deepseek_base_url": "https://api.deepseek.com/v1"
}
```

或切换到其他 OpenAI 兼容 API：
```json
{
    "deepseek_base_url": "https://api.openai.com/v1",
    "deepseek_model": "gpt-4o"
}
```
