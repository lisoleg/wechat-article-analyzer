"""数据模型定义 — Article 与 AnalysisResult dataclass。

所有时间字段使用 ISO 8601 格式字符串。
JSON 字段（concepts / keywords / theory_pillars）在内存中为 list[str]，
持久化到 SQLite 时由 ArticleRepository 序列化为 JSON 字符串。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Article:
    """文章数据模型，对应 articles 表。

    Attributes:
        id: 数据库自增主键，新建未入库时为 None。
        title: 文章标题。
        url: 文章唯一 URL（用于去重）。
        publish_time: 发布时间（ISO 8601）。
        cover_image_url: 封面图 URL。
        content_html: 正文 HTML。
        content_text: 正文纯文本。
        crawl_status: 采集状态 — pending / in_progress / complete / failed。
        crawl_time: 采集完成时间（ISO 8601）。
        crawl_error: 采集失败时的错误信息。
    """

    id: Optional[int] = None
    title: str = ""
    url: str = ""
    publish_time: Optional[str] = None
    cover_image_url: Optional[str] = None
    content_html: Optional[str] = None
    content_text: Optional[str] = None
    crawl_status: str = "pending"
    crawl_time: Optional[str] = None
    crawl_error: Optional[str] = None


@dataclass
class AnalysisResult:
    """分析结果数据模型，对应 analysis_results 表。

    Attributes:
        id: 数据库自增主键，新建未入库时为 None。
        article_id: 关联的文章 ID。
        concepts: 提取的核心概念列表。
        keywords: 提取的关键词列表。
        theory_pillars: 标注的理论支柱列表（从预定义列表中选择）。
        summary: 文章理论摘要（1-2 句）。
        tomas_agi_related: 是否与 TOMAS-AGI 项目相关。
        taiji_os_related: 是否与太极 OS 项目相关。
        analysis_status: 分析状态 — pending / in_progress / complete / failed。
        analysis_time: 分析完成时间（ISO 8601）。
        analysis_error: 分析失败时的错误信息。
    """

    id: Optional[int] = None
    article_id: int = 0
    concepts: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    theory_pillars: list[str] = field(default_factory=list)
    summary: Optional[str] = None
    tomas_agi_related: bool = False
    taiji_os_related: bool = False
    analysis_status: str = "pending"
    analysis_time: Optional[str] = None
    analysis_error: Optional[str] = None
