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

from src.models import Article, AnalysisResult


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
        """插入或更新文章（基于 URL 去重），返回文章 ID。

        Args:
            article: 文章对象。

        Returns:
            文章 ID（新插入的自增 ID 或已存在记录的 ID）。
        """
        conn = self.db.get_connection()
        now = datetime.now().isoformat()

        # 先查询是否已存在
        existing = conn.execute(
            "SELECT id FROM articles WHERE url = ?",
            (article.url,),
        ).fetchone()

        if existing:
            article_id = existing["id"]
            conn.execute(
                """
                UPDATE articles SET
                    title = ?,
                    publish_time = COALESCE(?, publish_time),
                    updated_at = ?
                WHERE id = ?
                """,
                (article.title, article.publish_time, now, article_id),
            )
            conn.commit()
            article.id = article_id
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
