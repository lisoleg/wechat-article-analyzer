"""Pydantic 响应模型 — 定义所有 API 端点的请求/响应格式。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ============================================================
# 通用响应
# ============================================================
class StatusResponse(BaseModel):
    """数据库状态响应。"""

    total_articles: int = Field(..., description="文章总数")
    crawled: int = Field(..., description="采集完成数")
    pending: int = Field(..., description="待采集数")
    analyzed: int = Field(..., description="分析完成数")
    db_size_mb: float = Field(..., description="数据库文件大小(MB)")


class StatsSummary(BaseModel):
    """综合统计摘要。"""

    total_articles: int = Field(..., description="文章总数")
    crawled: int = Field(..., description="采集完成数")
    analyzed: int = Field(..., description="分析完成数")
    total_concepts: int = Field(..., description="唯一概念数")
    total_relations: int = Field(..., description="概念关系数")
    pillar_distribution: dict[str, int] = Field(..., description="理论支柱分布")
    last_analysis_time: str | None = Field(None, description="最近分析时间")


# ============================================================
# 概念图谱
# ============================================================
class GraphNode(BaseModel):
    """图谱节点。"""

    id: str = Field(..., description="概念名称")
    label: str = Field(..., description="显示标签")
    frequency: int = Field(..., description="出现频次")


class GraphEdge(BaseModel):
    """图谱边。"""

    source: str = Field(..., description="源节点")
    target: str = Field(..., description="目标节点")
    weight: int = Field(..., description="共现次数")


class GraphMetadata(BaseModel):
    """图谱元数据。"""

    total_nodes: int
    total_edges: int
    top_n: int


class GraphResponse(BaseModel):
    """概念关系图谱响应。"""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    metadata: GraphMetadata


class FullGraphResponse(BaseModel):
    """完整概念关系图谱响应。"""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    total: int = Field(..., description="总关系数")


# ============================================================
# 概念演化
# ============================================================
class TimelineItem(BaseModel):
    """时间线单项。"""

    time: str = Field(..., description="时间点(YYYY-MM)")
    article_count: int = Field(..., description="该时间点文章数")
    concept_counts: dict[str, int] = Field(..., description="各概念出现频次")


class ConceptEvolutionSummary(BaseModel):
    """单个概念的演化摘要。"""

    first_seen: str | None = None
    peak_time: str | None = None
    peak_count: int = 0
    total_count: int = 0
    recent_trend: str = "stable"


class EvolutionResponse(BaseModel):
    """概念演化响应。"""

    tracked_concepts: list[str]
    timeline: list[TimelineItem]
    summary: dict[str, ConceptEvolutionSummary]


# ============================================================
# 概念
# ============================================================
class ConceptFrequencyItem(BaseModel):
    """概念频次项。"""

    concept: str
    frequency: int


class ConceptRelationItem(BaseModel):
    """概念关联关系项。"""

    related_concept: str = Field(..., description="关联概念")
    weight: int = Field(..., description="共现权重")


class StandardizeResponse(BaseModel):
    """标准化响应。"""

    query: str = Field(..., description="原始查询")
    standardized: list[str] = Field(..., description="标准化结果")


class ConceptSearchResponse(BaseModel):
    """概念搜索响应。"""

    query: str
    results: list[str]
    total: int


# ============================================================
# 文章
# ============================================================
class ArticleSummary(BaseModel):
    """文章摘要（列表项）。"""

    id: int
    title: str
    url: str
    publish_time: str | None = None
    crawl_status: str
    has_analysis: bool = Field(False, description="是否已分析")


class ArticleDetail(BaseModel):
    """文章详情（含分析结果）。"""

    id: int
    title: str
    url: str
    publish_time: str | None = None
    cover_image_url: str | None = None
    crawl_status: str
    crawl_time: str | None = None
    content_text: str | None = None
    analysis: dict[str, Any] | None = None


class ArticleListResponse(BaseModel):
    """文章列表响应（分页）。"""

    total: int
    page: int
    page_size: int
    articles: list[ArticleSummary]


class ArticleSearchResponse(BaseModel):
    """文章搜索响应。"""

    query: str
    total: int
    articles: list[ArticleSummary]


# ============================================================
# 理论体系与跨理论分析
# ============================================================
class TheorySystemInfo(BaseModel):
    """理论体系信息。"""

    id: int
    system_name: str
    description: str
    pillars: list[str]
    color_code: str


class TheoryPillarDistribution(BaseModel):
    """理论体系支柱分布。"""

    pillar: str
    count: int


class CrossTheorySystem(BaseModel):
    """跨理论分析中的理论体系数据。"""

    name: str
    description: str
    color_code: str
    pillars: list[str]
    pillar_distribution: dict[str, int]
    total_articles: int
    top_concepts: list[dict[str, Any]]
    unique_concepts: list[str]


class CrossTheoryResponse(BaseModel):
    """跨理论体系对比响应。"""

    systems: list[CrossTheorySystem]
    shared_concepts: list[str]
    all_concepts_count: int


# ============================================================
# 同义词、增量日志、多模型
# ============================================================
class SynonymMapItem(BaseModel):
    """同义词映射项。"""

    id: int
    original_concept: str
    standardized_concept: str
    mapping_type: str
    confidence: float
    created_at: str


class IncrementalLogItem(BaseModel):
    """增量分析日志项。"""

    id: int
    last_article_id: int | None = None
    last_analysis_time: str | None = None
    new_articles_count: int = 0
    new_concepts_count: int = 0
    executed_at: str


class MultiModelStats(BaseModel):
    """多模型验证统计。"""

    total_results: int
    total_articles: int
    avg_consistency: float
    model_counts: dict[str, int]


# ============================================================
# 错误响应
# ============================================================
class ErrorResponse(BaseModel):
    """错误响应。"""

    detail: str
    code: str | None = None
