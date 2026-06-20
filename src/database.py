"""数据库管理模块 — Database 类与 ArticleRepository 类。

Database 负责 SQLite 连接管理和表初始化（DDL）。
ArticleRepository 封装所有数据库操作，上层模块禁止直接执行 SQL。

JSON 字段（concepts / keywords / theory_pillars）存储为 JSON 字符串，
读取时通过 json.loads() 反序列化。
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from loguru import logger
from src.models import Article, AnalysisResult, SynonymMap, CrossModelResult, TheorySystem, IncrementalLog


# ============================================================
# SQLite DDL — 严格按架构文档 3.1 节
# ============================================================
_DDL_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS articles (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        title           TEXT NOT NULL,
        url             TEXT UNIQUE NOT NULL,
        publish_time    TEXT,
        cover_image_url TEXT,
        content_html    TEXT,
        content_text    TEXT,
        crawl_status    TEXT DEFAULT 'pending'
                        CHECK(crawl_status IN ('pending','in_progress','complete','failed')),
        crawl_time      TEXT,
        crawl_error     TEXT,
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS analysis_results (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id          INTEGER NOT NULL,
        concepts            TEXT,
        keywords            TEXT,
        theory_pillars      TEXT,
        summary             TEXT,
        tomas_agi_related   INTEGER DEFAULT 0,
        taiji_os_related    INTEGER DEFAULT 0,
        analysis_status     TEXT DEFAULT 'pending'
                            CHECK(analysis_status IN ('pending','in_progress','complete','failed')),
        analysis_time       TEXT,
        analysis_error      TEXT,
        created_at          TEXT DEFAULT (datetime('now')),
        updated_at          TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (article_id) REFERENCES articles(id),
        UNIQUE(article_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS concept_relations (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        concept_a           TEXT NOT NULL,
        concept_b           TEXT NOT NULL,
        co_occurrence_count INTEGER DEFAULT 0,
        UNIQUE(concept_a, concept_b),
        CHECK(concept_a < concept_b)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_articles_crawl_status ON articles(crawl_status)",
    "CREATE INDEX IF NOT EXISTS idx_articles_publish_time ON articles(publish_time)",
    "CREATE INDEX IF NOT EXISTS idx_analysis_status ON analysis_results(analysis_status)",
    "CREATE INDEX IF NOT EXISTS idx_analysis_article_id ON analysis_results(article_id)",
    "CREATE INDEX IF NOT EXISTS idx_concept_relations_count ON concept_relations(co_occurrence_count DESC)",
    # --- v2.0 新增表 ---
    """
    CREATE TABLE IF NOT EXISTS synonym_maps (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        original_concept    TEXT NOT NULL,
        standardized_concept TEXT NOT NULL,
        mapping_type        TEXT DEFAULT 'manual'
                            CHECK(mapping_type IN ('manual','auto_clustered')),
        confidence          REAL DEFAULT 1.0,
        created_at          TEXT DEFAULT (datetime('now')),
        updated_at          TEXT DEFAULT (datetime('now')),
        UNIQUE(original_concept)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cross_model_results (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id          INTEGER NOT NULL,
        model_name          TEXT NOT NULL,
        concepts            TEXT,
        keywords            TEXT,
        theory_pillars      TEXT,
        summary             TEXT,
        consistency_score   REAL,
        created_at          TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (article_id) REFERENCES articles(id),
        UNIQUE(article_id, model_name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS theory_systems (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        system_name         TEXT UNIQUE NOT NULL,
        description         TEXT,
        pillars             TEXT,
        color_code          TEXT DEFAULT '#000000',
        created_at          TEXT DEFAULT (datetime('now')),
        updated_at          TEXT DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS incremental_logs (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        last_article_id     INTEGER,
        last_analysis_time  TEXT,
        new_articles_count  INTEGER DEFAULT 0,
        new_concepts_count  INTEGER DEFAULT 0,
        executed_at         TEXT DEFAULT (datetime('now'))
    )
    """,
    # 新索引
    "CREATE INDEX IF NOT EXISTS idx_synonym_original ON synonym_maps(original_concept)",
    "CREATE INDEX IF NOT EXISTS idx_synonym_standard ON synonym_maps(standardized_concept)",
    "CREATE INDEX IF NOT EXISTS idx_cross_model_article ON cross_model_results(article_id)",
    "CREATE INDEX IF NOT EXISTS idx_cross_model_model ON cross_model_results(model_name)",
    "CREATE INDEX IF NOT EXISTS idx_theory_system_name ON theory_systems(system_name)",
]


class Database:
    """SQLite 连接管理与表初始化。

    持有单例连接，使用 check_same_thread=False 支持跨线程访问。
    每次写操作自动 commit。
    """

    def __init__(self, db_path: str = "./data/articles.db") -> None:
        """初始化数据库管理器。

        Args:
            db_path: SQLite 数据库文件路径。
        """
        self.db_path: str = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def init(self) -> None:
        """初始化数据库：创建目录、建立连接、执行 DDL 建表。"""
        # 确保数据目录存在
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)

        # 建立连接
        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

        # 执行 DDL
        for statement in _DDL_STATEMENTS:
            self._conn.executescript(statement)
        self._conn.commit()

    def get_connection(self) -> sqlite3.Connection:
        """获取当前数据库连接。

        Returns:
            sqlite3.Connection 实例。

        Raises:
            RuntimeError: 数据库未初始化。
        """
        if self._conn is None:
            self.init()
        assert self._conn is not None  # for type checker
        return self._conn

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行 SQL 语句并自动提交。

        Args:
            sql: SQL 语句。
            params: 参数元组。

        Returns:
            游标对象。
        """
        conn = self.get_connection()
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor

    def close(self) -> None:
        """关闭数据库连接。"""
        if self._conn is not None:
            self._conn.close()
            self._conn = None


class ArticleRepository:
    """数据访问层 — 封装所有数据库操作。

    所有上层模块通过此类访问数据库，禁止直接执行 SQL。
    """

    def __init__(self, db: Database) -> None:
        """初始化仓库。

        Args:
            db: Database 实例。
        """
        self.db: Database = db

    # ----------------------------------------------------------
    # 文章 CRUD
    # ----------------------------------------------------------
    def upsert_article(self, article: Article) -> int:
        """插入或更新文章（基于 URL 或 title+publish_time 去重），返回文章 ID。

        WeChat 文章列表 API 返回的 content_url 含临时 tempkey，
        每次采集都会变化。因此去重逻辑分两步：
          1. 先按 URL 精确匹配；
          2. 未匹配时再按 title + publish_time 稳定匹配，
             命中则刷新 URL（tempkey 更新）。

        Args:
            article: 文章对象。

        Returns:
            文章 ID（新插入的自增 ID 或已存在记录的 ID）。
        """
        conn = self.db.get_connection()
        now = datetime.now().isoformat()

        # 第1步：按 URL 查询
        existing = conn.execute(
            "SELECT id FROM articles WHERE url = ?",
            (article.url,),
        ).fetchone()

        # 第2步：URL 未匹配时，按 title + publish_time 查询（tempkey 刷新场景）
        if not existing:
            existing = conn.execute(
                "SELECT id FROM articles WHERE title = ? AND publish_time = ?",
                (article.title, article.publish_time),
            ).fetchone()

        if existing:
            article_id = existing["id"]
            conn.execute(
                """
                UPDATE articles SET
                    title = ?,
                    url = ?,
                    publish_time = COALESCE(?, publish_time),
                    updated_at = ?
                WHERE id = ?
                """,
                (article.title, article.url, article.publish_time, now, article_id),
            )
            conn.commit()
            article.id = article_id
            logger.debug(f"更新文章（含 URL 刷新）: {article.title[:30]}")
            return article_id

        cursor = conn.execute(
            """
            INSERT INTO articles (title, url, publish_time, cover_image_url,
                                  content_html, content_text, crawl_status,
                                  crawl_time, crawl_error, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                article.title,
                article.url,
                article.publish_time,
                article.cover_image_url,
                article.content_html,
                article.content_text,
                article.crawl_status,
                article.crawl_time,
                article.crawl_error,
                now,
                now,
            ),
        )
        conn.commit()
        article.id = cursor.lastrowid
        return article.id  # type: ignore[return-value]

    def get_article(self, article_id: int) -> Optional[Article]:
        """根据 ID 获取文章。

        Args:
            article_id: 文章 ID。

        Returns:
            文章对象，不存在时返回 None。
        """
        row = self.db.get_connection().execute(
            "SELECT * FROM articles WHERE id = ?",
            (article_id,),
        ).fetchone()
        return self._row_to_article(row) if row else None

    def get_article_by_url(self, url: str) -> Optional[Article]:
        """根据 URL 获取文章。

        Args:
            url: 文章 URL。

        Returns:
            文章对象，不存在时返回 None。
        """
        row = self.db.get_connection().execute(
            "SELECT * FROM articles WHERE url = ?",
            (url,),
        ).fetchone()
        return self._row_to_article(row) if row else None

    def get_article_by_title_and_time(
        self, title: str, publish_time: Optional[str]
    ) -> Optional[Article]:
        """根据标题（+ 发布时间）获取文章。

        publish_time 为 None 时回退到按 title 唯一匹配。

        Args:
            title: 文章标题。
            publish_time: 发布时间（ISO 格式字符串），为 None 时不参与匹配。

        Returns:
            文章对象，不存在时返回 None。
        """
        if publish_time:
            row = self.db.get_connection().execute(
                "SELECT * FROM articles WHERE title = ? AND publish_time = ?",
                (title, publish_time),
            ).fetchone()
        else:
            # publish_time 为空时按 title 唯一匹配
            row = self.db.get_connection().execute(
                "SELECT * FROM articles WHERE title = ? ORDER BY id LIMIT 1",
                (title,),
            ).fetchone()
        return self._row_to_article(row) if row else None

    def get_article_by_title(self, title: str) -> Optional[Article]:
        """根据标题获取文章（title 唯一）。

        Args:
            title: 文章标题。

        Returns:
            文章对象，不存在时返回 None。
        """
        row = self.db.get_connection().execute(
            "SELECT * FROM articles WHERE title = ? ORDER BY id LIMIT 1",
            (title,),
        ).fetchone()
        return self._row_to_article(row) if row else None

    def update_url(self, article_id: int, new_url: str) -> None:
        """更新文章 URL（用于 tempkey 刷新场景）。

        Args:
            article_id: 文章 ID。
            new_url: 新的文章 URL。
        """
        conn = self.db.get_connection()
        conn.execute(
            "UPDATE articles SET url = ?, updated_at = ? WHERE id = ?",
            (new_url, datetime.now().isoformat(), article_id),
        )
        conn.commit()

    def get_articles_by_crawl_status(self, status: str) -> list[Article]:
        """获取指定采集状态的文章列表。

        Args:
            status: 采集状态 — pending / in_progress / complete / failed。

        Returns:
            文章列表。
        """
        rows = self.db.get_connection().execute(
            "SELECT * FROM articles WHERE crawl_status = ? ORDER BY id",
            (status,),
        ).fetchall()
        return [self._row_to_article(row) for row in rows]

    def get_articles_by_analysis_status(self, status: str) -> list[Article]:
        """获取指定分析状态的文章列表（LEFT JOIN analysis_results）。

        当 status='pending' 时返回尚无分析结果或分析状态为 pending 的文章。
        当 status='complete' 时返回分析完成的文章。

        Args:
            status: 分析状态。

        Returns:
            文章列表。
        """
        if status == "pending":
            rows = self.db.get_connection().execute(
                """
                SELECT a.* FROM articles a
                LEFT JOIN analysis_results ar ON a.id = ar.article_id
                WHERE ar.analysis_status IS NULL
                   OR ar.analysis_status = 'pending'
                ORDER BY a.id
                """,
            ).fetchall()
        else:
            rows = self.db.get_connection().execute(
                """
                SELECT a.* FROM articles a
                INNER JOIN analysis_results ar ON a.id = ar.article_id
                WHERE ar.analysis_status = ?
                ORDER BY a.id
                """,
                (status,),
            ).fetchall()
        return [self._row_to_article(row) for row in rows]

    def get_all_articles(self) -> list[Article]:
        """获取所有文章列表。

        Returns:
            全部文章列表，按 ID 排序。
        """
        rows = self.db.get_connection().execute(
            "SELECT * FROM articles ORDER BY id",
        ).fetchall()
        return [self._row_to_article(row) for row in rows]

    def search_articles(self, query: str, limit: int = 20) -> list[dict]:
        """搜索文章标题，支持模糊匹配。

        Args:
            query: 搜索关键词。
            limit: 最多返回结果数。

        Returns:
            文章摘要字典列表。
        """
        conn = self.db.get_connection()
        rows = conn.execute(
            "SELECT id, title, url, publish_time, crawl_status FROM articles "
            "WHERE title LIKE ? ORDER BY publish_time DESC LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_crawl_status(
        self, article_id: int, status: str, error: Optional[str] = None
    ) -> None:
        """更新文章采集状态。

        Args:
            article_id: 文章 ID。
            status: 新状态。
            error: 采集错误信息（可选）。
        """
        now = datetime.now().isoformat()
        crawl_time = now if status == "complete" else None
        self.db.execute(
            """
            UPDATE articles SET
                crawl_status = ?,
                crawl_error = ?,
                crawl_time = COALESCE(?, crawl_time),
                updated_at = ?
            WHERE id = ?
            """,
            (status, error, crawl_time, now, article_id),
        )

    def update_content(
        self,
        article_id: int,
        html: str,
        text: str,
        cover_url: Optional[str] = None,
    ) -> None:
        """更新文章正文内容。

        Args:
            article_id: 文章 ID。
            html: 正文 HTML。
            text: 正文纯文本。
            cover_url: 封面图 URL（可选）。
        """
        now = datetime.now().isoformat()
        self.db.execute(
            """
            UPDATE articles SET
                content_html = ?,
                content_text = ?,
                cover_image_url = COALESCE(?, cover_image_url),
                updated_at = ?
            WHERE id = ?
            """,
            (html, text, cover_url, now, article_id),
        )

    # ----------------------------------------------------------
    # 分析结果 CRUD
    # ----------------------------------------------------------
    def save_analysis_result(self, result: AnalysisResult) -> None:
        """保存分析结果（UPSERT by article_id）。

        Args:
            result: 分析结果对象。
        """
        conn = self.db.get_connection()
        now = datetime.now().isoformat()

        concepts_json = json.dumps(result.concepts, ensure_ascii=False)
        keywords_json = json.dumps(result.keywords, ensure_ascii=False)
        pillars_json = json.dumps(result.theory_pillars, ensure_ascii=False)
        tomas_val = 1 if result.tomas_agi_related else 0
        taiji_val = 1 if result.taiji_os_related else 0

        existing = conn.execute(
            "SELECT id FROM analysis_results WHERE article_id = ?",
            (result.article_id,),
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE analysis_results SET
                    concepts = ?,
                    keywords = ?,
                    theory_pillars = ?,
                    summary = ?,
                    tomas_agi_related = ?,
                    taiji_os_related = ?,
                    analysis_status = ?,
                    analysis_time = ?,
                    analysis_error = ?,
                    updated_at = ?
                WHERE article_id = ?
                """,
                (
                    concepts_json,
                    keywords_json,
                    pillars_json,
                    result.summary,
                    tomas_val,
                    taiji_val,
                    result.analysis_status,
                    now,
                    result.analysis_error,
                    now,
                    result.article_id,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO analysis_results (
                    article_id, concepts, keywords, theory_pillars,
                    summary, tomas_agi_related, taiji_os_related,
                    analysis_status, analysis_time, analysis_error,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.article_id,
                    concepts_json,
                    keywords_json,
                    pillars_json,
                    result.summary,
                    tomas_val,
                    taiji_val,
                    result.analysis_status,
                    now,
                    result.analysis_error,
                    now,
                    now,
                ),
            )
        conn.commit()

    def get_analysis_result(self, article_id: int) -> Optional[AnalysisResult]:
        """获取指定文章的分析结果。

        Args:
            article_id: 文章 ID。

        Returns:
            分析结果对象，不存在时返回 None。
        """
        row = self.db.get_connection().execute(
            "SELECT * FROM analysis_results WHERE article_id = ?",
            (article_id,),
        ).fetchone()
        return self._row_to_analysis_result(row) if row else None

    def get_all_analysis_results(self) -> list[AnalysisResult]:
        """获取所有已完成的分析结果。

        Returns:
            分析结果列表（analysis_status='complete'）。
        """
        rows = self.db.get_connection().execute(
            "SELECT * FROM analysis_results WHERE analysis_status = 'complete' ORDER BY article_id",
        ).fetchall()
        return [self._row_to_analysis_result(row) for row in rows]

    # ----------------------------------------------------------
    # 统计信息
    # ----------------------------------------------------------
    def get_stats(self) -> dict[str, Any]:
        """返回统计信息。

        Returns:
            包含 total / crawled / crawl_failed / analyzed / analyze_failed
            等统计项的字典。
        """
        conn = self.db.get_connection()

        total = conn.execute("SELECT COUNT(*) as c FROM articles").fetchone()["c"]
        crawled = conn.execute(
            "SELECT COUNT(*) as c FROM articles WHERE crawl_status = 'complete'"
        ).fetchone()["c"]
        crawl_pending = conn.execute(
            "SELECT COUNT(*) as c FROM articles WHERE crawl_status = 'pending'"
        ).fetchone()["c"]
        crawl_failed = conn.execute(
            "SELECT COUNT(*) as c FROM articles WHERE crawl_status = 'failed'"
        ).fetchone()["c"]
        analyzed = conn.execute(
            "SELECT COUNT(*) as c FROM analysis_results WHERE analysis_status = 'complete'"
        ).fetchone()["c"]
        analyze_failed = conn.execute(
            "SELECT COUNT(*) as c FROM analysis_results WHERE analysis_status = 'failed'"
        ).fetchone()["c"]

        return {
            "total": total,
            "crawled": crawled,
            "crawl_pending": crawl_pending,
            "crawl_failed": crawl_failed,
            "analyzed": analyzed,
            "analyze_failed": analyze_failed,
        }

    # ----------------------------------------------------------
    # 概念关系
    # ----------------------------------------------------------
    def save_concept_relation(
        self, concept_a: str, concept_b: str, count: int
    ) -> None:
        """保存概念共现关系（UPSERT）。

        保证 concept_a < concept_b（按字典序），满足 CHECK 约束。

        Args:
            concept_a: 概念 A。
            concept_b: 概念 B。
            count: 共现次数。
        """
        # 保证有序
        a, b = sorted([concept_a, concept_b])
        self.db.execute(
            """
            INSERT INTO concept_relations (concept_a, concept_b, co_occurrence_count)
            VALUES (?, ?, ?)
            ON CONFLICT(concept_a, concept_b)
            DO UPDATE SET co_occurrence_count = ?
            """,
            (a, b, count, count),
        )

    def get_concept_relations_count(self) -> int:
        """返回 concept_relations 表的总行数。"""
        return self.db.get_connection().execute(
            "SELECT COUNT(*) FROM concept_relations"
        ).fetchone()[0]

    def get_concept_relations(self, top_n: int = 50) -> list[dict[str, Any]]:
        """获取共现次数 Top N 的概念关系。

        Args:
            top_n: 返回前 N 条关系。

        Returns:
            关系列表，每项包含 concept_a / concept_b / co_occurrence_count。
        """
        rows = self.db.get_connection().execute(
            """
            SELECT concept_a, concept_b, co_occurrence_count
            FROM concept_relations
            ORDER BY co_occurrence_count DESC
            LIMIT ?
            """,
            (top_n,),
        ).fetchall()
        return [
            {
                "concept_a": row["concept_a"],
                "concept_b": row["concept_b"],
                "co_occurrence_count": row["co_occurrence_count"],
            }
            for row in rows
        ]

    def get_concept_relations_by_concept(
        self, concept: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """获取与指定概念相关的所有共现关系。

        Args:
            concept: 概念名称。
            limit: 最多返回关系数。

        Returns:
            关系列表，每项包含 related_concept / weight。
        """
        conn = self.db.get_connection()
        rows = conn.execute(
            "SELECT concept_a, concept_b, co_occurrence_count FROM concept_relations "
            "WHERE concept_a = ? OR concept_b = ? ORDER BY co_occurrence_count DESC LIMIT ?",
            (concept, concept, limit),
        ).fetchall()
        results = []
        for r in rows:
            related = r["concept_b"] if r["concept_a"] == concept else r["concept_a"]
            results.append({"related_concept": related, "weight": r["co_occurrence_count"]})
        return results

    # ----------------------------------------------------------
    # 行到对象转换（私有）
    # ----------------------------------------------------------
    @staticmethod
    def _row_to_article(row: sqlite3.Row) -> Article:
        """将数据库行转换为 Article 对象。"""
        return Article(
            id=row["id"],
            title=row["title"],
            url=row["url"],
            publish_time=row["publish_time"],
            cover_image_url=row["cover_image_url"],
            content_html=row["content_html"],
            content_text=row["content_text"],
            crawl_status=row["crawl_status"],
            crawl_time=row["crawl_time"],
            crawl_error=row["crawl_error"],
        )

    @staticmethod
    def _row_to_analysis_result(row: sqlite3.Row) -> AnalysisResult:
        """将数据库行转换为 AnalysisResult 对象。"""
        concepts: list[str] = (
            json.loads(row["concepts"]) if row["concepts"] else []
        )
        keywords: list[str] = (
            json.loads(row["keywords"]) if row["keywords"] else []
        )
        pillars: list[str] = (
            json.loads(row["theory_pillars"]) if row["theory_pillars"] else []
        )
        return AnalysisResult(
            id=row["id"],
            article_id=row["article_id"],
            concepts=concepts,
            keywords=keywords,
            theory_pillars=pillars,
            summary=row["summary"],
            tomas_agi_related=bool(row["tomas_agi_related"]),
            taiji_os_related=bool(row["taiji_os_related"]),
            analysis_status=row["analysis_status"],
            analysis_time=row["analysis_time"],
            analysis_error=row["analysis_error"],
        )

    # ----------------------------------------------------------
    # 同义词映射 CRUD（v2.0）
    # ----------------------------------------------------------
    def upsert_synonym_map(
        self,
        original: str,
        standardized: str,
        mapping_type: str = "manual",
        confidence: float = 1.0,
    ) -> int:
        """插入或更新同义词映射（UPSERT by original_concept）。

        Args:
            original: 原始概念名。
            standardized: 标准化概念名。
            mapping_type: 映射类型 — manual / auto_clustered。
            confidence: 置信度（0.0–1.0）。

        Returns:
            记录 ID。
        """
        conn = self.db.get_connection()
        now = datetime.now().isoformat()
        cursor = conn.execute(
            """
            INSERT INTO synonym_maps (original_concept, standardized_concept,
                                      mapping_type, confidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(original_concept)
            DO UPDATE SET
                standardized_concept = excluded.standardized_concept,
                mapping_type = excluded.mapping_type,
                confidence = excluded.confidence,
                updated_at = excluded.updated_at
            """,
            (original, standardized, mapping_type, confidence, now, now),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def get_synonym_map(self, original: str) -> Optional[dict]:
        """查询单个同义词映射。

        Args:
            original: 原始概念名。

        Returns:
            映射字典（含 id / original_concept / standardized_concept /
            mapping_type / confidence / created_at / updated_at），不存在时返回 None。
        """
        row = self.db.get_connection().execute(
            "SELECT * FROM synonym_maps WHERE original_concept = ?",
            (original,),
        ).fetchone()
        return dict(row) if row else None

    def get_all_synonym_maps(self) -> list[dict]:
        """获取所有同义词映射。

        Returns:
            映射字典列表，按 original_concept 排序。
        """
        rows = self.db.get_connection().execute(
            "SELECT * FROM synonym_maps ORDER BY original_concept",
        ).fetchall()
        return [dict(row) for row in rows]

    def delete_synonym_map(self, id: int) -> bool:
        """删除同义词映射。

        Args:
            id: 记录 ID。

        Returns:
            是否删除成功（受影响行数 > 0）。
        """
        conn = self.db.get_connection()
        cursor = conn.execute(
            "DELETE FROM synonym_maps WHERE id = ?",
            (id,),
        )
        conn.commit()
        return cursor.rowcount > 0

    # ----------------------------------------------------------
    # 多模型验证 CRUD（v2.0）
    # ----------------------------------------------------------
    def save_cross_model_result(
        self,
        article_id: int,
        model_name: str,
        concepts: list,
        keywords: list,
        theory_pillars: list,
        summary: str,
        consistency_score: float,
    ) -> None:
        """保存多模型验证结果（UPSERT by article_id + model_name）。

        Args:
            article_id: 文章 ID。
            model_name: 模型名称。
            concepts: 概念列表。
            keywords: 关键词列表。
            theory_pillars: 理论支柱列表。
            summary: 摘要。
            consistency_score: 一致性分数。
        """
        conn = self.db.get_connection()
        now = datetime.now().isoformat()
        concepts_json = json.dumps(concepts, ensure_ascii=False)
        keywords_json = json.dumps(keywords, ensure_ascii=False)
        pillars_json = json.dumps(theory_pillars, ensure_ascii=False)

        conn.execute(
            """
            INSERT INTO cross_model_results (
                article_id, model_name, concepts, keywords,
                theory_pillars, summary, consistency_score, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(article_id, model_name)
            DO UPDATE SET
                concepts = excluded.concepts,
                keywords = excluded.keywords,
                theory_pillars = excluded.theory_pillars,
                summary = excluded.summary,
                consistency_score = excluded.consistency_score,
                created_at = excluded.created_at
            """,
            (
                article_id,
                model_name,
                concepts_json,
                keywords_json,
                pillars_json,
                summary,
                consistency_score,
                now,
            ),
        )
        conn.commit()

    def get_cross_model_results(self, article_id: int) -> list[dict]:
        """获取某文章的所有模型验证结果。

        Args:
            article_id: 文章 ID。

        Returns:
            模型结果字典列表，按 model_name 排序。JSON 字段已反序列化。
        """
        rows = self.db.get_connection().execute(
            "SELECT * FROM cross_model_results WHERE article_id = ? ORDER BY model_name",
            (article_id,),
        ).fetchall()
        results: list[dict] = []
        for row in rows:
            d = dict(row)
            d["concepts"] = json.loads(d["concepts"]) if d["concepts"] else []
            d["keywords"] = json.loads(d["keywords"]) if d["keywords"] else []
            d["theory_pillars"] = (
                json.loads(d["theory_pillars"]) if d["theory_pillars"] else []
            )
            results.append(d)
        return results

    def get_cross_model_stats(self) -> dict:
        """统计多模型验证情况。

        Returns:
            包含 total_results / total_articles / avg_consistency /
            model_counts 的字典。
        """
        conn = self.db.get_connection()
        total_results = conn.execute(
            "SELECT COUNT(*) as c FROM cross_model_results"
        ).fetchone()["c"]
        total_articles = conn.execute(
            "SELECT COUNT(DISTINCT article_id) as c FROM cross_model_results"
        ).fetchone()["c"]
        avg_row = conn.execute(
            "SELECT AVG(consistency_score) as avg FROM cross_model_results"
        ).fetchone()
        avg_consistency = avg_row["avg"] if avg_row["avg"] is not None else 0.0
        model_rows = conn.execute(
            "SELECT model_name, COUNT(*) as c FROM cross_model_results GROUP BY model_name"
        ).fetchall()
        model_counts = {row["model_name"]: row["c"] for row in model_rows}

        return {
            "total_results": total_results,
            "total_articles": total_articles,
            "avg_consistency": round(avg_consistency, 4),
            "model_counts": model_counts,
        }

    # ----------------------------------------------------------
    # 理论体系 CRUD（v2.0）
    # ----------------------------------------------------------
    def upsert_theory_system(
        self,
        name: str,
        description: str,
        pillars: list,
        color_code: str = "#000000",
    ) -> int:
        """插入或更新理论体系（UPSERT by system_name）。

        Args:
            name: 体系名称。
            description: 描述。
            pillars: 支柱列表。
            color_code: 颜色代码（默认 #000000）。

        Returns:
            记录 ID。
        """
        conn = self.db.get_connection()
        now = datetime.now().isoformat()
        pillars_json = json.dumps(pillars, ensure_ascii=False)
        cursor = conn.execute(
            """
            INSERT INTO theory_systems (system_name, description, pillars,
                                        color_code, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(system_name)
            DO UPDATE SET
                description = excluded.description,
                pillars = excluded.pillars,
                color_code = excluded.color_code,
                updated_at = excluded.updated_at
            """,
            (name, description, pillars_json, color_code, now, now),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def get_all_theory_systems(self) -> list[dict]:
        """获取所有理论体系。

        Returns:
            理论体系字典列表，按 system_name 排序。pillars 字段已反序列化。
        """
        rows = self.db.get_connection().execute(
            "SELECT * FROM theory_systems ORDER BY system_name",
        ).fetchall()
        results: list[dict] = []
        for row in rows:
            d = dict(row)
            d["pillars"] = json.loads(d["pillars"]) if d["pillars"] else []
            results.append(d)
        return results

    def get_theory_system(self, name: str) -> Optional[dict]:
        """按名称查询理论体系。

        Args:
            name: 体系名称。

        Returns:
            理论体系字典（pillars 已反序列化），不存在时返回 None。
        """
        row = self.db.get_connection().execute(
            "SELECT * FROM theory_systems WHERE system_name = ?",
            (name,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["pillars"] = json.loads(d["pillars"]) if d["pillars"] else []
        return d

    def delete_theory_system(self, id: int) -> bool:
        """删除理论体系。

        Args:
            id: 记录 ID。

        Returns:
            是否删除成功（受影响行数 > 0）。
        """
        conn = self.db.get_connection()
        cursor = conn.execute(
            "DELETE FROM theory_systems WHERE id = ?",
            (id,),
        )
        conn.commit()
        return cursor.rowcount > 0

    # ----------------------------------------------------------
    # 增量分析日志（v2.0）
    # ----------------------------------------------------------
    def get_last_incremental_log(self) -> Optional[dict]:
        """获取最近一次增量分析日志。

        Returns:
            日志字典，不存在时返回 None。
        """
        row = self.db.get_connection().execute(
            "SELECT * FROM incremental_logs ORDER BY id DESC LIMIT 1",
        ).fetchone()
        return dict(row) if row else None

    def save_incremental_log(
        self,
        last_article_id: int,
        last_analysis_time: str,
        new_articles_count: int,
        new_concepts_count: int,
    ) -> int:
        """保存增量分析日志。

        Args:
            last_article_id: 最后分析的文章 ID。
            last_analysis_time: 最后分析时间（ISO 8601）。
            new_articles_count: 新增文章数。
            new_concepts_count: 新增概念数。

        Returns:
            日志记录 ID。
        """
        conn = self.db.get_connection()
        now = datetime.now().isoformat()
        cursor = conn.execute(
            """
            INSERT INTO incremental_logs (
                last_article_id, last_analysis_time,
                new_articles_count, new_concepts_count, executed_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (last_article_id, last_analysis_time, new_articles_count, new_concepts_count, now),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def get_articles_after_id(self, last_id: int) -> list[Article]:
        """获取 ID 大于 last_id 且 crawl_status='complete' 的文章。

        Args:
            last_id: 上次增量分析的最后一篇文章 ID。

        Returns:
            文章列表，按 ID 升序排列。
        """
        rows = self.db.get_connection().execute(
            "SELECT * FROM articles WHERE id > ? AND crawl_status = 'complete' ORDER BY id",
            (last_id,),
        ).fetchall()
        return [self._row_to_article(row) for row in rows]
