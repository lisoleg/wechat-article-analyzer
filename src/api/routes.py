"""FastAPI 路由模块 — 注册所有 API 端点。"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from src.api.dependencies import get_repo, get_graph_builder, get_evolution_tracker, get_standardizer
from src.api.models import (
    StatusResponse,
    StatsSummary,
    GraphResponse,
    FullGraphResponse,
    GraphNode,
    GraphEdge,
    TimelineItem,
    ConceptEvolutionSummary,
    EvolutionResponse,
    ConceptFrequencyItem,
    ConceptRelationItem,
    ConceptSearchResponse,
    StandardizeResponse,
    ArticleDetail,
    ArticleListResponse,
    ArticleSearchResponse,
    ArticleSummary,
    TheorySystemInfo,
    TheoryPillarDistribution,
    CrossTheorySystem,
    CrossTheoryResponse,
    SynonymMapItem,
    IncrementalLogItem,
    MultiModelStats,
    ErrorResponse,
)

router = APIRouter()


# ============================================================
# 1. 状态与统计
# ============================================================
@router.get(
    "/status",
    response_model=StatusResponse,
    tags=["状态"],
    summary="获取数据库状态",
)
def get_status(repo: Any = Depends(get_repo)) -> StatusResponse:
    """返回数据库统计信息（文章总数、采集数、分析数等）。"""
    stats = repo.get_stats()
    db_path = getattr(router, "_db_path", "data/articles.db")
    db_size = 0.0
    if os.path.exists(db_path):
        db_size = round(os.path.getsize(db_path) / (1024 * 1024), 2)
    return StatusResponse(
        total_articles=stats["total"],
        crawled=stats["crawled"],
        pending=stats["total"] - stats["crawled"],
        analyzed=stats["analyzed"],
        db_size_mb=db_size,
    )


@router.get(
    "/stats/summary",
    response_model=StatsSummary,
    tags=["统计"],
    summary="获取综合统计摘要",
)
def get_stats_summary(repo: Any = Depends(get_repo)) -> StatsSummary:
    """返回综合统计（文章数、概念数、关系数、支柱分布等）。"""
    from src.analyzer.concepts import ConceptProcessor

    stats = repo.get_stats()
    proc = ConceptProcessor(repo)
    concept_freq = proc.get_concept_frequency()
    total_relations = repo.get_concept_relations_count()
    last_log = repo.get_last_incremental_log()
    return StatsSummary(
        total_articles=stats["total"],
        crawled=stats["crawled"],
        analyzed=stats["analyzed"],
        total_concepts=len(concept_freq),
        total_relations=total_relations,
        pillar_distribution=proc.get_pillar_distribution(),
        last_analysis_time=last_log.get("executed_at") if last_log else None,
    )


# ============================================================
# 2. 概念图谱
# ============================================================
@router.get(
    "/concept-graph",
    response_model=GraphResponse,
    tags=["概念图谱"],
    summary="获取概念关系图谱",
)
def get_concept_graph(
    builder: Any = Depends(get_graph_builder),
    top_n: int = Query(100, ge=1, le=500, description="取 Top N 概念"),
    article_id: int = Query(None, description="按文章 ID 过滤（返回该文章的概念子图）"),
) -> GraphResponse:
    """基于共现矩阵构建概念关系图谱。
    - 无 article_id：返回全量 Top N 概念图谱
    - 有 article_id：返回该文章涉及的概念子图
    """
    if article_id is not None:
        # 文章专属子图
        article = builder.repo.get_article(article_id)
        if not article:
            raise HTTPException(status_code=404, detail=f"文章 ID={article_id} 不存在")
        analysis = builder.repo.get_analysis_result(article_id)
        if not analysis or not analysis.concepts:
            return GraphResponse(
                nodes=[],
                edges=[],
                metadata={"total_nodes": 0, "total_edges": 0, "top_n": 0, "article_id": article_id},
            )
        concepts = analysis.concepts  # List[str]
        concept_set = set(concepts)
        # 节点
        nodes = [
            {"id": c, "label": c, "frequency": builder.freq.get(c, 0)}
            for c in concepts
        ]
        # 边：查询 concept_relations 中这些概念之间的关系
        conn = builder.repo.db.get_connection()
        placeholders = ",".join(["?"] * len(concepts))
        rows = conn.execute(
            f"SELECT concept_a, concept_b, co_occurrence_count "
            f"FROM concept_relations "
            f"WHERE concept_a IN ({placeholders}) AND concept_b IN ({placeholders})",
            list(concepts) + list(concepts),
        ).fetchall()
        edges = [
            {"source": r["concept_a"], "target": r["concept_b"],
             "weight": float(r["co_occurrence_count"])}
            for r in rows
        ]
        return GraphResponse(
            nodes=nodes,
            edges=edges,
            metadata={
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "top_n": len(nodes),
                "article_id": article_id,
            },
        )
    # 全量图谱
    graph_data = builder.build_graph(top_n=top_n)
    return GraphResponse(
        nodes=[{"id": n["id"], "label": n["label"], "frequency": n["frequency"]} for n in graph_data["nodes"]],
        edges=[{"source": e["source"], "target": e["target"], "weight": e["weight"]} for e in graph_data["edges"]],
        metadata={
            "total_nodes": graph_data["metadata"]["total_nodes"],
            "total_edges": graph_data["metadata"]["total_edges"],
            "top_n": graph_data["metadata"]["top_n"],
        },
    )


@router.get(
    "/concept-graph/full",
    response_model=FullGraphResponse,
    tags=["概念图谱"],
    summary="获取完整概念关系图谱",
)
def get_concept_graph_full(
    limit: int = Query(500, ge=1, le=2000, description="最多返回关系数"),
    repo: Any = Depends(get_repo),
) -> FullGraphResponse:
    """返回 concept_relations 表中所有关系（分页）。"""
    from src.analyzer.concepts import ConceptProcessor

    proc = ConceptProcessor(repo)
    freq = proc.get_concept_frequency()
    rows = repo.get_concept_relations(limit)
    nodes_set: dict[str, int] = {}
    edges: list[dict] = []
    for r in rows:
        a, b = r["concept_a"], r["concept_b"]
        w = r["co_occurrence_count"]
        if a not in nodes_set:
            nodes_set[a] = freq.get(a, 0)
        if b not in nodes_set:
            nodes_set[b] = freq.get(b, 0)
        edges.append({"source": a, "target": b, "weight": w})
    nodes = [{"id": c, "label": c, "frequency": f} for c, f in nodes_set.items()]
    return FullGraphResponse(nodes=nodes, edges=edges, total=len(rows))


@router.get(
    "/relations",
    tags=["概念关系"],
    summary="获取概念关系列表（分页）",
)
def list_relations(
    limit: int = Query(20, ge=1, le=500, description="每页条数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    search: str = Query("", description="搜索关键词"),
    repo: Any = Depends(get_repo),
):
    """返回 concept_relations 表中的关系列表（分页+搜索）。"""
    conn = repo.db.get_connection()
    if search.strip():
        like = f"%{search.strip()}%"
        total = conn.execute(
            "SELECT COUNT(*) FROM concept_relations WHERE concept_a LIKE ? OR concept_b LIKE ?",
            (like, like),
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT concept_a, concept_b, co_occurrence_count FROM concept_relations WHERE concept_a LIKE ? OR concept_b LIKE ? ORDER BY co_occurrence_count DESC LIMIT ? OFFSET ?",
            (like, like, limit, offset),
        ).fetchall()
    else:
        total = conn.execute("SELECT COUNT(*) FROM concept_relations").fetchone()[0]
        rows = conn.execute(
            "SELECT concept_a, concept_b, co_occurrence_count FROM concept_relations ORDER BY co_occurrence_count DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    items = [
        {
            "concept_a": r["concept_a"],
            "concept_b": r["concept_b"],
            "relation_type": "共现",
            "weight": float(r["co_occurrence_count"]),
        }
        for r in rows
    ]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


# ============================================================
# 3. 概念演化
# ============================================================
@router.get(
    "/evolution",
    response_model=EvolutionResponse,
    tags=["概念演化"],
    summary="获取概念演化时间线",
)
def get_evolution(
    concepts: str | None = Query(None, description="逗号分隔的概念列表"),
    top_n: int = Query(10, ge=1, le=50, description="自动取 Top N 概念"),
    tracker: Any = Depends(get_evolution_tracker),
    repo: Any = Depends(get_repo),
) -> EvolutionResponse:
    """追踪核心概念的演化脉络。"""
    from src.analyzer.concepts import ConceptProcessor
    from src.report.evolution_tracker import EvolutionTracker
    import traceback

    try:
        # 直接使用传入的 tracker（已通过依赖注入缓存）
        if concepts:
            concept_list = [c.strip() for c in concepts.split(",") if c.strip()]
            top_concepts = [(c, 0) for c in concept_list]
            evolution_data = tracker.track_evolution(top_concepts=top_concepts)
        else:
            proc = ConceptProcessor(repo)
            top_concepts = proc.get_top_concepts(top_n)
            print(f"Top concepts: {top_concepts[:5]}")
            evolution_data = tracker.track_evolution(top_concepts=top_concepts)
        
        print(f"Evolution data timeline length: {len(evolution_data['timeline'])}")
        print(f"Evolution data summary keys: {list(evolution_data['summary'].keys())}")
        
        timeline = [
            TimelineItem(time=t["time"], article_count=t["article_count"], concept_counts=t["concept_counts"])
            for t in evolution_data["timeline"]
        ]
        summary = {k: ConceptEvolutionSummary(**v) for k, v in evolution_data["summary"].items()}
        return EvolutionResponse(tracked_concepts=evolution_data["tracked_concepts"], timeline=timeline, summary=summary)
    except Exception as e:
        error_msg = f"Evolution API error: {e}\n{traceback.format_exc()}"
        print(error_msg)
        raise


# ============================================================
# 4. 概念查询
# ============================================================

# ============================================================
# 2.5 概念列表（分页）
# ============================================================
@router.get(
    "/concepts",
    tags=["概念"],
    summary="获取概念列表（分页，按权重排列）",
)
def list_concepts(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: str | None = Query(None, description="搜索关键词"),
    repo: Any = Depends(get_repo),
) -> dict:
    """返回所有概念的频次排序列表（支持分页和搜索）。"""
    import json
    from collections import Counter

    conn = repo.db.get_connection()

    # 从 analysis_results 的 concepts 字段聚合
    rows = conn.execute("SELECT concepts FROM analysis_results WHERE concepts IS NOT NULL AND concepts != ''").fetchall()

    # 统计所有概念频率
    all_concepts: Counter[str] = Counter()
    for row in rows:
        try:
            concepts_list = json.loads(row["concepts"])
            if isinstance(concepts_list, list):
                all_concepts.update(concepts_list)
        except (json.JSONDecodeError, TypeError):
            continue

    # 排序（按频率降序）
    sorted_concepts = sorted(all_concepts.items(), key=lambda x: x[1], reverse=True)

    # 搜索过滤
    if search and search.strip():
        keyword = search.strip().lower()
        sorted_concepts = [(c, f) for c, f in sorted_concepts if keyword in c.lower()]

    total = len(sorted_concepts)

    # 分页
    start = (page - 1) * page_size
    end = start + page_size
    items = [
        {"concept": c, "frequency": f}
        for c, f in sorted_concepts[start:end]
    ]

    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get(
    "/concepts/top",
    response_model=list[ConceptFrequencyItem],
    tags=["概念"],
    summary="获取 Top N 概念频次",
)
def get_top_concepts(
    n: int = Query(50, ge=1, le=200, description="返回前 N 个概念"),
    repo: Any = Depends(get_repo),
) -> list[ConceptFrequencyItem]:
    """返回频次最高的 N 个概念。"""
    from src.analyzer.concepts import ConceptProcessor

    proc = ConceptProcessor(repo)
    return [ConceptFrequencyItem(concept=c, frequency=f) for c, f in proc.get_top_concepts(n)]


@router.get(
    "/concepts/search",
    response_model=ConceptSearchResponse,
    tags=["概念"],
    summary="搜索概念",
)
def search_concepts(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="最多返回结果数"),
    repo: Any = Depends(get_repo),
) -> ConceptSearchResponse:
    """从 concept_relations 表搜索概念（模糊匹配）。"""
    conn = repo.db.get_connection()
    rows = conn.execute(
        "SELECT DISTINCT concept_a FROM concept_relations WHERE concept_a LIKE ? LIMIT ?",
        (f"%{q}%", limit),
    ).fetchall()
    results = [row["concept_a"] for row in rows]
    if len(results) < limit:
        rows2 = conn.execute(
            "SELECT DISTINCT concept_b FROM concept_relations WHERE concept_b LIKE ? LIMIT ?",
            (f"%{q}%", limit),
        ).fetchall()
        for row in rows2:
            if row["concept_b"] not in results:
                results.append(row["concept_b"])
                if len(results) >= limit:
                    break
    return ConceptSearchResponse(query=q, results=results[:limit], total=len(results))


@router.get(
    "/concepts/{concept}/relations",
    response_model=list[ConceptRelationItem],
    tags=["概念"],
    summary="获取指定概念的关联关系",
)
def get_concept_relations(
    concept: str,
    limit: int = Query(50, ge=1, le=200, description="最多返回关系数"),
    repo: Any = Depends(get_repo),
) -> list[ConceptRelationItem]:
    """返回与指定概念共现的所有其他概念及权重。"""
    relations = repo.get_concept_relations_by_concept(concept, limit)
    return [ConceptRelationItem(related_concept=r["related_concept"], weight=r["weight"]) for r in relations]


@router.get(
    "/concepts/standardize",
    response_model=StandardizeResponse,
    tags=["概念"],
    summary="标准化概念",
)
def standardize_concept(
    q: str = Query(..., min_length=1, description="待标准化概念"),
    standardizer: Any = Depends(get_standardizer),
) -> StandardizeResponse:
    """调用 StandardizerPipeline 标准化概念。"""
    result = standardizer.standardize([q])
    return StandardizeResponse(query=q, standardized=result)


# ============================================================
# 5. 跨理论体系
# ============================================================
@router.get(
    "/cross-theory",
    response_model=CrossTheoryResponse,
    tags=["理论体系"],
    summary="获取跨理论体系对比数据",
)
def get_cross_theory(repo: Any = Depends(get_repo)) -> CrossTheoryResponse:
    """返回各理论体系的支柱分布、核心概念等对比数据（纯数据库聚合）。"""
    import json
    from collections import Counter
    
    conn = repo.db.get_connection()
    
    # 1. 获取所有理论体系
    systems_rows = conn.execute("SELECT * FROM theory_systems").fetchall()
    
    # 2. 获取所有分析结果的 theory_pillars 和 concepts
    analysis_rows = conn.execute(
        "SELECT article_id, theory_pillars, concepts FROM analysis_results WHERE theory_pillars IS NOT NULL AND theory_pillars != ''"
    ).fetchall()
    
    result_systems = []
    all_concepts_counter = Counter()
    
    for sys_row in systems_rows:
        sys_name = sys_row["system_name"]
        pillars_raw = sys_row["pillars"]
        pillars = json.loads(pillars_raw) if pillars_raw else []
        pillar_set = set(pillars)
        
        # 找属于该体系的文章
        sys_article_ids = set()
        sys_concepts = []
        pillar_dist = Counter()
        
        for arow in analysis_rows:
            try:
                row_pillars = set(json.loads(arow["theory_pillars"]))
            except Exception:
                continue
            # 如果该体系的支柱与文章的支柱有交集
            if row_pillars & pillar_set:
                sys_article_ids.add(arow["article_id"])
                pillar_dist.update(row_pillars)
                try:
                    sys_concepts.extend(json.loads(arow["concepts"]))
                except Exception:
                    pass
        
        # Top 10 概念
        top_concepts = [{"concept": c, "count": n} for c, n in Counter(sys_concepts).most_common(10)]
        
        # unique_concepts: 该体系文章中出现频率 > 0 的概念（取前20）
        unique_concepts = [c for c, n in Counter(sys_concepts).most_common(20)]
        
        all_concepts_counter.update(sys_concepts)
        
        result_systems.append(CrossTheorySystem(
            name=sys_name,
            description=sys_row["description"] or "",
            color_code=sys_row["color_code"] or "#999",
            pillars=pillars,
            pillar_distribution=dict(pillar_dist),
            total_articles=len(sys_article_ids),
            top_concepts=top_concepts,
            unique_concepts=unique_concepts,
        ))
    
    # 共享概念：出现在多个体系中的概念
    # 简化：返回出现频次最高的概念（跨体系）
    shared = []
    concept_sys_count = Counter()
    for sys_row in systems_rows:
        pillars_raw = sys_row["pillars"]
        pillars = json.loads(pillars_raw) if pillars_raw else []
        pillar_set = set(pillars)
        sys_concepts_set = set()
        for arow in analysis_rows:
            try:
                row_pillars = set(json.loads(arow["theory_pillars"]))
                if row_pillars & pillar_set:
                    sys_concepts_set.update(json.loads(arow["concepts"]))
            except Exception:
                continue
        for c in list(sys_concepts_set)[:10]:
            concept_sys_count[c] += 1
    
    shared = [c for c, cnt in concept_sys_count.items() if cnt >= 2]
    
    return CrossTheoryResponse(
        systems=result_systems,
        shared_concepts=shared[:10],
        all_concepts_count=len(all_concepts_counter),
    )


@router.get(
    "/theory-systems",
    response_model=list[TheorySystemInfo],
    tags=["理论体系"],
    summary="获取所有理论体系",
)
def get_theory_systems(repo: Any = Depends(get_repo)) -> list[TheorySystemInfo]:
    """返回所有预定义理论体系。"""
    systems = repo.get_all_theory_systems()
    return [TheorySystemInfo(**s) for s in systems]


# ============================================================
# 6. 文章
# ============================================================
@router.get(
    "/articles",
    response_model=ArticleListResponse,
    tags=["文章"],
    summary="获取文章列表（分页）",
)
def list_articles(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: str | None = Query(None, description="过滤采集状态"),
    repo: Any = Depends(get_repo),
) -> ArticleListResponse:
    """分页返回文章列表，可按采集状态过滤。"""
    all_articles = repo.get_all_articles()
    # 批量查询已分析文章ID（高效方式）
    conn = repo.db.get_connection()
    analyzed_rows = conn.execute("SELECT DISTINCT article_id FROM analysis_results").fetchall()
    analyzed_ids = {row["article_id"] for row in analyzed_rows}
    if status:
        all_articles = [a for a in all_articles if a.crawl_status == status]
    total = len(all_articles)
    start = (page - 1) * page_size
    end = start + page_size
    items = all_articles[start:end]
    return ArticleListResponse(
        total=total,
        page=page,
        page_size=page_size,
        articles=[ArticleSummary(
            id=a.id, title=a.title, url=a.url,
            publish_time=a.publish_time,
            crawl_status=a.crawl_status,
            has_analysis=a.id in analyzed_ids,
        ) for a in items],
    )


@router.get(
    "/articles/{article_id}",
    response_model=ArticleDetail,
    tags=["文章"],
    summary="获取文章详情",
)
def get_article_detail(
    article_id: int,
    repo: Any = Depends(get_repo),
) -> ArticleDetail:
    """返回单篇文章详情及分析结果。"""
    article = repo.get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail=f"文章 ID={article_id} 不存在")
    analysis = repo.get_analysis_result(article_id)
    analysis_dict = None
    if analysis:
        analysis_dict = {
            "concepts": analysis.concepts,
            "keywords": analysis.keywords,
            "theory_pillars": analysis.theory_pillars,
            "summary": analysis.summary,
            "tomas_agi_related": analysis.tomas_agi_related,
            "taiji_os_related": analysis.taiji_os_related,
        }
    return ArticleDetail(
        id=article.id,
        title=article.title,
        url=article.url,
        publish_time=article.publish_time,
        cover_image_url=article.cover_image_url,
        crawl_status=article.crawl_status,
        crawl_time=article.crawl_time,
        content_text=article.content_text,
        analysis=analysis_dict,
    )


@router.get(
    "/articles/search",
    response_model=ArticleSearchResponse,
    tags=["文章"],
    summary="搜索文章标题",
)
def search_articles(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="最多返回结果数"),
    repo: Any = Depends(get_repo),
) -> ArticleSearchResponse:
    """按标题模糊搜索文章。"""
    results = repo.search_articles(q, limit)
    return ArticleSearchResponse(
        query=q,
        total=len(results),
        articles=[ArticleSummary(**a) for a in results],
    )


# ============================================================
# 7. 同义词、增量日志、多模型
# ============================================================
@router.get(
    "/synonyms",
    response_model=list[SynonymMapItem],
    tags=["同义词"],
    summary="获取所有同义词映射",
)
def get_synonyms(repo: Any = Depends(get_repo)) -> list[SynonymMapItem]:
    """返回所有同义词映射。"""
    return [SynonymMapItem(**m) for m in repo.get_all_synonym_maps()]


@router.get(
    "/incremental/log",
    response_model=IncrementalLogItem | None,
    tags=["增量分析"],
    summary="获取最近增量分析日志",
)
def get_incremental_log(repo: Any = Depends(get_repo)) -> IncrementalLogItem | None:
    """返回最近一次增量分析日志。"""
    log = repo.get_last_incremental_log()
    return IncrementalLogItem(**log) if log else None


@router.get(
    "/multi-model/stats",
    response_model=MultiModelStats,
    tags=["多模型"],
    summary="获取多模型验证统计",
)
def get_multi_model_stats(repo: Any = Depends(get_repo)) -> MultiModelStats:
    """返回多模型交叉验证统计信息。"""
    stats = repo.get_cross_model_stats()
    return MultiModelStats(**stats)


# ============================================================
# 8. 理论支柱分布
# ============================================================
@router.get(
    "/pillars/distribution",
    response_model=list[TheoryPillarDistribution],
    tags=["支柱"],
    summary="获取理论支柱分布",
)
def get_pillar_distribution(repo: Any = Depends(get_repo)) -> list[TheoryPillarDistribution]:
    """返回各理论支柱的文章数分布（数组格式）。"""
    from src.analyzer.concepts import ConceptProcessor

    proc = ConceptProcessor(repo)
    dist_dict = proc.get_pillar_distribution()
    return [TheoryPillarDistribution(pillar=p, count=c) for p, c in dist_dict.items()]
