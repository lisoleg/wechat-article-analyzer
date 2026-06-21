# 使用指南 — 微信公众号文章采集与理论收敛分析工具

## 1. 环境准备

### 1.1 系统要求

- Python 3.13+
- Windows / macOS / Linux
- 网络连接（需访问微信公众号后台和 DeepSeek API）

### 1.2 安装依赖

```bash
# 进入项目目录
cd wechat-article-analyzer

# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器内核（首次必须执行）
playwright install chromium
```

### 1.3 配置 DeepSeek API 密钥

方式一：环境变量（推荐）

```bash
# Linux/macOS
export DEEPSEEK_API_KEY="sk-your-api-key-here"

# Windows PowerShell
$env:DEEPSEEK_API_KEY="sk-your-api-key-here"
```

方式二：配置文件

```bash
python -m src.main config set deepseek_api_key "sk-your-api-key-here"
```

### 1.4 验证安装

```bash
# 查看帮助
python -m src.main --help

# 查看默认配置
python -m src.main config show

# 查看数据库状态（应显示空状态）
python -m src.main status
```

---

## 2. 完整使用流程

### 概览

```
login → crawl → analyze → report → graph
```

### 2.1 第一步：登录微信公众号后台

```bash
python -m src.main login
```

- 自动打开 Chromium 浏览器，访问 `mp.weixin.qq.com`
- **用手机微信扫码登录**
- 登录成功后自动保存 Cookie，后续操作无需重复扫码
- 超时时间默认 300 秒，可通过 `--timeout 600` 调整

> **提示**：Cookie 有效期有限，如后续操作提示未登录，重新执行 `login` 即可。

### 2.2 第二步：批量采集文章

```bash
# 全量采集
python -m src.main crawl

# 断点续抓（跳过已采集的文章）
python -m src.main crawl --resume

# 限制采集数量（用于测试）
python -m src.main crawl --limit 10
```

**采集内容**：
- 文章标题
- 发布时间
- 正文 HTML
- 正文纯文本（自动清洗）
- 封面图 URL

**防风控机制**：
- 每篇文章间隔 2-3 秒随机延迟
- 使用持久化浏览器上下文
- 失败自动记录，不中断整体流程

**进度显示**：
```
[150/2000] 正在抓取: 刘原理与三视界法的深层关联...
```

### 2.3 第三步：AI 分析文章

```bash
# 全量分析
python -m src.main analyze

# 断点续分析（跳过已分析的文章）
python -m src.main analyze --resume

# 只分析指定文章
python -m src.main analyze --article-id 42
```

**每篇文章的 AI 分析内容**：
- 核心概念提取
- 关键词标注
- 理论支柱分类（刘原理 / 三视界法 / 太乙预言机 / 全息拓扑动力学）
- 文章理论摘要
- TOMAS-AGI / 太极OS 项目关联性判断

**API 调用**：
- 模型：DeepSeek (deepseek-chat)
- 每篇文章截断至 8000 字符
- 失败自动重试（指数退避，最多 3 次）

### 2.4 第四步：生成理论收敛报告

```bash
# 生成报告（默认输出到 ./output/report.md）
python -m src.main report

# 指定输出路径
python -m src.main report --output ./output/my_report.md
```

**报告内容**：
1. **核心理论框架** — 从 2000 篇文章中收敛出的理论主干
2. **关键概念集群** — 高频概念及其聚类关系
3. **概念演化路径** — 按时间线追踪理论发展脉络
4. **理论支柱总结** — 四大基石各自的文章分布和核心命题

**输出文件**：
- `output/report.md` — 可读 Markdown 报告
- `output/report.json` — 结构化 JSON 数据

### 2.5 第五步：构建概念关系图谱

```bash
python -m src.main graph --output ./output/concept_graph.json
```

**输出文件**：
- `output/concept_graph.json` — 图谱数据（节点+边+权重）
- `output/concept_graph.mmd` — Mermaid 格式可视化文件

### 2.6 查看状态

```bash
python -m src.main status
```

输出示例：
```
=== 采集状态 ===
总文章数: 2000
已采集: 2000 篇
采集失败: 0 篇

=== 分析状态 ===
已分析: 1200 篇
分析失败: 3 篇
待分析: 797 篇
```

---

## 3. 配置管理

### 3.1 查看当前配置

```bash
python -m src.main config show
```

### 3.2 修改配置

```bash
# 设置 API 密钥
python -m src.main config set deepseek_api_key "sk-xxx"

# 设置模型
python -m src.main config set deepseek_model "deepseek-chat"

# 设置采集间隔（秒）
python -m src.main config set crawl_interval_min 3
python -m src.main config set crawl_interval_max 5
```

### 3.3 配置文件

配置文件位于项目根目录 `config.json`，可直接编辑：

```json
{
    "deepseek_api_key": "",
    "deepseek_model": "deepseek-chat",
    "deepseek_base_url": "https://api.deepseek.com/v1",
    "db_path": "./data/articles.db",
    "cookies_path": "./data/cookies.json",
    "browser_data_dir": "./data/browser_data",
    "crawl_interval_min": 2,
    "crawl_interval_max": 3,
    "login_timeout": 300,
    "log_level": "INFO",
    "log_file": "./logs/app.log",
    "output_dir": "./output",
    "theory_pillars": ["刘原理", "三视界法", "太乙预言机", "全息拓扑动力学"],
    "tomas_agi_keywords": ["TOMAS-AGI", "TOMAS", "AGI", "通用人工智能"],
    "taiji_os_keywords": ["太极OS", "太极操作系统", "TaijiOS"]
}
```

---

## 4. 常见问题

### Q: 采集过程中断了怎么办？
A: 使用 `python -m src.main crawl --resume` 断点续抓，已完成的文章会自动跳过。

### Q: API 调用失败怎么办？
A: 系统会自动重试 3 次（指数退避）。如果仍然失败，该文章状态标记为 `failed`，可稍后用 `--resume` 重新分析。

### Q: Cookie 过期了怎么办？
A: 重新执行 `python -m src.main login` 扫码登录即可。

### Q: 如何只分析特定文章？
A: 使用 `python -m src.main analyze --article-id <ID>`，ID 可通过 `status` 命令查看。

### Q: 报告内容不够深入？
A: 确保所有文章已完成分析（`status` 查看进度）。报告基于全量分析结果生成，文章越多越准确。

### Q: 采集速度可以加快吗？
A: 可以调小 `crawl_interval_min` 和 `crawl_interval_max`，但不建议低于 1 秒，可能触发微信风控。

---

## 5. 目录结构说明

```
wechat-article-analyzer/
├── src/           # 源代码
├── tests/         # 测试文件
├── data/          # 运行时数据（数据库、cookies、浏览器数据）
├── logs/          # 运行日志
├── output/        # 报告与图谱输出
├── docs/          # 文档
├── config.json    # 配置文件
└── requirements.txt
```

---

## 7. v2.0 Web 界面

v2.0 新增基于浏览器的交互式界面，可在完成文章采集和分析后，通过可视化方式浏览结果。

### 7.1 启动 Web 界面

> **注意**：由于 Vite 8 与 MUI+Emotion 的兼容性已知问题，**必须使用 `build + preview` 模式**，不能用 `vite dev`。

**第一步：启动后端 API（终端 1）**

```bash
cd wechat-article-analyzer
PYTHONPATH=. python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8001
```

成功启动后显示：
```
INFO:     Uvicorn running on http://0.0.0.0:8001
```

**第二步：构建并预览前端（终端 2）**

```bash
cd wechat-article-analyzer/frontend
npm install          # 首次需要，后续可跳过
npm run build       # 构建到 dist/ 目录
npm run preview     # 启动预览服务器（端口 3000）
```

**第三步：打开浏览器**

```
http://localhost:3000/
```

### 7.2 功能导览

#### 仪表盘（`#/`）

首页显示系统整体状态：
- 文章总数、已分析数、分析进度百分比
- 理论支柱分布（饼图/柱状图）
- 最近采集的文章列表
- 最近分析的 AI 摘要

#### 文章列表（`#/articles`）

- 分页浏览所有已采集文章
- 支持按标题关键词搜索
- 点击「查看详情」进入文章详情页

#### 文章详情（`#/articles/:id`）

- 显示文章完整标题、发布时间、封面图
- **全文显示**：保留段落格式，支持完整滚动阅读
- 显示 AI 分析结果：核心概念、关键词、理论支柱标注、摘要
- 点击「查看概念图谱」按钮，跳转到该文章的概念子图

#### 概念图谱（`#/concept-graph`）

交互式概念关系网络，基于 vis-network 渲染：

- **拖拽节点**：自由排列布局
- **缩放**：鼠标滚轮或 pinch 手势
- **点击节点**：高亮该节点的所有连接边
- **筛选 Top N**：调整滑块过滤高频概念
- **单篇子图**：从文章详情页点击「查看概念图谱」进入，仅显示该文章涉及的概念及其关系

#### 演化追踪（`#/evolution`）

- 按时间线显示核心概念出现频率变化
- 支持多选概念进行对比
- 折线图 + 面积图两种展示模式

#### 概念列表（`#/concepts`）

- 按出现频率排序的所有概念列表
- 支持分页和关键词搜索
- 显示每个概念的频率和归属理论支柱

#### 跨理论对比（`#/cross-theory`）

- 对比不同理论支柱的概念分布
- 显示各支柱的核心概念和演化趋势

### 7.3 常见问题（Web 界面）

#### Q：打开 `localhost:3000` 显示空白或 502？

A：后端 API 未启动或端口不对。确认终端 1 的后端正在运行（端口 8001），且前端 `vite preview` 正在运行（端口 3000）。

#### Q：点击「查看概念图谱」后图表区域显示「无数据」？

A：该文章的概念之间可能没有共现关系（概念关系是从全库统计的）。当前版本仅展示有关系连接的概念；未来版本会将文章的所有概念作为孤立节点纳入子图。

#### Q：修改代码后页面没有更新？

A：`vite preview`  serving 的是 `dist/` 目录的静态文件，不会热更新。每次修改代码后需要重新执行 `npm run build`，然后刷新浏览器（Ctrl+Shift+R 强制刷新）。

#### Q：`npm run dev` 卡死了怎么办？

A：这是已知的 Vite 8 + MUI + Emotion 兼容性问题。请使用 `npm run build && npm run preview` 替代，详见 `README.md` 中的「已知问题与解决」章节。

#### Q：如何部署到生产环境？

A：将 `frontend/dist/` 目录部署到任意静态文件服务器（nginx、Vercel、Netlify 等）。确保 API 请求被正确代理到后端（生产环境需配置 nginx 反向代理或修改 API 基础 URL）。

---

## 8. 目录结构说明（完整版）

```
wechat-article-analyzer/
├── src/
│   ├── main.py                    # CLI 入口
│   ├── config.py                  # 配置管理
│   ├── database.py                # SQLite 数据层
│   ├── models.py                  # Pydantic 数据模型
│   ├── analyzer/                  # 分析模块
│   ├── crawler/                   # 采集模块
│   ├── report/                    # 报告模块
│   ├── api/                       # FastAPI 后端（v2.0）
│   │   ├── app.py                 # FastAPI 应用入口
│   │   ├── routes.py              # RESTful API 路由
│   │   └── dependencies.py        # 依赖注入
│   └── utils/                     # 工具模块
├── frontend/                      # React + MUI Web 界面（v2.0）
│   ├── src/
│   │   ├── App.tsx               # 路由配置
│   │   ├── api/client.ts         # API 客户端
│   │   ├── store/useAppStore.ts  # Zustand 状态管理
│   │   ├── pages/                # 页面组件
│   │   └── theme/                # MUI 主题
│   ├── package.json
│   ├── vite.config.ts            # Vite 配置
│   └── dist/                     # 构建输出（gitignore）
├── tests/                         # 单元测试
├── docs/                          # 文档
├── data/                          # 数据库（gitignore）
├── logs/                          # 日志（gitignore）
├── output/                        # 报告输出（gitignore）
├── config.json                    # 配置文件（gitignore）
└── requirements.txt
```

---

## 9. 日志查看

日志文件位于 `logs/app.log`，按天轮转，保留 7 天。

```bash
# 查看最新日志
tail -f logs/app.log

# 只看错误
grep ERROR logs/app.log

# Web 后端日志（单独终端运行）
# 直接在运行 uvicorn 的终端查看输出
```


