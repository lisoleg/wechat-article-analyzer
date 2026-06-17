"""概念处理模块 — ConceptProcessor。

统计所有文章 concepts 字段中概念出现频次，构建共现矩阵，
统计四大理论支柱分布，追踪概念随时间的演化。
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Optional

from loguru import logger

from src.database import ArticleRepository


class ConceptProcessor:
    """概念统计与共现分析处理器。

    Attributes:
        repo: 文章仓库。
    """

    def __init__(self, repo: ArticleRepository) -> None:
        """初始化概念处理器。

        Args:
            repo: 文章仓库实例。
        """
        self.repo: ArticleRepository = repo

    def get_concept_frequency(self) -> dict[str, int]:
        """统计所有文章 concepts 字段中概念出现频次。

        遍历所有已完成分析的结果，统计每个概念出现的文章数。

        Returns:
            {概念: 频次} 字典，按频次降序排列。
        """
        results = self.repo.get_all_analysis_results()
        counter: Counter[str] = Counter()

        for result in results:
            for concept in result.concepts:
                counter[concept] += 1

        # 按频次降序排列
        return dict(counter.most_common())

    def build_co_occurrence_matrix(self) -> dict[tuple[str, str], int]:
        """构建概念共现矩阵。

        遍历每篇文章的 concepts，统计两两共现次数。
        结果存入 concept_relations 表。

        Returns:
            {(concept_a, concept_b): count} 字典，概念对按字典序排列。
        """
        results = self.repo.get_all_analysis_results()
        co_occurrence: Counter[tuple[str, str]] = Counter()

        for result in results:
            concepts = sorted(set(result.concepts))  # 去重并排序
            # 遍历所有两两组合
            for i in range(len(concepts)):
                for j in range(i + 1, len(concepts)):
                    pair = (concepts[i], concepts[j])
                    co_occurrence[pair] += 1

        # 存入数据库
        for (concept_a, concept_b), count in co_occurrence.items():
            self.repo.save_concept_relation(concept_a, concept_b, count)

        logger.info(f"共现矩阵构建完成，共 {len(co_occurrence)} 对概念关系")
        return dict(co_occurrence)

    def get_pillar_distribution(self) -> dict[str, int]:
        """统计四大理论支柱各自的文章数。

        Returns:
            {理论支柱: 文章数} 字典。
        """
        results = self.repo.get_all_analysis_results()
        counter: Counter[str] = Counter()

        for result in results:
            for pillar in result.theory_pillars:
                counter[pillar] += 1

        return dict(counter)

    def get_concept_evolution(self) -> list[dict[str, Any]]:
        """按 publish_time 排序，统计概念随时间出现频率。

        将文章按发布时间排序，统计每个时间点（按月聚合）各概念的出现频次。

        Returns:
            演化时间线列表，每项包含 time（年月）和 concepts（{概念: 频次}）。
        """
        results = self.repo.get_all_analysis_results()
        articles = self.repo.get_all_articles()

        # 建立文章 ID → 发布时间 的映射
        article_time_map: dict[int, str] = {
            a.id: (a.publish_time or "") for a in articles if a.id
        }

        # 按月聚合概念频次
        monthly_concepts: dict[str, Counter[str]] = defaultdict(Counter)

        for result in results:
            publish_time = article_time_map.get(result.article_id, "")
            if not publish_time:
                continue

            # 提取年月（ISO 8601 格式取前 7 位：YYYY-MM）
            month_key = publish_time[:7]
            if len(month_key) < 7:
                continue

            for concept in result.concepts:
                monthly_concepts[month_key][concept] += 1

        # 按时间排序输出
        timeline: list[dict[str, Any]] = []
        for month_key in sorted(monthly_concepts.keys()):
            timeline.append({
                "time": month_key,
                "concepts": dict(monthly_concepts[month_key].most_common(20)),
                "article_count": sum(monthly_concepts[month_key].values()),
            })

        return timeline

    def get_top_concepts(self, n: int = 50) -> list[tuple[str, int]]:
        """返回频次 Top N 概念。

        Args:
            n: 返回前 N 个概念。

        Returns:
            [(概念, 频次), ...] 列表。
        """
        frequency = self.get_concept_frequency()
        return list(frequency.items())[:n]

    def get_tomas_articles(self) -> list[dict[str, Any]]:
        """获取与 TOMAS-AGI 项目相关的文章信息。

        Returns:
            文章信息列表，每项包含 article_id / title / summary。
        """
        results = self.repo.get_all_analysis_results()
        articles = self.repo.get_all_articles()
        article_map: dict[int, str] = {
            a.id: a.title for a in articles if a.id
        }

        tomas_articles: list[dict[str, Any]] = []
        for result in results:
            if result.tomas_agi_related:
                tomas_articles.append({
                    "article_id": result.article_id,
                    "title": article_map.get(result.article_id, ""),
                    "summary": result.summary or "",
                })
        return tomas_articles

    def get_taiji_articles(self) -> list[dict[str, Any]]:
        """获取与太极 OS 项目相关的文章信息。

        Returns:
            文章信息列表，每项包含 article_id / title / summary。
        """
        results = self.repo.get_all_analysis_results()
        articles = self.repo.get_all_articles()
        article_map: dict[int, str] = {
            a.id: a.title for a in articles if a.id
        }

        taiji_articles: list[dict[str, Any]] = []
        for result in results:
            if result.taiji_os_related:
                taiji_articles.append({
                    "article_id": result.article_id,
                    "title": article_map.get(result.article_id, ""),
                    "summary": result.summary or "",
                })
        return taiji_articles
