# 微信公众号文章采集与理论收敛分析工具

> 基于 Playwright + DeepSeek API 的大规模公众号文章采集与理论体系收敛分析系统

[![Python](https://img.shields.io/badge/Python-3.13-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-52%20passed-brightgreen)](#)

## 简介

本工具专为理论研究者构建，解决"近2000篇公众号文章难以系统性整理"的痛点。通过浏览器自动化批量采集微信公众号文章，利用大语言模型（LLM）进行深度分析，实现理论体系的收敛——提取核心概念、构建概念关系图谱、追踪理论演化脉络、生成结构化收敛报告。

核心应用场景：**复合体理学理论体系收敛**（刘原理、三视界法、太乙预言机、全息拓扑动力学四大理论支柱）。

## 功能特性

### 采集模块
- **扫码登录** — Playwright 驱动浏览器，用户扫码一次即可
- **批量抓取** — 自动获取全部已发布文章列表，逐篇抓取正文
- **断点续抓** — 基于数据库状态持久化，中断后 `--resume` 继续
- **防风控** — 每篇间隔 2-3 秒随机延迟

### 分析模块
- **逐篇 AI 分析** — DeepSeek API 提取核心概念、关键词、理论支柱标注
- **概念关系图谱** — 基于共现频率构建概念关联网络，支持按文章过滤子图
- **演化脉络追踪** — 按时间线追踪概念出现频率变化趋势
- **项目关联标注** — 自动识别 TOMAS-AGI / 太极OS 项目相关内容

### 报告模块
- **理论收敛报告** — Markdown + JSON 双格式输出
- **概念图谱可视化** — Mermaid 格式概念关系图
- **演化趋势分析** — rising / declining / stable 趋势分类

### v2.0 Web 界面
- **仪表盘**：统计概览、理论支柱分布、最近文章
- **文章管理**：文章列表、详情查看、**全文段落格式显示**、AI 分析结果
- **概念图谱**：交互式概念关系网络（vis-network），支持按文章展示概念子图
- **演化追踪**：概念频次随时间变化趋势（折线图、面积图）
- **概念列表**：按权重排列的概念列表（分页、搜索）
- **跨理论对比**：多理论体系的收敛对比分析

## 快速开始

### 环境要求

- Python >= 3.12
- Node.js >= 18（Web 界面）
- Chromium 浏览器（Playwright 自动安装）

### 安装

```bash
git clone https://github.com/lisoleg/wechat-article-analyzer.git
cd wechat-article-analyzer
pip install -r requirements.txt
playwright install chromium
```

### 配置

```bash
# 设置 DeepSeek API Key
export DEEPSEEK_API_KEY="your-api-key-here"

# 或通过 CLI 配置
python -m src.main config set deepseek_api_key "your-api-key-here"
```

### 使用流程

```bash
# 1. 扫码登录公众号后台
python -m src.main login

# 2. 批量采集文章（支持断点续抓）
python -m src.main crawl
python -m src.main crawl --resume  # 中断后继续

# 3. AI 逐篇分析
python -m src.main analyze
python -m src.main analyze --resume  # 中断后继续

# 4. 生成理论收敛报告
python -m src.main report --output output/convergence_report.md

# 5. 构建概念关系图谱
python -m src.main graph --output output/concept_graph.mmd

# 6. 查看进度
python -m src.main status
```

### 启动 Web 界面

> **注意**：由于 Vite 8 开发服务器与 MUI + emotion 存在兼容性问题（`vite dev` 卡死在依赖优化阶段），生产环境请使用 `vite build && vite preview` 方式启动。

```bash
# 终端 1：启动后端 API（端口 8001）
cd wechat-article-analyzer
PYTHONPATH=. python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8001

# 终端 2：构建并预览前端（端口 3000）
cd wechat-article-analyzer/frontend
npm install
npm run build && npm run preview

# 3. 访问 Web 界面
open http://localhost:3000/
```

## CLI 命令一览

| 命令 | 说明 | 关键参数 |
|------|------|---------|
| `login` | 扫码登录公众号后台 | `--timeout 300` |
| `crawl` | 批量采集文章 | `--resume`, `--limit N` |
| `analyze` | AI 分析文章 | `--resume`, `--article-id N` |
| `report` | 生成理论收敛报告 | `--output path` |
| `graph` | 构建概念关系图谱 | `--output path` |
| `status` | 查看采集与分析进度 | — |
| `config` | 配置管理 | `set`, `show` |

## 项目结构

```
wechat-article-analyzer/
├── src/
│   ├── main.py                    # CLI 入口
│   ├── config.py                  # 配置管理
│   ├── database.py                # SQLite 数据层（含概念关系统计）
│   ├── models.py                  # 数据模型（Pydantic）
│   ├── analyzer/                  # 分析模块
│   │   ├── deepseek_client.py     # DeepSeek API 客户端
│   │   ├── article_analyzer.py    # 单篇分析器
│   │   └── concepts.py            # 概念处理
│   ├── crawler/                   # 采集模块
│   │   ├── browser.py             # 浏览器管理
│   │   ├── login.py               # 登录处理
│   │   ├── article_list.py        # 文章列表获取
│   │   └── article_content.py     # 正文抓取（含 HTML 清洗）
│   ├── report/                    # 报告模块
│   │   ├── convergence_report.py  # 收敛报告生成（含 AI 综合）
│   │   ├── concept_graph.py       # 概念图谱构建
│   │   └── evolution_tracker.py   # 演化追踪
│   ├── api/                       # FastAPI 后端（v2.0）
│   │   ├── app.py                 # FastAPI 应用入口
│   │   ├── routes.py              # RESTful API 路由
│   │   └── dependencies.py        # 依赖注入
│   └── utils/                     # 工具模块
│       ├── html_cleaner.py        # HTML 清洗
│       ├── logger.py              # 日志
│       └── progress.py            # 进度显示
├── frontend/                      # React + MUI Web 界面（v2.0）
│   ├── src/
│   │   ├── App.tsx               # 路由配置（HashRouter）
│   │   ├── api/client.ts         # API 客户端（Axios）
│   │   ├── store/useAppStore.ts  # Zustand 全局状态
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx     # 仪表盘
│   │   │   ├── ArticleList.tsx   # 文章列表
│   │   │   ├── ArticleDetail.tsx # 文章详情（含全文格式显示）
│   │   │   ├── ConceptGraph.tsx  # 概念图谱（vis-network/standalone）
│   │   │   ├── Evolution.tsx     # 演化追踪
│   │   │   ├── ConceptList.tsx   # 概念列表
│   │   │   └── CrossTheory.tsx   # 跨理论对比
│   │   └── theme/                # MUI 主题配置
│   ├── package.json
│   ├── vite.config.ts            # Vite 配置（含 API 代理）
│   └── tsconfig.json
├── tests/                         # 单元测试（52个）
├── docs/                          # 文档
│   ├── PRD.md                     # 产品需求文档
│   ├── ARCHITECTURE.md            # 架构设计文档
│   ├── ARCHITECTURE-v2.md        # v2.0 架构更新
│   ├── USER_GUIDE.md              # 使用指南
│   ├── TECHNICAL.md               # 技术文档
│   ├── paper.md                    # 学术论文
│   └── *.mermaid                 # Mermaid 图表源文件
├── data/                          # 数据目录（SQLite 数据库）
├── output/                        # 报告输出目录
├── config.json                    # 默认配置
├── requirements.txt               # Python 依赖声明
└── pyproject.toml               # 项目元数据（含 CLI 入口）
```

## 数据库设计

| 表名 | 用途 |
|------|------|
| `articles` | 文章数据 + 采集状态（含完整正文 `content_text`） |
| `analysis_results` | AI 分析结果（概念/关键词/理论支柱/摘要） |
| `concept_relations` | 概念共现统计（含强度评分） |

## Web API 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/status` | GET | 获取系统状态（文章总数、分析进度等） |
| `/api/articles` | GET | 获取文章列表（分页、过滤） |
| `/api/articles/{id}` | GET | 获取单篇文章详情（含完整正文） |
| `/api/concept-graph` | GET | 获取概念图谱数据（节点 + 边），支持 `article_id` 参数过滤单篇文章概念子图 |
| `/api/evolution` | GET | 获取概念演化数据 |
| `/api/concepts` | GET | 获取概念列表（分页、搜索） |
| `/api/pillars/distribution` | GET | 获取理论支柱分布统计 |
| `/api/cross-theory` | GET | 获取跨理论对比数据 |

## 文档

- [使用指南](docs/USER_GUIDE.md) — 安装、配置、完整使用流程
- [技术文档](docs/TECHNICAL.md) — 架构设计、模块详解、数据库设计
- [架构设计](docs/ARCHITECTURE.md) — 系统架构、类图、时序图
- [学术论文](docs/paper.md) — 基于 LLM 的理论收敛分析系统

## 测试

```bash
python -m pytest tests/ -v
```

52 个单元测试覆盖：数据库 CRUD、HTML 清洗、概念处理、DeepSeek 客户端重试逻辑。

## 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| 语言 | Python 3.13 | 类型标注 + dataclass |
| 浏览器自动化 | Playwright | 反检测、SPA 渲染、Cookie 持久化 |
| AI API | DeepSeek (deepseek-chat) | OpenAI SDK 兼容模式 |
| 存储 | SQLite | 零配置文件级存储 |
| CLI | Click + Rich | 命令组 + 美观进度条 |
| 日志 | Loguru | 控制台 + 文件双输出 |
| HTML 解析 | BeautifulSoup4 + lxml | 高性能解析，支持回退 |
| **Web 后端** | **FastAPI** | 异步 RESTful API |
| **Web 前端** | **React 18 + TypeScript + Vite** | 基于 HashRouter 的 SPA |
| **UI 框架** | **MUI v5 + Emotion** | Material Design 组件库 |
| **状态管理** | **Zustand** | 轻量级 TypeScript 友好 |
| **图表可视化** | **vis-network/standalone** | 交互式概念关系网络 |
| **趋势图表** | **Recharts** | 演化趋势折线图/面积图 |

## 已知问题与解决

### `vite dev` 卡死在依赖优化阶段

MUI 5 + Emotion + Vite 8 组合下，`vite dev` 的开发服务器优化器会卡死在 "bundling dependencies..."。解决方案：使用 `vite build && vite preview` 替代开发服务器。

### 文章全文显示不全

确保 `src/api/routes.py` 中 `content_text` 字段未被截断（移除 `[:2000]` 切片）。前端 `ArticleDetail.tsx` 使用 `dangerouslySetInnerHTML` 渲染带段落格式的正文。

## 许可证

Apache License 2.0

## 作者

章锋、李宗海
