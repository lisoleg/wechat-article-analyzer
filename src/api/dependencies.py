"""FastAPI 依赖注入——管理 Database / Repository 等单例生命周期。"""

from __future__ import annotations

from functools import lru_cache

from src.database import Database, ArticleRepository
from src.analyzer.concepts import ConceptProcessor
from src.report.concept_graph import ConceptGraphBuilder
from src.report.evolution_tracker import EvolutionTracker
from src.standardizer.standardizer_pipeline import StandardizerPipeline

# 全局状态
_db: Database | None = None
_db_path: str = "data/articles.db"


def init_db(path: str = "data/articles.db") -> None:
    """初始化数据库（全局单例）。"""
    global _db, _db_path
    _db_path = path
    _db = Database(path)
    _db.init()


def get_db() -> Database:
    """获取 Database 单例。"""
    global _db
    if _db is None:
        init_db(_db_path)
    return _db


def get_repo() -> ArticleRepository:
    """获取 ArticleRepository 实例（每次返回新实例，共享同一 Database）。"""
    return ArticleRepository(get_db())


@lru_cache
def _get_concept_proc() -> ConceptProcessor:
    return ConceptProcessor(get_repo())


@lru_cache
def get_graph_builder() -> ConceptGraphBuilder:
    return ConceptGraphBuilder(_get_concept_proc())


def get_evolution_tracker() -> EvolutionTracker:
    """获取 EvolutionTracker 实例（每次返回新实例）。"""
    return EvolutionTracker(get_repo(), _get_concept_proc())


@lru_cache
def get_standardizer() -> StandardizerPipeline:
    return StandardizerPipeline(get_repo())
