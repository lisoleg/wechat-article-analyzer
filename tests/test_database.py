"""数据库 CRUD 操作测试。

测试 ArticleRepository 的增删改查功能。
使用临时 SQLite 数据库，测试后自动清理。
"""

import json
import os
import tempfile
from datetime import datetime

import pytest

from src.database import ArticleRepository, Database
from src.models import AnalysisResult, Article


@pytest.fixture
def repo():
    """创建临时数据库和仓库实例。"""
    # 使用临时文件
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    db = Database(db_path=db_path)
    db.init()
    repository = ArticleRepository(db)

    yield repository

    # 清理
    db.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


class TestArticleCRUD:
    """文章 CRUD 测试。"""

    def test_upsert_article_insert(self, repo: ArticleRepository):
        """测试插入新文章。"""
        article = Article(
            title="测试文章",
            url="https://example.com/article/1",
            publish_time="2024-01-15T10:00:00",
            crawl_status="pending",
        )
        article_id = repo.upsert_article(article)

        assert article_id is not None
        assert article_id > 0

        # 验证可读回
        fetched = repo.get_article(article_id)
        assert fetched is not None
        assert fetched.title == "测试文章"
        assert fetched.url == "https://example.com/article/1"

    def test_upsert_article_dedup(self, repo: ArticleRepository):
        """测试 URL 去重（相同 URL 不创建新记录）。"""
        article1 = Article(title="文章1", url="https://example.com/1")
        id1 = repo.upsert_article(article1)

        article2 = Article(title="文章1更新", url="https://example.com/1")
        id2 = repo.upsert_article(article2)

        assert id1 == id2

    def test_get_article_by_url(self, repo: ArticleRepository):
        """测试按 URL 查询。"""
        article = Article(title="URL查询测试", url="https://example.com/url-test")
        repo.upsert_article(article)

        fetched = repo.get_article_by_url("https://example.com/url-test")
        assert fetched is not None
        assert fetched.title == "URL查询测试"

    def test_get_articles_by_crawl_status(self, repo: ArticleRepository):
        """测试按采集状态查询。"""
        for i in range(3):
            repo.upsert_article(
                Article(title=f"待采集{i}", url=f"https://example.com/pending/{i}")
            )
        for i in range(2):
            article = Article(
                title=f"已完成{i}",
                url=f"https://example.com/complete/{i}",
                crawl_status="complete",
            )
            article_id = repo.upsert_article(article)
            repo.update_crawl_status(article_id, "complete")

        pending = repo.get_articles_by_crawl_status("pending")
        complete = repo.get_articles_by_crawl_status("complete")

        assert len(pending) == 3
        assert len(complete) == 2

    def test_update_crawl_status(self, repo: ArticleRepository):
        """测试更新采集状态。"""
        article = Article(title="状态更新测试", url="https://example.com/status")
        article_id = repo.upsert_article(article)

        repo.update_crawl_status(article_id, "complete")
        fetched = repo.get_article(article_id)
        assert fetched is not None
        assert fetched.crawl_status == "complete"
        assert fetched.crawl_time is not None

    def test_update_crawl_status_with_error(self, repo: ArticleRepository):
        """测试采集失败时记录错误。"""
        article = Article(title="失败测试", url="https://example.com/failed")
        article_id = repo.upsert_article(article)

        repo.update_crawl_status(article_id, "failed", "连接超时")
        fetched = repo.get_article(article_id)
        assert fetched is not None
        assert fetched.crawl_status == "failed"
        assert fetched.crawl_error == "连接超时"

    def test_update_content(self, repo: ArticleRepository):
        """测试更新正文内容。"""
        article = Article(title="内容更新", url="https://example.com/content")
        article_id = repo.upsert_article(article)

        repo.update_content(
            article_id,
            html="<p>正文HTML</p>",
            text="正文文本",
            cover_url="https://example.com/cover.jpg",
        )

        fetched = repo.get_article(article_id)
        assert fetched is not None
        assert fetched.content_html == "<p>正文HTML</p>"
        assert fetched.content_text == "正文文本"
        assert fetched.cover_image_url == "https://example.com/cover.jpg"

    def test_get_all_articles(self, repo: ArticleRepository):
        """测试获取全部文章。"""
        for i in range(5):
            repo.upsert_article(
                Article(title=f"文章{i}", url=f"https://example.com/all/{i}")
            )

        all_articles = repo.get_all_articles()
        assert len(all_articles) == 5


class TestAnalysisResultCRUD:
    """分析结果 CRUD 测试。"""

    @pytest.fixture
    def article_id(self, repo: ArticleRepository) -> int:
        """创建一篇文章用于测试。"""
        article = Article(title="分析测试文章", url="https://example.com/analysis")
        return repo.upsert_article(article)

    def test_save_and_get_analysis_result(
        self, repo: ArticleRepository, article_id: int
    ):
        """测试保存和读取分析结果。"""
        result = AnalysisResult(
            article_id=article_id,
            concepts=["概念A", "概念B", "概念C"],
            keywords=["关键词1", "关键词2"],
            theory_pillars=["刘原理", "三视界法"],
            summary="本文探讨了概念之间的关系。",
            tomas_agi_related=False,
            taiji_os_related=True,
            analysis_status="complete",
        )
        repo.save_analysis_result(result)

        fetched = repo.get_analysis_result(article_id)
        assert fetched is not None
        assert fetched.article_id == article_id
        assert fetched.concepts == ["概念A", "概念B", "概念C"]
        assert fetched.keywords == ["关键词1", "关键词2"]
        assert fetched.theory_pillars == ["刘原理", "三视界法"]
        assert fetched.summary == "本文探讨了概念之间的关系。"
        assert fetched.tomas_agi_related is False
        assert fetched.taiji_os_related is True

    def test_save_analysis_result_upsert(
        self, repo: ArticleRepository, article_id: int
    ):
        """测试分析结果 UPSERT（同一文章更新不创建新记录）。"""
        result1 = AnalysisResult(
            article_id=article_id,
            concepts=["概念A"],
            analysis_status="complete",
        )
        repo.save_analysis_result(result1)

        result2 = AnalysisResult(
            article_id=article_id,
            concepts=["概念A", "概念B"],
            analysis_status="complete",
        )
        repo.save_analysis_result(result2)

        all_results = repo.get_all_analysis_results()
        assert len(all_results) == 1
        assert all_results[0].concepts == ["概念A", "概念B"]

    def test_get_all_analysis_results(self, repo: ArticleRepository):
        """测试获取所有已完成的分析结果。"""
        for i in range(3):
            aid = repo.upsert_article(
                Article(title=f"文章{i}", url=f"https://example.com/results/{i}")
            )
            repo.save_analysis_result(
                AnalysisResult(
                    article_id=aid,
                    concepts=[f"概念{i}"],
                    analysis_status="complete",
                )
            )

        # 添加一个未完成的分析
        aid4 = repo.upsert_article(
            Article(title="未完成", url="https://example.com/results/incomplete")
        )
        repo.save_analysis_result(
            AnalysisResult(article_id=aid4, analysis_status="pending")
        )

        results = repo.get_all_analysis_results()
        assert len(results) == 3  # 只返回 complete 的


class TestConceptRelations:
    """概念关系测试。"""

    def test_save_concept_relation(self, repo: ArticleRepository):
        """测试保存概念共现关系。"""
        repo.save_concept_relation("概念A", "概念B", 5)
        relations = repo.get_concept_relations(top_n=10)
        assert len(relations) == 1
        assert relations[0]["concept_a"] == "概念A"
        assert relations[0]["concept_b"] == "概念B"
        assert relations[0]["co_occurrence_count"] == 5

    def test_save_concept_relation_ordering(self, repo: ArticleRepository):
        """测试概念对按字典序排列（保证唯一性）。"""
        # 反序传入也应正序存储
        repo.save_concept_relation("概念Z", "概念A", 3)
        relations = repo.get_concept_relations()
        assert relations[0]["concept_a"] == "概念A"
        assert relations[0]["concept_b"] == "概念Z"

    def test_save_concept_relation_upsert(self, repo: ArticleRepository):
        """测试概念关系 UPSERT。"""
        repo.save_concept_relation("A", "B", 3)
        repo.save_concept_relation("A", "B", 5)
        relations = repo.get_concept_relations()
        assert len(relations) == 1
        assert relations[0]["co_occurrence_count"] == 5

    def test_get_concept_relations_top_n(self, repo: ArticleRepository):
        """测试 Top N 排序。"""
        repo.save_concept_relation("A", "B", 1)
        repo.save_concept_relation("C", "D", 10)
        repo.save_concept_relation("E", "F", 5)

        relations = repo.get_concept_relations(top_n=2)
        assert len(relations) == 2
        assert relations[0]["co_occurrence_count"] == 10  # 最高
        assert relations[1]["co_occurrence_count"] == 5   # 第二


class TestStats:
    """统计信息测试。"""

    def test_get_stats_empty(self, repo: ArticleRepository):
        """测试空数据库统计。"""
        stats = repo.get_stats()
        assert stats["total"] == 0
        assert stats["crawled"] == 0
        assert stats["crawl_pending"] == 0
        assert stats["crawl_failed"] == 0
        assert stats["analyzed"] == 0
        assert stats["analyze_failed"] == 0

    def test_get_stats_with_data(self, repo: ArticleRepository):
        """测试有数据时的统计。"""
        # 创建 5 篇文章
        for i in range(5):
            aid = repo.upsert_article(
                Article(title=f"文章{i}", url=f"https://example.com/stats/{i}")
            )
            if i < 3:
                repo.update_crawl_status(aid, "complete")
            elif i == 3:
                repo.update_crawl_status(aid, "failed", "测试错误")

        # 为前 2 篇添加分析结果
        for i in range(2):
            repo.save_analysis_result(
                AnalysisResult(
                    article_id=i + 1,
                    concepts=["概念"],
                    analysis_status="complete",
                )
            )

        stats = repo.get_stats()
        assert stats["total"] == 5
        assert stats["crawled"] == 3
        assert stats["crawl_pending"] == 1
        assert stats["crawl_failed"] == 1
        assert stats["analyzed"] == 2
