"""概念处理测试。

测试 ConceptProcessor 的概念频次统计、共现矩阵、理论支柱分布、演化追踪等功能。
"""

import os
import tempfile

import pytest

from src.analyzer.concepts import ConceptProcessor
from src.database import ArticleRepository, Database
from src.models import AnalysisResult, Article


@pytest.fixture
def concept_processor():
    """创建带有测试数据的 ConceptProcessor 实例。"""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    db = Database(db_path=db_path)
    db.init()
    repo = ArticleRepository(db)

    # 创建文章和分析结果
    articles_data = [
        ("文章1", "https://example.com/1", "2024-01-15T10:00:00",
         ["刘原理", "三视界法", "概念A"]),
        ("文章2", "https://example.com/2", "2024-02-20T10:00:00",
         ["刘原理", "概念A", "概念B"]),
        ("文章3", "https://example.com/3", "2024-03-10T10:00:00",
         ["三视界法", "概念B", "概念C"]),
        ("文章4", "https://example.com/4", "2024-03-25T10:00:00",
         ["刘原理", "三视界法", "太乙预言机"]),
    ]

    for title, url, publish_time, concepts in articles_data:
        article = Article(
            title=title,
            url=url,
            publish_time=publish_time,
            crawl_status="complete",
            content_text="测试正文",
        )
        article_id = repo.upsert_article(article)

        result = AnalysisResult(
            article_id=article_id,
            concepts=concepts,
            keywords=["关键词"],
            theory_pillars=[c for c in concepts if c in
                            ["刘原理", "三视界法", "太乙预言机", "全息拓扑动力学"]],
            summary="测试摘要",
            analysis_status="complete",
        )
        repo.save_analysis_result(result)

    processor = ConceptProcessor(repo)

    yield processor

    db.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


class TestConceptFrequency:
    """概念频次统计测试。"""

    def test_get_concept_frequency(self, concept_processor: ConceptProcessor):
        """测试概念频次统计。"""
        freq = concept_processor.get_concept_frequency()

        # 刘原理出现在文章1、2、4
        assert freq["刘原理"] == 3
        # 三视界法出现在文章1、3、4
        assert freq["三视界法"] == 3
        # 概念A出现在文章1、2
        assert freq["概念A"] == 2
        # 概念B出现在文章2、3
        assert freq["概念B"] == 2
        # 概念C出现在文章3
        assert freq["概念C"] == 1
        # 太乙预言机出现在文章4
        assert freq["太乙预言机"] == 1

    def test_frequency_ordered_by_count(self, concept_processor: ConceptProcessor):
        """测试频次按降序排列。"""
        freq = concept_processor.get_concept_frequency()
        values = list(freq.values())

        # 验证降序排列
        for i in range(len(values) - 1):
            assert values[i] >= values[i + 1]

    def test_get_top_concepts(self, concept_processor: ConceptProcessor):
        """测试获取 Top N 概念。"""
        top3 = concept_processor.get_top_concepts(3)
        assert len(top3) == 3
        # Top 1 应该是频次最高的（刘原理或三视界法，都是3次）
        assert top3[0][1] == 3


class TestCoOccurrenceMatrix:
    """共现矩阵测试。"""

    def test_build_co_occurrence_matrix(self, concept_processor: ConceptProcessor):
        """测试构建共现矩阵。"""
        matrix = concept_processor.build_co_occurrence_matrix()

        # 刘原理和三视界法在文章1、4中共现
        pair = ("三视界法", "刘原理")  # 按字典序
        assert pair in matrix
        assert matrix[pair] == 2  # 文章1和文章4

        # 概念A和刘原理在文章1、2中共现
        pair2 = ("刘原理", "概念A")
        assert pair2 in matrix
        assert matrix[pair2] == 2

        # 概念A和概念B在文章2中共现
        pair3 = ("概念A", "概念B")
        assert pair3 in matrix
        assert matrix[pair3] == 1

    def test_co_occurrence_pairs_ordered(self, concept_processor: ConceptProcessor):
        """测试概念对按字典序排列。"""
        matrix = concept_processor.build_co_occurrence_matrix()

        for concept_a, concept_b in matrix.keys():
            assert concept_a < concept_b

    def test_co_occurrence_saved_to_db(self, concept_processor: ConceptProcessor):
        """测试共现矩阵保存到数据库。"""
        concept_processor.build_co_occurrence_matrix()

        # 从数据库读取
        relations = concept_processor.repo.get_concept_relations(top_n=100)
        assert len(relations) > 0

        # 验证排序
        counts = [r["co_occurrence_count"] for r in relations]
        for i in range(len(counts) - 1):
            assert counts[i] >= counts[i + 1]


class TestPillarDistribution:
    """理论支柱分布测试。"""

    def test_get_pillar_distribution(self, concept_processor: ConceptProcessor):
        """测试理论支柱分布统计。"""
        dist = concept_processor.get_pillar_distribution()

        # 刘原理在文章1、2、4中标注
        assert dist["刘原理"] == 3
        # 三视界法在文章1、3、4中标注
        assert dist["三视界法"] == 3
        # 太乙预言机在文章4中标注
        assert dist["太乙预言机"] == 1


class TestConceptEvolution:
    """概念演化追踪测试。"""

    def test_get_concept_evolution(self, concept_processor: ConceptProcessor):
        """测试概念演化时间线。"""
        timeline = concept_processor.get_concept_evolution()

        # 应该有 3 个月份（1月、2月、3月）
        assert len(timeline) == 3

        # 按时间排序
        times = [item["time"] for item in timeline]
        assert times == sorted(times)

        # 1月应有刘原理和三视界法
        jan_data = timeline[0]
        assert jan_data["time"] == "2024-01"
        assert "刘原理" in jan_data["concepts"]
        assert "三视界法" in jan_data["concepts"]

        # 3月应有2篇文章（文章3和4）
        mar_data = timeline[2]
        assert mar_data["time"] == "2024-03"

    def test_evolution_concepts_top20(self, concept_processor: ConceptProcessor):
        """测试演化时间线中每个时间点最多返回 Top 20 概念。"""
        timeline = concept_processor.get_concept_evolution()
        for item in timeline:
            assert len(item["concepts"]) <= 20


class TestTomasTaijiArticles:
    """TOMAS-AGI / 太极 OS 相关文章测试。"""

    def test_get_tomas_articles(self, concept_processor: ConceptProcessor):
        """测试获取 TOMAS-AGI 相关文章。"""
        # 没有设置 tomas_agi_related=True 的文章
        articles = concept_processor.get_tomas_articles()
        assert len(articles) == 0

    def test_get_taiji_articles(self, concept_processor: ConceptProcessor):
        """测试获取太极 OS 相关文章。"""
        articles = concept_processor.get_taiji_articles()
        assert len(articles) == 0
